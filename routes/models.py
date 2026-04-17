import os
import uuid

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.utils import secure_filename

from services.ai_models import glioma_segmentation_service, list_segmentation_models

models_bp = Blueprint('models', __name__, url_prefix='/api/models')


@models_bp.route('/segmentation', methods=['GET'])
def get_segmentation_models():
    """Get available segmentation models, optionally filtered by diagnosis type."""
    try:
        diagnosis_type = str(request.args.get('diagnosis_type', '')).strip().lower()
        models = list_segmentation_models(diagnosis_type=diagnosis_type)

        return jsonify({
            'success': True,
            'models': models,
            'count': len(models),
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@models_bp.route('/glioma/segment', methods=['POST'])
def generate_glioma_segmentation():
    """Generate a glioma segmentation volume from four MRI modalities."""
    required_fields = ['flair', 't1', 't1ce', 't2']
    saved_paths = []

    try:
        missing_fields = [field for field in required_fields if field not in request.files]
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f"Missing file uploads: {', '.join(missing_fields)}"
            }), 400

        temp_root = os.path.join(current_app.config['UPLOAD_FOLDER'], 'glioma_inputs', uuid.uuid4().hex)
        os.makedirs(temp_root, exist_ok=True)

        input_paths = {}
        for field in required_fields:
            file_storage = request.files[field]
            if not file_storage or file_storage.filename == '':
                return jsonify({'success': False, 'message': f'Missing {field} file'}), 400

            filename = secure_filename(file_storage.filename)
            if not filename:
                filename = f'{field}.nii.gz'

            save_path = os.path.join(temp_root, f'{field}_{filename}')
            file_storage.save(save_path)
            input_paths[field] = save_path
            saved_paths.append(save_path)

        output_path, output_name = glioma_segmentation_service.generate_segmentation(
            flair_path=input_paths['flair'],
            t1_path=input_paths['t1'],
            t1ce_path=input_paths['t1ce'],
            t2_path=input_paths['t2'],
        )

        return send_file(
            output_path,
            as_attachment=True,
            download_name=output_name,
            mimetype='application/octet-stream',
        )

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500
    finally:
        for file_path in saved_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                pass

        if saved_paths:
            temp_root = os.path.dirname(saved_paths[0])
            try:
                if os.path.isdir(temp_root) and not os.listdir(temp_root):
                    os.rmdir(temp_root)
            except OSError:
                pass