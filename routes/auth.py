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

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user - saves pending verification until email is verified"""
    try:
        data = request.get_json()
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        medical_id = data.get('medical_id', '').strip()
        
        # Validation
        if not all([name, email, password, medical_id]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
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
        data = request.get_json()
        
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
            db.increment_verification_attempts(email)
            return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user with email and password"""
    try:
        data = request.get_json()
        
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
        data = request.get_json()
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
        data = request.get_json()
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
        data = request.get_json()
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
