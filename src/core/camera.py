import cv2
from PySide6.QtCore import QThread, Signal
import numpy as np

class CameraThread(QThread):
    frame_received = Signal(np.ndarray)
    error_occurred = Signal(str)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self._running = True

    def run(self):
        # Try to open with CAP_DSHOW first on Windows, then fallback
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.camera_index)
            
        if not cap.isOpened():
            self.error_occurred.emit(f"Cannot open camera {self.camera_index}. Check connection or index.")
            return

        # Try to read one frame to verify
        ret, _ = cap.read()
        if not ret:
            self.error_occurred.emit(f"Camera {self.camera_index} opened but failed to read. Busy?")
            cap.release()
            return

        self.error_occurred.emit(f"Camera {self.camera_index} started successfully.")

        while self._running:
            ret, frame = cap.read()
            if ret:
                self.frame_received.emit(frame)
            else:
                self.error_occurred.emit("Failed to read frame")
                # Add a small sleep to avoid tight loop on error
                self.msleep(100)
            
            # Limit fps roughly if needed, purely for resource saving, 
            # but user asked for high performance so we run as fast as possible 
            # or rely on camera hardware fps (usually 30/60).
            # self.msleep(1) 

        cap.release()

    def stop(self):
        self._running = False
        self.wait()
