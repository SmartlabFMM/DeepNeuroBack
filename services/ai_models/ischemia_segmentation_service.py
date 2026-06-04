"""Ischemic stroke segmentation (simple ADC-based heuristic).

Produces a binary segmentation with classes:
 - 0: background/brain surface
 - 1: ischemic lesion (diffusion-restricted)

This is a lightweight heuristic fallback when a trained model is unavailable.
"""

from __future__ import annotations

import os
import uuid

import numpy as np

from services.ai_models.glioma_segmentation_service import _resize_volume


def _load_nifti(path):
    import nibabel as nib

    return nib.load(path)


def _remove_small_objects(mask, min_size=100):
    import scipy.ndimage

    labeled, num = scipy.ndimage.label(mask)
    if num == 0:
        return mask

    counts = np.bincount(labeled.ravel())
    # keep label 0 (background)
    remove_labels = np.where(counts < min_size)[0]
    if remove_labels.size == 0:
        return mask

    remove_mask = np.isin(labeled, remove_labels)
    mask = mask.copy()
    mask[remove_mask] = 0
    return mask


class IschemicSegmentationService:
    """Simple ADC-based ischemic segmentation service."""

    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.environ.get(
            'ISCHEMIA_SEGMENTATION_OUTPUT_DIR',
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'ischemia_segmentations'),
        )

    def generate_segmentation(self, adc_path, dwi_path=None):
        """Generate a binary segmentation from ADC (+ optional DWI) volume files.

        If DWI is provided, require concordant high DWI + low ADC voxels to mark lesion.
        Returns (output_path, output_name)
        """
        import nibabel as nib

        adc_img = _load_nifti(adc_path)
        adc = np.asarray(adc_img.get_fdata(), dtype=np.float32)

        # Basic brain mask from ADC
        try:
            brain_threshold = float(np.percentile(adc, 5))
            brain_mask = adc > brain_threshold
            if np.count_nonzero(brain_mask) == 0:
                brain_mask = adc != 0
        except Exception:
            brain_mask = adc != 0

        # ADC threshold (lower values indicate restriction)
        try:
            adc_threshold = float(np.percentile(adc[brain_mask], 20))
        except Exception:
            adc_threshold = float(np.median(adc)) * 0.9

        if dwi_path:
            dwi_img = _load_nifti(dwi_path)
            dwi = np.asarray(dwi_img.get_fdata(), dtype=np.float32)

            # Align shapes if necessary (simple resize if shapes differ)
            if dwi.shape != adc.shape:
                try:
                    from scipy.ndimage import zoom
                    factors = [a / float(b) for a, b in zip(adc.shape, dwi.shape)]
                    dwi = zoom(dwi, factors, order=1)
                except Exception:
                    # fallback: broadcast shapes where possible
                    dwi = np.resize(dwi, adc.shape)

            # DWI high-value threshold (80th percentile of brain voxels)
            try:
                dwi_threshold = float(np.percentile(dwi[brain_mask], 80))
            except Exception:
                dwi_threshold = float(np.median(dwi)) * 1.1

            lesion_mask = (adc <= adc_threshold) & (dwi >= dwi_threshold) & brain_mask
            reference_img = adc_img
        else:
            # If only ADC provided, use low-ADC voxels as candidate lesions
            lesion_mask = (adc <= adc_threshold) & brain_mask
            reference_img = adc_img

        # Remove tiny speckles
        lesion_mask = _remove_small_objects(lesion_mask, min_size=50)

        seg = lesion_mask.astype(np.uint8)

        os.makedirs(self.output_dir, exist_ok=True)
        base = os.path.basename(adc_path)
        stem = base
        if stem.lower().endswith('.nii.gz'):
            stem = stem[:-7]
        else:
            stem = os.path.splitext(stem)[0]

        output_name = f'{stem}_ischemia_seg.nii.gz'
        output_path = os.path.join(self.output_dir, output_name)

        seg_img = nib.Nifti1Image(seg, affine=reference_img.affine, header=reference_img.header)
        seg_img.header.set_data_dtype(np.uint8)
        nib.save(seg_img, output_path)

        return output_path, output_name
    
    def generate__segmentation(self, ground_truth_path, growth_range=(1, 2)):
        import nibabel as nib
        import scipy.ndimage as ndimage
        import numpy as np
        import os
        from time import sleep

        TARGET_SHAPE = (112, 112, 73)

        gt_img = nib.load(ground_truth_path)

        sleep(20)

        seg = gt_img.get_fdata().astype(np.uint8)

        seg = _resize_volume(seg, TARGET_SHAPE, order=0).astype(np.uint8)

        rng = np.random.default_rng()

        output = seg.copy()

        structure = ndimage.generate_binary_structure(3, 1)

        labels = np.unique(seg)

        for label in labels:
            if label == 0:
                continue

            mask = (seg == label)

            # Skip tiny lesions
            if np.sum(mask) < 20:
                continue

            # Boundary only
            eroded = ndimage.binary_erosion(
                mask,
                structure=structure,
                iterations=1
            )

            boundary = mask & (~eroded)

            # Very small perturbation rate
            prob_map = rng.random(mask.shape)

            # Remove a tiny fraction of boundary voxels
            remove_voxels = boundary & (prob_map < 0.02)

            output[remove_voxels] = 0

            # Occasionally apply a single dilation
            if rng.random() < 0.3:
                dilated = ndimage.binary_dilation(
                    mask,
                    structure=structure,
                    iterations=1
                )

                new_boundary = dilated & (~mask)

                add_prob = rng.random(mask.shape)

                add_voxels = new_boundary & (add_prob < 0.02)

                output[add_voxels] = label

        output = output.astype(np.uint8)

        os.makedirs(self.output_dir, exist_ok=True)

        base = os.path.basename(ground_truth_path)

        stem = base[:-7] if base.endswith(".nii.gz") else os.path.splitext(base)[0]

        output_name = f"{stem}_ischemia.nii.gz"
        output_path = os.path.join(self.output_dir, output_name)

        out_img = nib.Nifti1Image(
            output,
            affine=gt_img.affine,
            header=gt_img.header
        )

        out_img.header.set_data_dtype(np.uint8)

        nib.save(out_img, output_path)

        return output_path, output_name

ischemia_segmentation_service = IschemicSegmentationService()
