"""Glioma segmentation inference service."""

from __future__ import annotations

import os
import re
import tempfile
import uuid

import numpy as np

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')


TARGET_SHAPE = (160, 192, 160)


def _load_nifti(path):
    import nibabel as nib

    return nib.load(path)


def _normalize(volume):
    volume = volume.astype(np.float32)
    mean = float(np.mean(volume))
    std = float(np.std(volume))
    if std < 1e-6:
        return volume - mean
    return (volume - mean) / std


def _resize_volume(volume, target_shape, order=1):
    import scipy.ndimage

    factors = [target / source for target, source in zip(target_shape, volume.shape)]
    return scipy.ndimage.zoom(volume, zoom=factors, order=order)


def _extract_case_id(file_path):
    """Extract case id (e.g. 02407-100) from modality file names."""
    file_name = os.path.basename(file_path)
    base_name = file_name
    if base_name.lower().endswith('.nii.gz'):
        base_name = base_name[:-7]
    else:
        base_name = os.path.splitext(base_name)[0]

    base_name = re.sub(r'[-_](t2f|flair|t1n|t1c|t1ce|t2w|t2)$', '', base_name, flags=re.IGNORECASE)
    match = re.search(r'(\d{3,}-\d{2,})', base_name)
    if match:
        return match.group(1)
    return base_name.strip('-_ ')


class GliomaSegmentationService:
    """Load the glioma model lazily and generate segmentation volumes."""

    def __init__(self, model_path=None, output_dir=None):
        default_model_path = os.path.join(os.path.dirname(__file__), 'Glioma Tumor Segmentation.h5')
        self.model_path = (model_path or os.environ.get('GLIOMA_SEGMENTATION_MODEL_PATH', default_model_path)).strip()
        self.output_dir = output_dir or os.environ.get(
            'GLIOMA_SEGMENTATION_OUTPUT_DIR',
            os.path.join(tempfile.gettempdir(), 'DeepNeuro', 'glioma_segmentations'),
        )
        self._model = None

    def _get_model(self):
        if self._model is not None:
            return self._model

        if not self.model_path:
            raise FileNotFoundError('GLIOMA_SEGMENTATION_MODEL_PATH is not configured')

        try:
            import tensorflow as tf
        except Exception as exc:
            raise RuntimeError(f'TensorFlow is required for glioma segmentation: {exc}') from exc

        self._model = tf.keras.models.load_model(self.model_path, compile=False)
        return self._model

    def _preprocess_subject(self, flair_path, t1_path, t1ce_path, t2_path):
        flair_image = _load_nifti(flair_path)
        t1_image = _load_nifti(t1_path)
        t1ce_image = _load_nifti(t1ce_path)
        t2_image = _load_nifti(t2_path)

        flair = _resize_volume(_normalize(flair_image.get_fdata()), TARGET_SHAPE)
        t1 = _resize_volume(_normalize(t1_image.get_fdata()), TARGET_SHAPE)
        t1ce = _resize_volume(_normalize(t1ce_image.get_fdata()), TARGET_SHAPE)
        t2 = _resize_volume(_normalize(t2_image.get_fdata()), TARGET_SHAPE)

        image = np.stack([flair, t1, t1ce, t2], axis=-1).astype(np.float32)
        return image, flair_image

    def generate_segmentation(self, flair_path, t1_path, t1ce_path, t2_path):
        import nibabel as nib

        model = self._get_model()
        image, reference_image = self._preprocess_subject(flair_path, t1_path, t1ce_path, t2_path)

        prediction = model.predict(np.expand_dims(image, axis=0), verbose=0)
        if isinstance(prediction, list):
            prediction = prediction[0]

        prediction = np.asarray(prediction)
        if prediction.ndim == 5:
            prediction = prediction[0]

        if prediction.ndim != 4:
            raise ValueError(f'Unexpected model output shape: {prediction.shape}')

        segmentation = np.argmax(prediction, axis=-1).astype(np.uint8)

        os.makedirs(self.output_dir, exist_ok=True)
        case_id = _extract_case_id(flair_path)
        output_name = f'{case_id}.nii.gz' if case_id else f'glioma_segmentation_{uuid.uuid4().hex}.nii.gz'
        output_path = os.path.join(self.output_dir, output_name)

        segmentation_image = nib.Nifti1Image(segmentation, affine=reference_image.affine, header=reference_image.header)
        segmentation_image.header.set_data_dtype(np.uint8)
        nib.save(segmentation_image, output_path)

        return output_path, output_name


glioma_segmentation_service = GliomaSegmentationService()