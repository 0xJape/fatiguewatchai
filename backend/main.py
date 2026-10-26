from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timezone
from threading import Lock

import cv2
import numpy as np
from mediapipe.python.solutions.face_mesh_connections import (
    FACEMESH_FACE_OVAL,
    FACEMESH_LEFT_EYE,
    FACEMESH_LEFT_EYEBROW,
    FACEMESH_LIPS,
    FACEMESH_RIGHT_EYE,
    FACEMESH_RIGHT_EYEBROW,
    FACEMESH_TESSELATION,
)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.detector import LEFT_EYE, RIGHT_EYE, EyeLandmarkDetector

app = FastAPI(title="FatigueWatch API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
DEBUG_WINDOW = "FatigueWatch Backend Tracking — Q to close"
debug_lock = Lock()
DEBUG_CONNECTIONS = FACEMESH_FACE_OVAL | FACEMESH_LEFT_EYE | FACEMESH_RIGHT_EYE | FACEMESH_LEFT_EYEBROW | FACEMESH_RIGHT_EYEBROW | FACEMESH_LIPS
DEBUG_MESH = set(sorted(FACEMESH_TESSELATION)[::4])

def face_metrics(landmarks: list[tuple[float, float]] | None) -> tuple[float | None, str, bool]:
    if not landmarks or len(landmarks) < 478:
        return None, "UNKNOWN", False
    left, right = landmarks[33], landmarks[133]
    iris = np.mean(np.array([landmarks[index] for index in (468, 469, 470, 471, 472)]), axis=0)
    gaze_ratio = (iris[0] - left[0]) / max(right[0] - left[0], 1e-6)
    # Camera image is mirrored for driver-facing preview, so visual side is inverted.
    gaze = "RIGHT" if gaze_ratio < .32 else "LEFT" if gaze_ratio > .68 else "CENTER"
    mouth_height = abs(landmarks[13][1] - landmarks[14][1])
    mouth_width = abs(landmarks[78][0] - landmarks[308][0])
    return round(float(gaze_ratio), 2), gaze, mouth_height / max(mouth_width, 1e-6) > .42


def enhance_low_light(image: cv2.typing.MatLike) -> tuple[cv2.typing.MatLike, float]:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    light, color_a, color_b = cv2.split(lab)
    brightness = float(np.mean(light))
    if brightness < 105:
        light = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(light)
        image = cv2.cvtColor(cv2.merge((light, color_a, color_b)), cv2.COLOR_LAB2BGR)
        image = cv2.convertScaleAbs(image, alpha=1.25, beta=8)
    return image, brightness


def night_vision(image: cv2.typing.MatLike) -> cv2.typing.MatLike:
    green = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    return cv2.merge((green // 8, green, green // 4))


def show_tracking(image: cv2.typing.MatLike, landmarks: list[tuple[float, float]] | None, ear: float | None, threshold: float, night_mode: bool) -> None:
    if night_mode:
        image = night_vision(image)
    height, width = image.shape[:2]
    if landmarks:
        mesh = np.array([(round(x * width), round(y * height)) for x, y in landmarks], dtype=np.int32)
        mesh_lines = [mesh[[start, end]] for start, end in DEBUG_MESH]
        feature_lines = [mesh[[start, end]] for start, end in DEBUG_CONNECTIONS]
        cv2.polylines(image, mesh_lines, False, (65, 45, 15), 1, cv2.LINE_AA)
        cv2.polylines(image, feature_lines, False, (220, 170, 30), 1, cv2.LINE_AA)
        for indices in (LEFT_EYE, RIGHT_EYE):
            contour = np.array([mesh[index] for index in indices], dtype=np.int32)
            cv2.polylines(image, [contour], True, (0, 255, 180), 2, cv2.LINE_AA)
    color = (0, 0, 255) if ear is not None and ear < threshold else (0, 255, 180)
    cv2.putText(image, f"EAR {ear:.3f} / {threshold:.3f}" if ear is not None else "FACE NOT FOUND", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, .8, color, 2)
    with debug_lock:
        cv2.imshow(DEBUG_WINDOW, image)
        cv2.waitKey(1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fatiguewatch-backend"}


@app.websocket("/ws/monitor")
async def monitor(websocket: WebSocket) -> None:
    await websocket.accept()
    detector = EyeLandmarkDetector()
    samples: list[tuple[float, bool]] = []
    calibration: list[float] = []
    calibration_started = time.monotonic()
    monitoring_started = calibration_started
    smoothed_ear: float | None = None
    closed_since: float | None = None
    open_since: float | None = None
    closure_events: list[float] = []
    last_face_seen: float | None = None
    last_status = "ALERT"
    blink_count = 0
    yawn_since: float | None = None
    try:
        while True:
            payload = json.loads(await websocket.receive_text())
            frame = payload.get("frame", "")
            night_mode = bool(payload.get("nightMode"))
            now = time.monotonic()
            ear = None
            landmarks = None
            image = None
            gaze_ratio, gaze, yawn = None, "UNKNOWN", False
            if frame.startswith("data:"):
                raw = base64.b64decode(frame.split(",", 1)[-1], validate=False)
                image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
                if image is not None:
                    inference_image, brightness = enhance_low_light(image)
                    current_ear, landmarks = detector.measure(inference_image)
                    if current_ear is not None:
                        last_face_seen = now
                        smoothed_ear = current_ear if smoothed_ear is None else .7 * smoothed_ear + .3 * current_ear
                        ear = smoothed_ear
                        if now - calibration_started <= 5:
                            calibration.append(ear)
                        gaze_ratio, gaze, yawn = face_metrics(landmarks)

            baseline = float(np.median(calibration)) if calibration else .3
            threshold = max(.13, baseline * .55)
            if image is not None:
                show_tracking(image.copy(), landmarks, ear, threshold, night_mode)
            closed = ear is not None and ear < threshold
            if closed:
                closed_since = closed_since or now
                open_since = None
            elif ear is not None:
                if closed_since is not None and now - closed_since >= .8:
                    closure_events.append(now)
                    blink_count += 1
                closed_since = None
                open_since = open_since or now
            else:
                closed_since = None
                open_since = None

            if yawn:
                yawn_since = yawn_since or now
            else:
                yawn_since = None

            closure_events = [event for event in closure_events if event >= now - 12]

            if ear is not None:
                samples.append((now, closed))
            samples = [sample for sample in samples if sample[0] >= now - 30]
            perclos = sum(closed for _, closed in samples) / len(samples) * 100 if samples else 0
            closure_seconds = now - closed_since if closed_since else 0
            tracking_grace = ear is None and last_face_seen is not None and now - last_face_seen < .75
            tracking = "calibrating" if ear is not None and now - calibration_started <= 5 else ("good" if ear is not None or tracking_grace else ("face not found" if frame else "offline"))
            perclos_ready = now - monitoring_started >= 10
            recovered = open_since is not None and now - open_since >= 1
            sustained_yawn = yawn_since is not None and now - yawn_since >= .6
            elapsed_minutes = max((now - monitoring_started) / 60, 1 / 60)
            blink_rate = round(blink_count / elapsed_minutes, 1)
            if tracking_grace:
                status = last_status
            elif ear is None:
                status = "TRACKING UNAVAILABLE"
            elif closure_seconds >= 4 or (not recovered and perclos_ready and perclos >= 60):
                status = "HIGH DROWSINESS RISK"
            elif sustained_yawn or closure_seconds >= 2.2 or len(closure_events) >= 6 or (not recovered and perclos_ready and perclos >= 55):
                status = "POSSIBLE DROWSINESS"
            else:
                status = "ALERT"
            last_status = status
            await websocket.send_json({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": status,
                "tracking": tracking,
                "ear": round(ear, 3) if ear is not None else None,
                "earThreshold": round(threshold, 3),
                "perclos": round(perclos, 1),
                "closureSeconds": round(closure_seconds, 1),
                "recentClosures": len(closure_events),
                "blinkRate": blink_rate,
                "gaze": gaze,
                "yawn": yawn,
                "lowLight": brightness < 105 if image is not None else False,
                "received": bool(frame),
            })
    except WebSocketDisconnect:
        pass
    finally:
        detector.close()
        with debug_lock:
            cv2.destroyWindow(DEBUG_WINDOW)
