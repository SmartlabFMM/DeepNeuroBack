from flask import Blueprint, request, jsonify
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Database

diagnosis_bp = Blueprint('diagnosis', __name__, url_prefix='/api/diagnosis')

db = Database()

@diagnosis_bp.route('/submit', methods=['POST'])
def submit_diagnosis_request():
    """Submit a new diagnosis request"""
    try:
        data = request.get_json()
        
        required_fields = ['case_id', 'doctor_email', 'doctor_name', 'patient_name', 
                          'patient_id', 'patient_age', 'patient_gender', 'diagnosis_type',
                          'scan_date', 'priority', 'radiologist_email', 'description']
        
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Validate radiologist exists
        radiologist = db.get_user_by_email(data['radiologist_email'].lower())
        if not radiologist or radiologist['user_type'] != 'radiologist':
            return jsonify({'success': False, 'message': 'Invalid radiologist'}), 400
        
        # Save diagnosis request
        success = db.save_diagnosis_request(
            case_id=data['case_id'],
            doctor_email=data['doctor_email'],
            doctor_name=data['doctor_name'],
            patient_name=data['patient_name'],
            patient_id=data['patient_id'],
            patient_age=int(data['patient_age']),
            patient_gender=data['patient_gender'],
            diagnosis_type=data['diagnosis_type'],
            scan_date=data['scan_date'],
            priority=data['priority'],
            radiologist_email=data['radiologist_email'],
            description=data['description']
        )
        
        if not success:
            return jsonify({'success': False, 'message': 'Failed to submit request'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Diagnosis request submitted successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@diagnosis_bp.route('/doctor/<doctor_email>', methods=['GET'])
def get_doctor_requests(doctor_email):
    """Get all requests submitted by a doctor"""
    try:
        doctor_email = doctor_email.strip().lower()
        
        # Verify user is a doctor
        user = db.get_user_by_email(doctor_email)
        if not user or user['user_type'] != 'doctor':
            return jsonify({'success': False, 'message': 'Invalid doctor'}), 400
        
        requests = db.get_requests_by_doctor(doctor_email)
        
        return jsonify({
            'success': True,
            'requests': requests
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@diagnosis_bp.route('/radiologist/<radiologist_email>', methods=['GET'])
def get_radiologist_requests(radiologist_email):
    """Get all requests sent to a radiologist"""
    try:
        radiologist_email = radiologist_email.strip().lower()
        
        # Verify user is a radiologist
        user = db.get_user_by_email(radiologist_email)
        if not user or user['user_type'] != 'radiologist':
            return jsonify({'success': False, 'message': 'Invalid radiologist'}), 400
        
        requests = db.get_requests_by_radiologist(radiologist_email)
        
        return jsonify({
            'success': True,
            'requests': requests
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@diagnosis_bp.route('/radiologists', methods=['GET'])
def get_all_radiologists():
    """Get list of all available radiologists"""
    try:
        radiologists = db.get_all_radiologists()
        
        return jsonify({
            'success': True,
            'radiologists': radiologists
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@diagnosis_bp.route('/previous-cases/<doctor_email>', methods=['GET'])
def get_previous_cases(doctor_email):
    """Get all previous cases for a doctor (for autocomplete)"""
    try:
        doctor_email = doctor_email.strip().lower()
        
        cases = db.get_previous_cases_by_doctor(doctor_email)
        
        return jsonify({
            'success': True,
            'cases': cases
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@diagnosis_bp.route('/patients/add', methods=['POST'])
def add_patient():
    """Add a patient profile for a doctor"""
    try:
        data = request.get_json()

        required_fields = [
            'doctor_email', 'patient_name', 'patient_age', 'patient_sex',
            'patient_id', 'patient_email', 'phone_number', 'has_conditions', 'conditions_notes'
        ]

        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        doctor_email = data['doctor_email'].strip().lower()
        user = db.get_user_by_email(doctor_email)
        if not user or user['user_type'] != 'doctor':
            return jsonify({'success': False, 'message': 'Invalid doctor'}), 400

        success, message = db.save_patient(
            doctor_email=doctor_email,
            patient_name=data['patient_name'].strip(),
            patient_age=int(data['patient_age']),
            patient_sex=data['patient_sex'].strip(),
            patient_id=data['patient_id'].strip(),
            patient_email=data['patient_email'].strip().lower(),
            phone_number=data['phone_number'].strip(),
            has_conditions=bool(data['has_conditions']),
            conditions_notes=data['conditions_notes'].strip()
        )

        if not success:
            return jsonify({'success': False, 'message': message}), 400

        return jsonify({'success': True, 'message': message}), 201

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@diagnosis_bp.route('/patients/doctor/<doctor_email>', methods=['GET'])
def get_doctor_patients(doctor_email):
    """Get all patients added by a doctor"""
    try:
        doctor_email = doctor_email.strip().lower()

        user = db.get_user_by_email(doctor_email)
        if not user or user['user_type'] != 'doctor':
            return jsonify({'success': False, 'message': 'Invalid doctor'}), 400

        patients = db.get_patients_by_doctor(doctor_email)

        return jsonify({
            'success': True,
            'patients': patients
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@diagnosis_bp.route('/mark-read/doctor/<int:request_id>', methods=['PUT'])
def mark_read_doctor(request_id):
    """Mark request as read by doctor"""
    try:
        success = db.mark_request_as_read_by_doctor(request_id)
        
        if not success:
            return jsonify({'success': False, 'message': 'Failed to update request'}), 500
        
        return jsonify({'success': True, 'message': 'Request marked as read'}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@diagnosis_bp.route('/mark-read/radiologist/<int:request_id>', methods=['PUT'])
def mark_read_radiologist(request_id):
    """Mark request as read by radiologist"""
    try:
        success = db.mark_request_as_read_by_radiologist(request_id)
        
        if not success:
            return jsonify({'success': False, 'message': 'Failed to update request'}), 500
        
        return jsonify({'success': True, 'message': 'Request marked as read'}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500
