from __future__ import annotations

from pathlib import Path

import cv2
import mediapipe as mp

from fatiguewatch.eye_metrics import eye_aspect_ratio

LEFT_EYE = (362, 385, 387, 263, 373, 380)
RIGHT_EYE = (33, 160, 158, 133, 153, 144)
MODEL = Path(__file__).parents[1] / "models" / "face_landmarker.task"


class EyeLandmarkDetector:
    def __init__(self) -> None:
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.6,
            min_face_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self._detector = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        self._timestamp_ms = 0

    def measure(self, image: cv2.typing.MatLike) -> tuple[float | None, list[tuple[float, float]] | None]:
        self._timestamp_ms += 1
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        result = self._detector.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), self._timestamp_ms
        )
        if not result.face_landmarks:
            return None, None
        landmarks = result.face_landmarks[0]

        def points(indices: tuple[int, ...]) -> list[tuple[float, float]]:
            return [(landmarks[index].x, landmarks[index].y) for index in indices]

        ear = (eye_aspect_ratio(points(LEFT_EYE)) + eye_aspect_ratio(points(RIGHT_EYE))) / 2
        return ear, [(landmark.x, landmark.y) for landmark in landmarks]

    def close(self) -> None:
        self._detector.close()
