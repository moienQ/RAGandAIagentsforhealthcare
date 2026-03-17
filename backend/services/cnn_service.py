"""
CNN inference service for MediVision AI.

Loads a pretrained EfficientNetV2-S model fine-tuned on Brain Tumor MRI dataset
(or any 4-class image classifier) and returns class + confidence for a PIL image.

Model file: backend/best_model.pt
Classes: glioma, meningioma, no_tumor, pituitary

If best_model.pt is not found, all functions gracefully return None so the
Gemini pipeline continues without CNN hints.
"""

import os
import io
import logging
from pathlib import Path
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

# Class labels matching the training script output order
BRAIN_TUMOR_CLASSES = ["glioma", "meningioma", "no_tumor", "pituitary"]

# ImageNet normalization constants (same as training)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]

MODEL_PATH = Path(__file__).parent.parent / "best_model.pt"

# Module-level model cache — loaded once at first call
_model = None
_device = None


def _load_model():
    """Load EfficientNetV2-S from best_model.pt. Returns model or None."""
    global _model, _device
    if _model is not None:
        return _model

    if not MODEL_PATH.exists():
        logger.warning(
            f"[CNN] Model file not found at {MODEL_PATH}. "
            "CNN inference will be skipped. Train and place best_model.pt to enable it."
        )
        return None

    try:
        import torch
        import torchvision.models as models

        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"[CNN] Loading model on {_device} from {MODEL_PATH}")

        # Rebuild architecture — must match training script exactly
        model = models.efficientnet_v2_s(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier[1] = torch.nn.Linear(in_features, len(BRAIN_TUMOR_CLASSES))

        state_dict = torch.load(MODEL_PATH, map_location=_device)
        model.load_state_dict(state_dict)
        model.to(_device)
        model.eval()

        _model = model
        logger.info("[CNN] Model loaded successfully.")
        return _model

    except ImportError:
        logger.warning(
            "[CNN] PyTorch is not installed. Install torch and torchvision to enable CNN inference."
        )
        return None
    except Exception as e:
        logger.error(f"[CNN] Failed to load model: {e}")
        return None


def _preprocess(pil_image: Image.Image):
    """Preprocess a PIL image identically to training: 224×224, ImageNet normalize."""
    import torch
    import torchvision.transforms as T

    transform = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])

    # Ensure RGB (handles grayscale / RGBA DICOMs)
    pil_image = pil_image.convert("RGB")
    tensor = transform(pil_image)
    return tensor.unsqueeze(0)  # Add batch dimension


def run_inference(pil_image: Image.Image) -> Optional[dict]:
    """
    Run CNN inference on a PIL image.

    Returns:
        dict with keys: predicted_class (str), confidence (float 0-1),
                        class_probabilities (dict label->float)
        or None if model is not available.
    """
    model = _load_model()
    if model is None:
        return None

    try:
        import torch
        import torch.nn.functional as F

        tensor = _preprocess(pil_image).to(_device)

        with torch.no_grad():
            logits = model(tensor)
            probs = F.softmax(logits, dim=1).squeeze(0)

        predicted_idx = int(probs.argmax().item())
        confidence = float(probs[predicted_idx].item())
        predicted_class = BRAIN_TUMOR_CLASSES[predicted_idx]

        class_probabilities = {
            label: round(float(probs[i].item()), 4)
            for i, label in enumerate(BRAIN_TUMOR_CLASSES)
        }

        logger.info(
            f"[CNN] Prediction: {predicted_class} (confidence: {confidence:.2%})"
        )

        return {
            "predicted_class": predicted_class,
            "confidence": round(confidence, 4),
            "class_probabilities": class_probabilities,
        }

    except Exception as e:
        logger.error(f"[CNN] Inference error: {e}")
        return None


def run_inference_from_bytes(image_bytes: bytes, media_type: str = "image/png") -> Optional[dict]:
    """
    Convenience wrapper: accepts raw image bytes, converts to PIL, runs inference.
    """
    try:
        pil_image = Image.open(io.BytesIO(image_bytes))
        return run_inference(pil_image)
    except Exception as e:
        logger.error(f"[CNN] Failed to decode image bytes: {e}")
        return None
