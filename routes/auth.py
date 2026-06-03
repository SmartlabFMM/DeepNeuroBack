from flask import Blueprint, request, jsonify
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Database
from services.email_service import EmailService

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

db = Database()
email_service = EmailService()


def _json_body():
    """Return request JSON as dict, or an empty dict for invalid/missing payloads."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user - saves pending verification until email is verified"""
    try:
        data = _json_body()
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        medical_id = data.get('medical_id', '').strip()
        
        # Validation
        if not all([name, email, password, medical_id]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        if not (medical_id.startswith('01') or medical_id.startswith('02')):
            return jsonify({
                'success': False,
                'message': 'Medical ID must start with 01 (Doctor) or 02 (Radiologist)'
            }), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400
        
        # Check if email already exists
        existing_user = db.get_user_by_email(email)
        if existing_user:
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
        
        # Generate verification code
        verification_code = email_service.generate_verification_code()
        expiration_time = email_service.get_expiration_time()
        
        # Save pending verification
        if not db.save_pending_verification(email, name, password, medical_id, 
                                           verification_code, expiration_time.isoformat()):
            return jsonify({'success': False, 'message': 'Failed to save registration'}), 500
        
        # Send verification email
        if not email_service.send_verification_email(email, name, verification_code):
            return jsonify({'success': False, 'message': 'Failed to send verification email'}), 500
        
        return jsonify({
            'success': True, 
            'message': 'Registration initiated. Please verify your email.',
            'email': email
        }), 201
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """Verify email with verification code"""
    try:
        data = _json_body()
        
        email = data.get('email', '').strip().lower()
        verification_code = data.get('verification_code', '').strip()
        
        if not email or not verification_code:
            return jsonify({'success': False, 'message': 'Missing email or verification code'}), 400
        
        # Verify code
        success, message = db.verify_code(email, verification_code)
        
        if success:
            user = db.get_user_by_email(email)
            return jsonify({
                'success': True,
                'message': message,
                'user': {
                    'id': user['id'],
                    'name': user['name'],
                    'email': user['email'],
                    'medical_id': user['medical_id'],
                    'user_type': user['user_type']
                }
            }), 200
        else:
            return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user with email and password"""
    try:
        data = _json_body()
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Missing email or password'}), 400
        
        # Verify credentials
        if not db.verify_user(email, password):
            return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
        
        # Get user info
        user = db.get_user_by_email(email)
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'medical_id': user['medical_id'],
                'user_type': user['user_type']
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@auth_bp.route('/request-password-reset', methods=['POST'])
def request_password_reset():
    """Request password reset"""
    try:
        data = _json_body()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        # Check if user exists
        user = db.get_user_by_email(email)
        if not user:
            # Don't reveal if email exists or not (security)
            return jsonify({
                'success': True,
                'message': 'If an account exists, you will receive a reset code'
            }), 200
        
        # Generate reset code
        verification_code = email_service.generate_verification_code()
        expiration_time = email_service.get_expiration_time()
        
        # Save password reset request
        db.save_password_reset(email, verification_code, expiration_time.isoformat())
        
        # Send reset email
        if not email_service.send_password_reset_email(email, user['name'], verification_code):
            return jsonify({'success': False, 'message': 'Failed to send reset email'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Password reset code sent to email'
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@auth_bp.route('/verify-reset-code', methods=['POST'])
def verify_reset_code():
    """Verify password reset code"""
    try:
        data = _json_body()
        email = data.get('email', '').strip().lower()
        verification_code = data.get('verification_code', '').strip()
        
        if not email or not verification_code:
            return jsonify({'success': False, 'message': 'Missing email or verification code'}), 400
        
        success, message = db.verify_password_reset_code(email, verification_code)
        
        if success:
            return jsonify({'success': True, 'message': message}), 200
        else:
            db.increment_password_reset_attempts(email)
            return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password with verified code"""
    try:
        data = _json_body()
        email = data.get('email', '').strip().lower()
        verification_code = data.get('verification_code', '').strip()
        new_password = data.get('new_password', '')
        
        if not all([email, verification_code, new_password]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400
        
        # Verify code
        success, message = db.verify_password_reset_code(email, verification_code)
        if not success:
            return jsonify({'success': False, 'message': message}), 400
        
        # Update password
        if not db.update_password(email, new_password):
            return jsonify({'success': False, 'message': 'Failed to update password'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@auth_bp.route('/user/<email>', methods=['GET'])
def get_user(email):
    """Get user information by email"""
    try:
        email = email.strip().lower()
        user = db.get_user_by_email(email)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': user
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@auth_bp.route('/profile/<email>', methods=['GET'])
def get_user_profile(email):
    """Get user profile information"""
    try:
        email = email.strip().lower()
        user = db.get_user_by_email(email)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': {
                'name': user.get('name', ''),
                'email': user.get('email', ''),
                'medical_id': user.get('medical_id', ''),
                'user_type': user.get('user_type', ''),
                'created_at': user.get('created_at', ''),
                'last_login': user.get('last_login', ''),
                'email_verified': user.get('email_verified', 0)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@auth_bp.route('/profile/<email>', methods=['PUT'])
def update_user_profile(email):
    """Update editable profile information."""
    try:
        email = email.strip().lower()
        data = _json_body()
        name = str(data.get('name', '')).strip()

        if not name:
            return jsonify({'success': False, 'message': 'Name is required'}), 400

        user = db.get_user_by_email(email)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        if not db.update_user_profile(email, name):
            return jsonify({'success': False, 'message': 'Failed to update profile'}), 500

        updated_user = db.get_user_by_email(email)
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': {
                'name': updated_user.get('name', name),
                'email': updated_user.get('email', email),
                'medical_id': updated_user.get('medical_id', ''),
                'user_type': updated_user.get('user_type', ''),
                'created_at': updated_user.get('created_at', ''),
                'last_login': updated_user.get('last_login', ''),
                'email_verified': updated_user.get('email_verified', 0)
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@auth_bp.route('/settings/<email>', methods=['GET'])
def get_user_settings(email):
    """Get user settings"""
    try:
        email = email.strip().lower()
        user = db.get_user_by_email(email)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Return default settings (in a real app, these would be stored in DB)
        settings = {
            'case_request_notify': True,
            'case_completed_notify': True,
            'patient_update_notify': True,
            'system_notify': True,
            'notification_frequency': 'Immediately',
            'theme': 'Light',
            'font_size': 10,
            'autosave': True,
            'session_timeout': 120,
            'allow_analytics': True,
            'allow_data_sharing': False
        }
        
        return jsonify({
            'success': True,
            'settings': settings
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@auth_bp.route('/settings', methods=['POST'])
def save_user_settings():
    """Save user settings"""
    try:
        data = _json_body()
        user_email = data.get('user_email', '').strip().lower()
        
        if not user_email:
            return jsonify({'success': False, 'message': 'User email required'}), 400
        
        user = db.get_user_by_email(user_email)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # In a real app, save these settings to a user_settings table
        # For now, just acknowledge receipt
        settings = {
            'case_request_notify': data.get('case_request_notify', True),
            'case_completed_notify': data.get('case_completed_notify', True),
            'patient_update_notify': data.get('patient_update_notify', True),
            'system_notify': data.get('system_notify', True),
            'notification_frequency': data.get('notification_frequency', 'Immediately'),
            'theme': data.get('theme', 'Light'),
            'font_size': data.get('font_size', 10),
            'autosave': data.get('autosave', True),
            'session_timeout': data.get('session_timeout', 120),
            'allow_analytics': data.get('allow_analytics', True),
            'allow_data_sharing': data.get('allow_data_sharing', False)
        }
        
        return jsonify({
            'success': True,
            'message': 'Settings saved successfully',
            'settings': settings
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

