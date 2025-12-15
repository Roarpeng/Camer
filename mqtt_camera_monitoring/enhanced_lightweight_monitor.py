"""
高性能摄像头监控器 - 纯OpenCV实现
"""

import cv2
import numpy as np
import logging
import threading
import time
from typing import List, Optional, Dict, Any
from .config import VisualMonitorConfig
from .camera_manager import CameraFrame
from .light_detector import RedLightDetection


class EnhancedLightweightMonitor:
    """高性能摄像头监控器 - 纯OpenCV实现，无GUI卡顿"""
    
    def __init__(self, config: VisualMonitorConfig, camera_count: int = 4):
        self.config = config
        self.camera_count = 4  # 固定4个摄像头
        self.logger = logging.getLogger(__name__)
        
        # 显示窗口
        self.camera_windows: List[str] = []
        self.display_active = False
        self.display_lock = threading.Lock()
        
        # 性能优化
        self.last_update = 0
        self.update_interval = 0.033  # 30fps
        
        # 初始化进度
        self.initialization_progress = 0
        self.initialization_total = camera_count
        self.initialization_status = "Ready"
        
        self.logger.info(f"EnhancedLightweightMonitor initialized for {camera_count} cameras")
    
    def create_windows(self) -> bool:
        """创建高性能摄像头窗口"""
        try:
            self.camera_windows = []
            
            # 创建4个摄像头窗口，2x2布局
            for camera_id in range(self.camera_count):
                window_name = f"Camera_{camera_id}"
                
                # 创建窗口
                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
                cv2.resizeWindow(window_name, 400, 300)
                
                # 2x2网格布局
                row = camera_id // 2
                col = camera_id % 2
                x_pos = col * 420
                y_pos = row * 330
                cv2.moveWindow(window_name, x_pos, y_pos)
                
                self.camera_windows.append(window_name)
                
                # 显示初始帧
                placeholder = self._create_placeholder_frame(camera_id, "Initializing...")
                cv2.imshow(window_name, placeholder)
            
            cv2.waitKey(1)
            self.display_active = True
            self.logger.info("High-performance camera windows created")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating windows: {e}")
            return False
    
    def add_log_entry(self, level: str, message: str, camera_id: Optional[int] = None) -> None:
        """添加日志条目 - 简化版本，仅输出到控制台"""
        timestamp = time.strftime('%H:%M:%S')
        camera_str = f"[Cam{camera_id}]" if camera_id is not None else "[SYS]"
        log_line = f"{timestamp} {camera_str} {level}: {message}"
        
        # 根据级别输出到不同流
        if level in ["ERROR"]:
            self.logger.error(log_line)
        elif level in ["WARNING"]:
            self.logger.warning(log_line)
        else:
            self.logger.info(log_line)
    
    def update_initialization_progress(self, current: int, total: int, status: str) -> None:
        """更新初始化进度"""
        self.initialization_progress = current
        self.initialization_total = total
        self.initialization_status = status
        
        # 添加日志
        self.add_log_entry("INFO", f"初始化进度: {current}/{total} - {status}")
    
    def _create_placeholder_frame(self, camera_id: int, message: str) -> np.ndarray:
        """创建占位符帧"""
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        
        # 简单的颜色背景
        colors = [(60, 30, 30), (30, 60, 30), (30, 30, 60), 
                 (60, 60, 30), (60, 30, 60), (30, 60, 60)]
        frame[:] = colors[camera_id % len(colors)]
        
        # 摄像头ID
        cv2.putText(frame, f"Cam {camera_id}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 消息
        cv2.putText(frame, message, (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
    
    def _create_display_frame(self, camera_frame: CameraFrame) -> np.ndarray:
        """创建显示帧"""
        frame = camera_frame.frame
        if frame.shape[0] > 240 or frame.shape[1] > 320:
            frame = cv2.resize(frame, (320, 240))
        else:
            frame = frame.copy()
        
        # 添加信息叠加
        cv2.putText(frame, f"Cam {camera_frame.camera_id}", (5, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 时间戳
        timestamp = time.strftime('%H:%M:%S', time.localtime(camera_frame.timestamp))
        cv2.putText(frame, timestamp, (5, frame.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return frame
    
    def update_display(self, frames: List[Optional[CameraFrame]], 
                      detection_results: Optional[List[Optional[RedLightDetection]]] = None) -> bool:
        """高性能显示更新 - 直接渲染，无卡顿"""
        if not self.display_active or not frames:
            return False
        
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return True
        
        try:
            # 快速更新，无锁
            for camera_id in range(min(self.camera_count, len(frames))):
                if camera_id >= len(self.camera_windows):
                    continue
                    
                window_name = self.camera_windows[camera_id]
                frame = frames[camera_id]
                
                if frame and frame.is_valid and frame.frame is not None:
                    # 直接使用原始帧，最小化处理
                    display_frame = frame.frame
                    
                    # 快速缩放到400x300
                    if display_frame.shape[:2] != (300, 400):
                        display_frame = cv2.resize(display_frame, (400, 300))
                    
                    # 最小化文字叠加
                    cv2.putText(display_frame, f"Cam{camera_id}", (10, 25), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # 检测结果
                    detection = detection_results[camera_id] if detection_results and camera_id < len(detection_results) else None
                    if detection and detection.count > 0:
                        cv2.putText(display_frame, f"Red:{detection.count} Area:{int(detection.total_area)}", 
                                   (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                        
                        # 快速绘制检测框
                        for x, y, w, h in detection.bounding_boxes[:5]:  # 最多5个框
                            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    
                    # 时间戳
                    cv2.putText(display_frame, time.strftime('%H:%M:%S'), 
                               (10, display_frame.shape[0] - 15), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                else:
                    # 快速占位符
                    display_frame = np.zeros((300, 400, 3), dtype=np.uint8)
                    cv2.putText(display_frame, f"Camera {camera_id}", (120, 140), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (128, 128, 128), 2)
                    cv2.putText(display_frame, "No Signal", (140, 170), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # 直接显示，无缓冲
                cv2.imshow(window_name, display_frame)
            
            # 最小化waitKey调用
            cv2.waitKey(1)
            self.last_update = current_time
            return True
            
        except Exception as e:
            self.logger.error(f"Display update error: {e}")
            return False
    
    def _create_live_frame(self, camera_frame: CameraFrame) -> np.ndarray:
        """创建实时显示帧"""
        frame = camera_frame.frame
        if frame.shape[0] > 240 or frame.shape[1] > 320:
            frame = cv2.resize(frame, (320, 240))
        else:
            frame = frame.copy()
        
        # 添加信息叠加
        cv2.putText(frame, f"Cam {camera_frame.camera_id}", (5, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)  # 绿色表示活跃
        
        # 时间戳
        timestamp = time.strftime('%H:%M:%S', time.localtime(camera_frame.timestamp))
        cv2.putText(frame, timestamp, (5, frame.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # 添加"LIVE"标识
        cv2.putText(frame, "LIVE", (frame.shape[1] - 50, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame
    
    def _create_live_frame_with_detection(self, camera_frame: CameraFrame, 
                                        detection: Optional[RedLightDetection] = None) -> np.ndarray:
        """创建带红光检测结果的实时显示帧"""
        frame = camera_frame.frame
        if frame.shape[0] > 240 or frame.shape[1] > 320:
            frame = cv2.resize(frame, (320, 240))
        else:
            frame = frame.copy()
        
        # 绘制红光检测结果
        if detection and detection.count > 0:
            # 绘制检测框
            for x, y, w, h in detection.bounding_boxes:
                # 调整坐标到缩放后的尺寸
                scale_x = frame.shape[1] / camera_frame.frame.shape[1]
                scale_y = frame.shape[0] / camera_frame.frame.shape[0]
                
                x_scaled = int(x * scale_x)
                y_scaled = int(y * scale_y)
                w_scaled = int(w * scale_x)
                h_scaled = int(h * scale_y)
                
                # 绘制绿色检测框
                cv2.rectangle(frame, (x_scaled, y_scaled), 
                            (x_scaled + w_scaled, y_scaled + h_scaled), 
                            (0, 255, 0), 2)
                
                # 添加标签
                cv2.putText(frame, "Red Light", (x_scaled, y_scaled - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # 添加摄像头信息
        cv2.putText(frame, f"Cam {camera_frame.camera_id}", (5, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # 添加检测信息
        if detection:
            detection_text = f"Count: {detection.count}, Area: {detection.total_area:.0f}"
            cv2.putText(frame, detection_text, (5, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        else:
            cv2.putText(frame, "Count: 0, Area: 0", (5, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1)
        
        # 时间戳
        timestamp = time.strftime('%H:%M:%S', time.localtime(camera_frame.timestamp))
        cv2.putText(frame, timestamp, (5, frame.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # 添加"LIVE"标识
        cv2.putText(frame, "LIVE", (frame.shape[1] - 50, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame
    
    def close_windows(self) -> None:
        """关闭所有窗口"""
        try:
            self.logger.info("Closing enhanced lightweight monitor")
            
            with self.display_lock:
                self.display_active = False
                
                # 关闭摄像头窗口
                for window_name in self.camera_windows:
                    try:
                        cv2.destroyWindow(window_name)
                    except:
                        pass
                
                cv2.destroyAllWindows()
                self.camera_windows.clear()
            
            self.logger.info("Enhanced lightweight monitor closed")
            
        except Exception as e:
            self.logger.error(f"Error closing enhanced monitor: {e}")
    
    def is_active(self) -> bool:
        """检查监控器是否活跃"""
        return self.display_active
    
    def get_window_status(self) -> Dict[str, Any]:
        """获取窗口状态"""
        return {
            'display_active': self.display_active,
            'total_windows': len(self.camera_windows),
            'initialization_progress': self.initialization_progress,
            'initialization_status': self.initialization_status
        }
    
    # 兼容性方法
    def show_error(self, camera_id: int, error_msg: str) -> bool:
        """显示错误"""
        self.add_log_entry("ERROR", error_msg, camera_id)
        return True
    
    def update_single_camera(self, camera_id: int, frame: Optional[CameraFrame], 
                           detection: Optional[RedLightDetection] = None) -> bool:
        """更新单个摄像头"""
        frames = [None] * self.camera_count
        frames[camera_id] = frame
        detection_results = [None] * self.camera_count
        detection_results[camera_id] = detection
        return self.update_display(frames, detection_results)
    
    def update_camera_detection_data(self, camera_id: int, **kwargs) -> None:
        """更新摄像头检测数据"""
        pass  # 轻量级版本暂不实现