"""
轻量级视觉监控组件 - 优化性能，避免UI卡死
"""

import cv2
import numpy as np
import logging
import threading
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from .config import VisualMonitorConfig
from .camera_manager import CameraFrame
from .light_detector import RedLightDetection


@dataclass
class LightweightWindow:
    """轻量级显示窗口"""
    camera_id: int
    window_name: str
    is_active: bool
    last_update: float
    error_count: int = 0
    max_errors: int = 10  # 最大错误次数，超过后停止更新


class LightweightVisualMonitor:
    """轻量级视觉监控器 - 专注性能和稳定性"""
    
    def __init__(self, config: VisualMonitorConfig, camera_count: int = 6):
        self.config = config
        self.camera_count = camera_count
        self.logger = logging.getLogger(__name__)
        
        # 显示窗口
        self.windows: List[LightweightWindow] = []
        self.display_active = False
        self.display_lock = threading.Lock()
        
        # 性能优化设置
        self.update_interval = 0.1  # 100ms更新间隔，降低CPU使用
        self.last_global_update = 0
        self.error_suppression = {}  # 错误抑制，避免日志洪水
        
        self.logger.info(f"LightweightVisualMonitor initialized for {camera_count} cameras")
    
    def create_windows(self) -> bool:
        """创建轻量级显示窗口"""
        try:
            self.logger.info("Creating lightweight display windows")
            
            with self.display_lock:
                # 清理现有窗口
                if self.windows:
                    cv2.destroyAllWindows()
                    self.windows.clear()
                
                # 创建窗口
                for camera_id in range(self.camera_count):
                    try:
                        window_name = f"Camera {camera_id}"
                        
                        # 创建OpenCV窗口
                        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                        cv2.resizeWindow(window_name, 320, 240)  # 更小的窗口尺寸
                        
                        # 简单的网格布局
                        cols = 3
                        row = camera_id // cols
                        col = camera_id % cols
                        x_pos = col * 330
                        y_pos = row * 270
                        cv2.moveWindow(window_name, x_pos, y_pos)
                        
                        # 创建窗口对象
                        window = LightweightWindow(
                            camera_id=camera_id,
                            window_name=window_name,
                            is_active=True,
                            last_update=time.time()
                        )
                        
                        self.windows.append(window)
                        
                        # 显示初始占位符
                        placeholder = self._create_simple_frame(camera_id, "Initializing...")
                        cv2.imshow(window_name, placeholder)
                        
                    except Exception as e:
                        self.logger.error(f"Error creating window for camera {camera_id}: {e}")
                        continue
                
                self.display_active = True
                cv2.waitKey(1)  # 只调用一次
                
                self.logger.info(f"Created {len(self.windows)} lightweight windows")
                return len(self.windows) > 0
                
        except Exception as e:
            self.logger.error(f"Error creating lightweight windows: {e}")
            return False
    
    def _create_simple_frame(self, camera_id: int, message: str) -> np.ndarray:
        """创建简单的显示帧"""
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
    
    def _create_error_frame(self, camera_id: int, error_msg: str) -> np.ndarray:
        """创建错误显示帧"""
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        frame[:] = (20, 20, 50)  # 深红色背景
        
        # 摄像头ID
        cv2.putText(frame, f"Cam {camera_id}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 错误标识
        cv2.putText(frame, "ERROR", (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        # 错误消息（截断）
        if len(error_msg) > 20:
            error_msg = error_msg[:17] + "..."
        cv2.putText(frame, error_msg, (10, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        return frame
    
    def _should_suppress_error(self, camera_id: int) -> bool:
        """检查是否应该抑制错误（避免日志洪水）"""
        current_time = time.time()
        key = f"camera_{camera_id}_error"
        
        if key not in self.error_suppression:
            self.error_suppression[key] = {'count': 0, 'last_time': current_time}
            return False
        
        error_info = self.error_suppression[key]
        
        # 如果距离上次错误超过10秒，重置计数
        if current_time - error_info['last_time'] > 10:
            error_info['count'] = 0
        
        error_info['count'] += 1
        error_info['last_time'] = current_time
        
        # 如果错误次数超过5次，开始抑制
        return error_info['count'] > 5
    
    def update_display(self, frames: List[Optional[CameraFrame]], 
                      detection_results: Optional[List[Optional[RedLightDetection]]] = None) -> bool:
        """更新显示（优化版本）"""
        if not self.display_active:
            return False
        
        current_time = time.time()
        
        # 限制全局更新频率
        if current_time - self.last_global_update < self.update_interval:
            return True
        
        try:
            with self.display_lock:
                updated_count = 0
                
                for camera_id in range(min(len(self.windows), len(frames))):
                    window = self.windows[camera_id]
                    frame = frames[camera_id]
                    
                    if not window.is_active:
                        continue
                    
                    # 检查错误次数，如果太多就跳过
                    if window.error_count > window.max_errors:
                        continue
                    
                    try:
                        # 创建显示帧
                        if frame and frame.is_valid and frame.frame is not None:
                            # 简化的帧处理
                            display_frame = self._create_display_frame(frame, camera_id)
                            window.error_count = 0  # 重置错误计数
                        else:
                            # 错误帧
                            if not self._should_suppress_error(camera_id):
                                display_frame = self._create_error_frame(camera_id, "Disconnected")
                                window.error_count += 1
                            else:
                                continue  # 跳过更新，避免日志洪水
                        
                        # 更新窗口
                        cv2.imshow(window.window_name, display_frame)
                        window.last_update = current_time
                        updated_count += 1
                        
                    except Exception as e:
                        window.error_count += 1
                        if not self._should_suppress_error(camera_id):
                            self.logger.warning(f"Camera {camera_id} display error: {e}")
                
                # 只在有更新时调用waitKey
                if updated_count > 0:
                    cv2.waitKey(1)
                
                self.last_global_update = current_time
                return True
                
        except Exception as e:
            self.logger.error(f"Error in lightweight display update: {e}")
            return False
    
    def _create_display_frame(self, camera_frame: CameraFrame, camera_id: int) -> np.ndarray:
        """创建简化的显示帧"""
        # 缩放帧以提高性能
        frame = camera_frame.frame
        if frame.shape[0] > 240 or frame.shape[1] > 320:
            frame = cv2.resize(frame, (320, 240))
        else:
            frame = frame.copy()
        
        # 简单的信息叠加
        cv2.putText(frame, f"Cam {camera_id}", (5, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 时间戳
        timestamp = time.strftime('%H:%M:%S', time.localtime(camera_frame.timestamp))
        cv2.putText(frame, timestamp, (5, frame.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return frame
    
    def show_error(self, camera_id: int, error_msg: str) -> bool:
        """显示错误（带抑制机制）"""
        if not self.display_active or camera_id >= len(self.windows):
            return False
        
        # 检查是否应该抑制错误
        if self._should_suppress_error(camera_id):
            return True  # 抑制但返回成功
        
        try:
            with self.display_lock:
                window = self.windows[camera_id]
                window.error_count += 1
                
                # 只有在错误次数不太多时才更新显示
                if window.error_count <= window.max_errors:
                    error_frame = self._create_error_frame(camera_id, error_msg)
                    cv2.imshow(window.window_name, error_frame)
                    cv2.waitKey(1)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error showing error for camera {camera_id}: {e}")
            return False
    
    def close_windows(self) -> None:
        """关闭所有窗口"""
        try:
            self.logger.info("Closing lightweight monitor windows")
            
            with self.display_lock:
                self.display_active = False
                
                # 关闭窗口
                for window in self.windows:
                    try:
                        cv2.destroyWindow(window.window_name)
                    except:
                        pass
                
                cv2.destroyAllWindows()
                self.windows.clear()
                
                self.logger.info("All lightweight monitor windows closed")
                
        except Exception as e:
            self.logger.error(f"Error closing lightweight windows: {e}")
    
    def is_active(self) -> bool:
        """检查监控器是否活跃"""
        return self.display_active
    
    def get_window_status(self) -> Dict[str, Any]:
        """获取窗口状态"""
        with self.display_lock:
            return {
                'display_active': self.display_active,
                'total_windows': len(self.windows),
                'active_windows': sum(1 for w in self.windows if w.is_active),
                'error_windows': sum(1 for w in self.windows if w.error_count > 0)
            }
    
    # 兼容性方法
    def update_single_camera(self, camera_id: int, frame: Optional[CameraFrame], 
                           detection: Optional[RedLightDetection] = None) -> bool:
        """更新单个摄像头（简化版本）"""
        if not self.display_active or camera_id >= len(self.windows):
            return False
        
        frames = [None] * self.camera_count
        frames[camera_id] = frame
        return self.update_display(frames)
    
    def update_camera_detection_data(self, camera_id: int, **kwargs) -> None:
        """更新摄像头检测数据（简化版本）"""
        pass  # 轻量级版本不显示详细检测数据
    
    def add_log_entry(self, level: str, message: str, camera_id: Optional[int] = None) -> None:
        """添加日志条目（简化版本）"""
        pass  # 轻量级版本不显示GUI日志