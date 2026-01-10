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
        self.fps = 15  # 限制帧率为 15fps，足够监控使用，大幅降低 CPU 占用

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

        # Set fixed resolution to match mask size (1386x768)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1376)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 768)

        self.error_occurred.emit(f"Camera {self.camera_index} started successfully.")

        # 帧率控制变量
        import time
        frame_time = 1.0 / self.fps  # 每帧的时间间隔（秒）
        last_time = time.time()

        while self._running:
            ret, frame = cap.read()
            if ret:
                self.frame_received.emit(frame)

                # 帧率控制：计算处理时间并休眠剩余时间
                current_time = time.time()
                elapsed = current_time - last_time
                if elapsed < frame_time:
                    sleep_time = int((frame_time - elapsed) * 1000)
                    if sleep_time > 0:
                        self.msleep(sleep_time)
                last_time = time.time()
            else:
                self.error_occurred.emit("Failed to read frame")
                # Add a small sleep to avoid tight loop on error
                self.msleep(100)

        cap.release()

    def stop(self):
        self._running = False
        self.wait()
