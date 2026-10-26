from __future__ import annotations

import sys
import time
import csv
from datetime import datetime, timezone
from pathlib import Path
from winsound import MessageBeep, MB_ICONEXCLAMATION

import cv2
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

from fatiguewatch.eye_metrics import eye_aspect_ratio


class FatigueWatch(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FatigueWatch AI")
        self.resize(1100, 720)
        self.camera = cv2.VideoCapture(0)
        cascade_dir = cv2.data.haarcascades
        self.face_detector = cv2.CascadeClassifier(cascade_dir + "haarcascade_frontalface_default.xml")
        self.eye_detector = cv2.CascadeClassifier(cascade_dir + "haarcascade_eye_tree_eyeglasses.xml")
        self.started = False
        self.started_at = 0.0
        self.closed_since: float | None = None
        self.alarm_active = False
        self.eye_count = 0
        self.eye_track: list[tuple[int, int, int, int]] = []
        self.blink_count = 0
        self.last_blink_at = 0.0
        self.log_path = Path("data") / "events.csv"
        self.log_path.parent.mkdir(exist_ok=True)
        if not self.log_path.exists():
            with self.log_path.open("w", newline="", encoding="utf-8") as file:
                csv.writer(file).writerow(["timestamp", "event", "ear", "duration_ms"])

        self.preview = QLabel("Camera offline")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(760, 480)
        self.status = QLabel("ALERT  •  Ready to start")
        self.status.setObjectName("status")
        self.metrics = QLabel("Eyes  —    Face  —")
        self.metrics.setObjectName("metrics")
        self.button = QPushButton("Start monitoring")
        self.button.clicked.connect(self.toggle_monitoring)

        layout = QVBoxLayout()
        layout.addWidget(self.preview, 1)
        layout.addWidget(self.metrics)
        layout.addWidget(self.status)
        layout.addWidget(self.button)
        root = QWidget()
        root.setLayout(layout)
        self.setCentralWidget(root)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        if self.face_detector.empty() or self.eye_detector.empty():
            self.status.setText("SETUP ERROR  •  OpenCV cascade files missing")
            self.button.setEnabled(False)
            self.timer.stop()
        else:
            self.timer.start(30)

    def toggle_monitoring(self) -> None:
        self.started = not self.started
        self.started_at = time.monotonic()
        self.button.setText("Stop monitoring" if self.started else "Start monitoring")
        self.status.setText("ALERT  •  Monitoring" if self.started else "ALERT  •  Ready to start")

    def update_frame(self) -> None:
        if self.face_detector.empty() or self.eye_detector.empty():
            return
        ok, frame = self.camera.read()
        if not ok:
            self.preview.setText("Camera unavailable")
            return
        gray = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        faces = self.face_detector.detectMultiScale(gray, 1.05, 5, minSize=(100, 100))
        ear = None
        self.eye_count = 0
        if len(faces):
            x, y, width, height = faces[0]
            eye_region = gray[y + int(height * 0.12):y + int(height * 0.58), x:x + width]
            eyes = self.eye_detector.detectMultiScale(eye_region, 1.05, 3, minSize=(18, 18), maxSize=(int(width * 0.45), int(height * 0.35)))
            eyes = sorted(eyes, key=lambda eye: eye[0])
            eyes = sorted(eyes, key=lambda eye: eye[2] * eye[3], reverse=True)[:2]
            self.eye_count = len(eyes)
            if eyes:
                self.eye_track = [
                    (x + eye_x, y + int(height * 0.12) + eye_y, eye_width, eye_height)
                    for eye_x, eye_y, eye_width, eye_height in eyes
                ]
            ear = sum(eye_height / max(eye_width, 1) for _, _, eye_width, eye_height in eyes) / len(eyes) if eyes else 0.15
            ear = min(0.45, max(0.12, ear * 0.75))
            for eye_x, eye_y, eye_width, eye_height in eyes:
                cv2.rectangle(frame, (x + eye_x, y + int(height * 0.12) + eye_y), (x + eye_x + eye_width, y + int(height * 0.12) + eye_y + eye_height), (80, 230, 170), 2)
            self.metrics.setText(f"Eyes  {self.eye_count}/2    Face  detected")
        else:
            self.metrics.setText("Eyes  —    Face  not detected")
            self.eye_track = []
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.update_state(ear)
        height, width, channels = frame.shape
        image = QImage(frame.data, width, height, channels * width, QImage.Format.Format_RGB888)
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def update_state(self, ear: float | None) -> None:
        if ear is None:
            self.metrics.setText("EAR  —    Face  not detected")
            self.closed_since = None
            return
        if ear < 0.21 and self.eye_count:
            now = time.monotonic()
            if now - self.last_blink_at > 0.25:
                self.blink_count += 1
                self.last_blink_at = now
        self.metrics.setText(f"Eyes  {self.eye_count}/2    Blink events  {self.blink_count}")
        if not self.started:
            return
        if ear < 0.21 and self.eye_count > 0:
            self.closed_since = self.closed_since or time.monotonic()
            if time.monotonic() - self.closed_since >= 1.5:
                self.status.setText("POSSIBLE DROWSINESS  •  Eyes closed")
                if not self.alarm_active:
                    self.record_event("possible_drowsiness", ear, (time.monotonic() - self.closed_since) * 1000)
                    MessageBeep(MB_ICON_EXCLAMATION)
                    self.alarm_active = True
                return
        elif self.eye_count > 0:
            if self.alarm_active:
                self.record_event("recovered", ear, 0)
            self.alarm_active = False
            self.closed_since = None
        else:
            self.closed_since = None
        self.status.setText("ALERT  •  Monitoring")

    def record_event(self, event: str, ear: float | None, duration_ms: float) -> None:
        with self.log_path.open("a", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow([
                datetime.now(timezone.utc).isoformat(), event,
                f"{ear:.4f}" if ear is not None else "", f"{duration_ms:.0f}",
            ])

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self.camera.release()
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { background: #0d1117; color: #e6edf3; font-family: 'SF Pro Display', 'Segoe UI', sans-serif; font-size: 16px; }
        QLabel { background: #161b22; border: 1px solid #30363d; border-radius: 18px; padding: 16px; }
        QLabel#status { color: #72e6a8; font-family: 'Ugly Dave Alternates', 'Arial Narrow', sans-serif; font-size: 22px; letter-spacing: 1px; }
        QPushButton { background: #6ee7b7; color: #08110d; border: 0; border-radius: 12px; padding: 14px; font-weight: 700; }
        QPushButton:hover { background: #a7f3d0; }
    """)
    window = FatigueWatch()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
