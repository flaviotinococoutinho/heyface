import threading
from pathlib import Path

import cv2
import numpy as np

from app.domain.representations import SFACE
from app.errors import DomainError
from app.media.images import decode_image
from app.people.facenet import FaceEngine
from app.policies import IMAGE
from app.retrieval.ports import VisualEncoder


class SFaceEncoder:
    def __init__(self, settings):
        self.settings = settings
        self.models = Path(settings.model_path).parent
        self.lock = threading.BoundedSemaphore(IMAGE.inference_slots)
        self.detector = cv2.FaceDetectorYN.create(
            str(self.models / "yunet.onnx"),
            "",
            (IMAGE.max_detection_dimension, IMAGE.max_detection_dimension),
            score_threshold=IMAGE.yunet_confidence,
        )
        self.recognizer = cv2.FaceRecognizerSF.create(str(self.models / "sface.onnx"), "")

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
        array = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
        scale = min(1, IMAGE.max_detection_dimension / max(image.size))
        if scale < 1:
            array = cv2.resize(array, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        height, width = array.shape[:2]
        # Mutable detector state is protected by the bounded inference slot.
        self.detector.setInputSize((width, height))
        _, faces = self.detector.detect(array)
        if faces is None or not len(faces):
            raise DomainError("no_face")
        if len(faces) != 1:
            raise DomainError("multiple_faces")
        if min(faces[0][2:4]) < IMAGE.minimum_face_size:
            raise DomainError("face_too_small")
        crop = self.recognizer.alignCrop(array, faces[0])
        vector = self.recognizer.feature(crop).flatten()
        vector = np.asarray(SFACE.normalize(vector).values, dtype=np.float32)
        if not np.isfinite(vector).all():
            raise DomainError("invalid_embedding", 503)
        return vector.tolist(), {
            "model": SFACE.version,
            "dimensions": SFACE.dimensions,
            "detection_confidence": float(faces[0][-1]),
        }


class HumanRecognition:
    def __init__(self, settings):
        self.encoders: dict[str, VisualEncoder] = {
            "facenet": FaceEngine(settings),
            "sface": SFaceEncoder(settings),
        }

    def enroll(self, encoded: str) -> tuple[dict[str, list[float]], dict]:
        vectors, metadata = {}, {}
        for name, encoder in self.encoders.items():
            vectors[name], metadata[name] = encoder.extract(encoded)
        return vectors, metadata["facenet"] | {"methods": metadata}

    def query(self, encoded: str, method: str) -> tuple[list[float], dict]:
        return self.encoders[method].extract(encoded)
