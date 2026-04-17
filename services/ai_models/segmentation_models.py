"""Segmentation model catalog service."""

_SEGMENTATION_MODELS = [
    {
        'id': 'glioma-seg-v1',
        'name': 'Glioma Tumor Segmentation',
        'diagnosis_type': 'Glioma Tumor',
        'version': '1.0.0',
        'status': 'active',
        'input_format': ['nii', 'nii.gz'],
    },
    {
        'id': 'hemorrhage-seg-v1',
        'name': 'Hemorrhagic Stroke Segmentation',
        'diagnosis_type': 'Hemorrhagic Stroke',
        'version': '1.0.0',
        'status': 'active',
        'input_format': ['nii', 'nii.gz'],
    },
    {
        'id': 'ischemia-seg-v1',
        'name': 'Ischemic Stroke Segmentation',
        'diagnosis_type': 'Ischemic Stroke',
        'version': '1.0.0',
        'status': 'active',
        'input_format': ['nii', 'nii.gz'],
    },
]


def list_segmentation_models(diagnosis_type=None):
    """Return segmentation models, optionally filtered by diagnosis type."""
    if not diagnosis_type:
        return list(_SEGMENTATION_MODELS)

    normalized_type = str(diagnosis_type).strip().lower()
    return [
        model for model in _SEGMENTATION_MODELS
        if str(model.get('diagnosis_type', '')).strip().lower() == normalized_type
    ]
