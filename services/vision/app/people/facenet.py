import threading

import cv2
import numpy as np
from PIL import Image

from app.config import Settings
from app.domain.representations import FACENET
from app.errors import DomainError
from app.media.images import decode_image
from app.policies import IMAGE


class FaceEngine:
    def __init__(self, settings: Settings):
        import torch
        from facenet_pytorch import MTCNN, InceptionResnetV1

        self.settings = settings
        self.torch = torch
        torch.set_num_threads(IMAGE.torch_threads)
        torch.set_num_interop_threads(1)
        cv2.setNumThreads(1)
        self.lock = threading.BoundedSemaphore(IMAGE.inference_slots)
        self.detector = MTCNN(
            image_size=IMAGE.facenet_crop_size, margin=0, keep_all=True, device="cpu"
        )
        self.model = InceptionResnetV1(pretrained=None, classify=False).eval()
        # The pinned release contains a classification head; embeddings do not use it.
        weights = torch.load(settings.model_path, map_location="cpu", weights_only=True)
        weights = {k: v for k, v in weights.items() if not k.startswith("logits.")}
        self.model.load_state_dict(weights, strict=True)

    def extract(self, encoded: str) -> tuple[list[float], dict]:
        if not self.lock.acquire(timeout=IMAGE.inference_queue_seconds):
            raise DomainError("vision_busy", 503)
        try:
            return self._extract(encoded)
        finally:
            self.lock.release()

    def _extract(self, encoded: str) -> tuple[list[float], dict]:
        image = decode_image(encoded, self.settings)
        if min(image.size) < IMAGE.minimum_face_size:
            raise DomainError("face_too_small")
        original_width, original_height = image.size
        scale = min(1.0, self.settings.max_dimension / max(image.size))
        if scale < 1:
            array = cv2.resize(
                np.asarray(image), None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA
            )
            image = Image.fromarray(array)
        sx, sy = original_width / image.width, original_height / image.height
        with self.torch.inference_mode():
            boxes, probabilities, landmarks = self.detector.detect(image, landmarks=True)
            if boxes is None or len(boxes) == 0:
                raise DomainError("no_face")
            # Never silently choose one person from a group photo.
            if len(boxes) != 1:
                raise DomainError("multiple_faces")
            if float(probabilities[0]) < IMAGE.facenet_confidence:
                raise DomainError("low_face_confidence")
            x1, y1, x2, y2 = boxes[0]
            if min(x2 - x1, y2 - y1) < IMAGE.minimum_face_size:
                raise DomainError("face_too_small")
            face = self.detector.extract(image, boxes, save_path=None)
            vector = self.model(face)[0].cpu().numpy().astype(np.float32)
        norm = np.linalg.norm(vector)
        if not np.isfinite(vector).all() or norm <= 0:
            raise DomainError("invalid_embedding", 503)
        vector = np.asarray(FACENET.normalize(vector).values, dtype=np.float32)
        gray = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
        crop = gray[
            max(0, int(y1)) : min(image.height, int(y2)),
            max(0, int(x1)) : min(image.width, int(x2)),
        ]
        metadata = {
            "model": self.settings.model_version,
            "dimensions": self.settings.dimensions,
            "detection_confidence": round(float(probabilities[0]), 6),
            "box": [
                round(float(x1 * sx), 2),
                round(float(y1 * sy), 2),
                round(float(x2 * sx), 2),
                round(float(y2 * sy), 2),
            ],
            "landmarks": [
                [round(float(x * sx), 2), round(float(y * sy), 2)] for x, y in landmarks[0]
            ],
            "landmark_order": ["left_eye", "right_eye", "nose", "left_mouth", "right_mouth"],
            "image_size": [original_width, original_height],
            "sharpness": round(float(cv2.Laplacian(crop, cv2.CV_64F).var()), 2),
        }
        return vector.tolist(), metadata
