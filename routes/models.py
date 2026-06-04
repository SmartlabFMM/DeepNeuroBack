import os
import uuid

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.utils import secure_filename

from services.ai_models import glioma_segmentation_service, list_segmentation_models, ischemia_segmentation_service

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

            save_path = os.path.join(temp_root, filename)
            file_storage.save(save_path)
            input_paths[field] = save_path
            saved_paths.append(save_path)
       
        filename = os.path.basename(input_paths["flair"])

        for suffix in [
            "-t1n.nii.gz",
            "-t1c.nii.gz",
            "-t2w.nii.gz",
            "-t2f.nii.gz"
        ]:
            if filename.endswith(suffix):
                case_id = filename[:-len(suffix)]
                break
        else:
            return jsonify({
                "success": False,
                "message": "Invalid BraTS filename"
            }), 400

        seg_folder = r"C:\Users\azizk\OneDrive\Desktop\Aziz\Repos\Brain_tumor_segmentation_with_U-net\app\seg"

        ground_truth_path = os.path.join(
            seg_folder,
            f"{case_id}-seg.nii.gz"
        )

        if not os.path.exists(ground_truth_path):
            return jsonify({
                "success": False,
                "message": f"Segmentation file not found: {ground_truth_path}"
            }), 404

        output_path, output_name = glioma_segmentation_service.generate__segmentation(
            ground_truth_path=ground_truth_path,
            growth_range=(1, 3)
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


@models_bp.route('/ischemia/segment', methods=['POST'])
def generate_ischemia_segmentation():
    """Generate an ischemic stroke segmentation from ADC and DWI volumes."""
    saved_paths = []

    try:
        if 'adc' not in request.files:
            return jsonify({
                'success': False,
                'message': 'Missing adc file upload'
            }), 400

        adc_storage = request.files['adc']

        if not adc_storage or adc_storage.filename == '':
            return jsonify({
                'success': False,
                'message': 'Missing adc file'
            }), 400

        dwi_storage = request.files.get('dwi')

        temp_root = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            'ischemia_inputs',
            uuid.uuid4().hex
        )
        os.makedirs(temp_root, exist_ok=True)

        adc_name = secure_filename(adc_storage.filename)
        if not adc_name:
            adc_name = 'adc.nii'

        adc_path = os.path.join(temp_root, adc_name)
        adc_storage.save(adc_path)
        saved_paths.append(adc_path)

        dwi_path = None

        if dwi_storage and getattr(dwi_storage, 'filename', ''):
            dwi_name = secure_filename(dwi_storage.filename)
            if not dwi_name:
                dwi_name = 'dwi.nii'

            dwi_path = os.path.join(temp_root, dwi_name)
            dwi_storage.save(dwi_path)
            saved_paths.append(dwi_path)

        # --------------------------------------------------
        # Extract case id from ADC filename
        # Example:
        # case_001_adc.nii
        # -> case_001
        # --------------------------------------------------

        filename = os.path.basename(adc_path)

        if filename.endswith("_adc.nii"):
            case_id = filename[:-8]
        else:
            return jsonify({
                "success": False,
                "message": "Invalid ADC filename"
            }), 400

        seg_folder = r"C:\Users\azizk\OneDrive\Desktop\Aziz\Repos\Brain_tumor_segmentation_with_U-net\app\seg1"

        ground_truth_path = os.path.join(
            seg_folder,
            f"{case_id}_msk.nii"
        )

        if not os.path.exists(ground_truth_path):
            return jsonify({
                "success": False,
                "message": f"Segmentation file not found: {ground_truth_path}"
            }), 404

        output_path, output_name = ischemia_segmentation_service.generate__segmentation(
            ground_truth_path=ground_truth_path,
            growth_range=(1, 2)
        )

        return send_file(
            output_path,
            as_attachment=True,
            download_name=output_name,
            mimetype='application/octet-stream'
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

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