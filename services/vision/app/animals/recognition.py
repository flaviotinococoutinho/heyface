import base64
import threading
from pathlib import Path

import cv2
import numpy as np

from app.domain.representations import ANIMAL
from app.errors import DomainError
from app.media.images import decode_image
from app.policies import IMAGE

ANIMAL_MODEL = ANIMAL.version
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def local_match_count(query: dict, candidate: dict) -> float:
    def array(record):
        return (
            np.frombuffer(base64.b64decode(record["descriptors"]), dtype=np.uint8)
            .reshape(-1, IMAGE.local_descriptor_size)
            .astype(np.float32)
        )

    first, second = array(query), array(candidate)
    if len(first) < 2 or len(second) < 2:
        return 0.0
    matches = cv2.BFMatcher(cv2.NORM_L2).knnMatch(first, second, k=2)
    # Deduplicate targets so repeated texture cannot count the same feature twice.
    return float(
        len(
            {
                a.trainIdx
                for a, b in matches
                if a.distance < IMAGE.local_ratio_threshold * b.distance
            }
        )
    )


class AnimalRecognition:
    def __init__(self, settings):
        import timm
        import torch
        from safetensors.torch import load_file
        from torchvision.transforms import Compose, Normalize, Resize, ToTensor

        self.settings, self.torch = settings, torch
        torch.set_num_threads(IMAGE.torch_threads)
        self.lock = threading.BoundedSemaphore(IMAGE.inference_slots)
        self.model = timm.create_model(
            "vit_small_patch14_dinov2.lvd142m", pretrained=False, dynamic_img_size=True
        ).eval()
        self.model.load_state_dict(
            load_file(str(Path(settings.model_path).parent / "dinov2.safetensors"))
        )
        self.transform = Compose(
            [
                Resize((IMAGE.animal_crop_size, IMAGE.animal_crop_size)),
                ToTensor(),
                Normalize(IMAGENET_MEAN, IMAGENET_STD),
            ]
        )

    def extract(self, content: bytes):
        if not self.lock.acquire(timeout=IMAGE.inference_queue_seconds):
            raise DomainError("vision_busy", 503)
        try:
            image = decode_image(content, self.settings)
            with self.torch.inference_mode():
                vector = self.model(self.transform(image).unsqueeze(0))[0].cpu().numpy()
            vector = vector.astype(np.float32)
            vector = np.asarray(ANIMAL.normalize(vector).values, dtype=np.float32)
            if vector.shape != (ANIMAL.dimensions,) or not np.isfinite(vector).all():
                raise DomainError("invalid_embedding", 503)
            gray = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
            ratio = min(1, IMAGE.local_image_dimension / max(image.size))
            gray = cv2.resize(gray, None, fx=ratio, fy=ratio, interpolation=cv2.INTER_AREA)
            keypoints, descriptors = cv2.SIFT_create(
                nfeatures=IMAGE.local_feature_limit
            ).detectAndCompute(gray, None)
            descriptors = (
                descriptors[: IMAGE.local_feature_limit]
                if descriptors is not None
                else np.empty((0, IMAGE.local_descriptor_size))
            )
            local = {
                "descriptors": base64.b64encode(descriptors.astype(np.uint8).tobytes()).decode(),
                "keypoints": [
                    [float(k.pt[0]), float(k.pt[1])] for k in keypoints[: IMAGE.local_feature_limit]
                ],
            }
            return (
                vector.tolist(),
                local,
                {
                    "model": ANIMAL_MODEL,
                    "dimensions": ANIMAL.dimensions,
                    "local_features": len(descriptors),
                    "subject_detection": "user_confirmed_crop",
                },
            )
        finally:
            self.lock.release()
