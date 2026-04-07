from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.utils import secure_filename
import os
import sys
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Database

files_bp = Blueprint('files', __name__, url_prefix='/api/files')

db = Database()


def _allowed_file(filename):
    extension = os.path.splitext(filename)[1].lower().lstrip('.')
    allowed_extensions = set(current_app.config.get('ALLOWED_FILE_EXTENSIONS', []))
    return extension in allowed_extensions


@files_bp.route('', methods=['GET'])
def list_files():
    """Return uploaded file metadata from SQLite."""
    try:
        uploaded_by_email = str(request.args.get('uploaded_by_email', '')).strip().lower()
        related_entity_id = str(request.args.get('related_entity_id', '')).strip()

        files = db.get_uploaded_files(
            uploaded_by_email=uploaded_by_email or None,
            related_entity_id=related_entity_id or None,
        )

        return jsonify({'success': True, 'files': files}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@files_bp.route('/upload', methods=['POST'])
def upload_file():
    """Upload a file to the local filesystem and store metadata in SQLite."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file part found'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        uploaded_by_email = str(request.form.get('uploaded_by_email', '')).strip().lower()
        related_entity_id = str(request.form.get('related_entity_id', '')).strip()

        if not uploaded_by_email:
            return jsonify({'success': False, 'message': 'Uploader email is required'}), 400

        if not _allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'File type not allowed'}), 400

        safe_name = secure_filename(file.filename)
        if not safe_name:
            return jsonify({'success': False, 'message': 'Invalid file name'}), 400

        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)

        unique_name = f"{uuid.uuid4().hex}_{safe_name}"
        file_path = os.path.abspath(os.path.join(upload_folder, unique_name))
        file.save(file_path)

        file_size = os.path.getsize(file_path)
        metadata_id = db.save_uploaded_file(
            file_name=safe_name,
            file_path=file_path,
            uploaded_by_email=uploaded_by_email,
            related_entity_id=related_entity_id,
            file_size=file_size,
            mime_type=file.mimetype or '',
        )

        if not metadata_id:
            try:
                os.remove(file_path)
            except OSError:
                pass
            return jsonify({'success': False, 'message': 'Failed to save file metadata'}), 500

        record = db.get_uploaded_file(metadata_id)
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'file': record,
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@files_bp.route('/<int:file_id>/download', methods=['GET'])
def download_file(file_id):
    """Download a stored file by ID after a basic ownership check."""
    try:
        user_email = str(request.args.get('user_email', '')).strip().lower()
        if not user_email:
            return jsonify({'success': False, 'message': 'User email is required'}), 400

        file_record = db.get_uploaded_file(file_id)
        if not file_record:
            return jsonify({'success': False, 'message': 'File not found'}), 404

        if file_record.get('uploaded_by_email', '').lower() != user_email:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        file_path = file_record.get('file_path', '')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'File not found on server'}), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
            mimetype=file_record.get('mime_type') or None,
        )
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500
