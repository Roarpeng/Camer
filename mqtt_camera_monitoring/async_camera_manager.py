。/"""
异步摄像头管理器 - 支持并行初始化和非阻塞操作
"""

import cv2
import numpy as np
import logging
import threading
import time
import concurrent.futures
from typing import List, Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass
from .config import CameraConfig
from .camera_manager import CameraFrame


class AsyncCameraManager:
    """异步摄像头管理器 - 优化初始化速度和UI响应"""
    
    def __init__(self, config: CameraConfig):
        self.config = config
        self.cameras: List[Optional[cv2.VideoCapture]] = []
        self.active_cameras: List[bool] = []
        self.capture_active = False
        self.frames_lock = threading.Lock()
        self.current_frames: List[Optional[CameraFrame]] = []
        self.logger = logging.getLogger(__name__)
        
        # 初始化状态跟踪
        self.initialization_progress = {}
        self.initialization_complete = False
        self.initialization_thread = None
        
        # 状态回调
        self.progress_callback: Optional[Callable[[int, int, str], None]] = None
        self.completion_callback: Optional[Callable[[List[int]], None]] = None
    
    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        """设置初始化进度回调"""
        self.progress_callback = callback
    
    def set_completion_callback(self, callback: Callable[[List[int]], None]) -> None:
        """设置初始化完成回调"""
        self.completion_callback = callback
    
    def initialize_cameras_async(self) -> None:
        """异步初始化摄像头，不阻塞主线程"""
        if self.initialization_thread and self.initialization_thread.is_alive():
            self.logger.warning("Camera initialization already in progress")
            return
        
        self.initialization_thread = threading.Thread(
            target=self._initialize_cameras_parallel,
            daemon=True
        )
        self.initialization_thread.start()
        self.logger.info("Started asynchronous camera initialization")
    
    def _initialize_cameras_parallel(self) -> None:
        """并行初始化摄像头"""
        self.logger.info(f"Initializing {self.config.count} cameras in parallel")
        
        # 初始化数据结构
        self.cameras = [None] * self.config.count
        self.active_cameras = [False] * self.config.count
        self.current_frames = [None] * self.config.count
        self.initialization_progress = {}
        
        successful_cameras = []
        
        # 使用线程池并行初始化，设置超时
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, self.config.count)) as executor:
            # 提交所有摄像头初始化任务
            future_to_camera = {
                executor.submit(self._initialize_single_camera, camera_id): camera_id
                for camera_id in range(self.config.count)
            }
            
            # 处理完成的任务，设置超时
            try:
                for future in concurrent.futures.as_completed(future_to_camera, timeout=30):
                    camera_id = future_to_camera[future]
                    try:
                        success, cap = future.result(timeout=5)  # 单个摄像头5秒超时
                        if success and cap is not None:
                            self.cameras[camera_id] = cap
                            self.active_cameras[camera_id] = True
                            successful_cameras.append(camera_id)
                            self.logger.info(f"Camera {camera_id} initialized successfully")
                        else:
                            self.logger.warning(f"Camera {camera_id} initialization failed")
                        
                        # 更新进度
                        completed = len([f for f in future_to_camera if f.done()])
                        if self.progress_callback:
                            self.progress_callback(completed, self.config.count, 
                                                 f"Camera {camera_id} {'OK' if success else 'Failed'}")
                            
                    except concurrent.futures.TimeoutError:
                        self.logger.error(f"Camera {camera_id} initialization timeout")
                        if self.progress_callback:
                            completed = len([f for f in future_to_camera if f.done()])
                            self.progress_callback(completed, self.config.count, 
                                                 f"Camera {camera_id} Timeout")
                    except Exception as e:
                        self.logger.error(f"Camera {camera_id} initialization error: {e}")
                        if self.progress_callback:
                            completed = len([f for f in future_to_camera if f.done()])
                            self.progress_callback(completed, self.config.count, 
                                                 f"Camera {camera_id} Error: {str(e)[:30]}")
            
            except concurrent.futures.TimeoutError:
                self.logger.error("Camera initialization timeout - some cameras may not be initialized")
                # 取消未完成的任务
                for future in future_to_camera:
                    if not future.done():
                        future.cancel()
        
        # 完成初始化
        self.initialization_complete = True
        successful_cameras.sort()
        
        self.logger.info(f"Camera initialization complete. Active cameras: {successful_cameras}")
        
        if self.completion_callback:
            self.completion_callback(successful_cameras)
    
    def _initialize_single_camera(self, camera_id: int) -> Tuple[bool, Optional[cv2.VideoCapture]]:
        """初始化单个摄像头"""
        try:
            # 添加延迟避免摄像头冲突
            delay = camera_id * 0.3  # 每个摄像头延迟0.3秒
            if delay > 0:
                time.sleep(delay)
            
            self.logger.info(f"Initializing camera {camera_id}...")
            
            # 尝试使用DirectShow后端打开摄像头（解决MSMF问题）
            cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
            
            if not cap.isOpened():
                self.logger.warning(f"Camera {camera_id} could not be opened")
                return False, None
            
            # 快速配置基本参数 - 使用分辨率匹配mask (1280x720)
            try:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FPS, 30)
                
                # 设置不同的亮度来帮助区分摄像头
                brightness_values = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
                if camera_id < len(brightness_values):
                    cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness_values[camera_id])
                    
            except Exception as e:
                self.logger.warning(f"Camera {camera_id} configuration warning: {e}")
            
            # 预热摄像头，多次尝试读取
            success = False
            for attempt in range(10):
                ret, frame = cap.read()
                if ret and frame is not None:
                    success = True
                    break
                time.sleep(0.1)
            
            if not success:
                self.logger.warning(f"Camera {camera_id} cannot capture frames after multiple attempts")
                cap.release()
                return False, None
            
            self.logger.info(f"Camera {camera_id} initialized successfully")
            
            return True, cap
            
        except Exception as e:
            self.logger.error(f"Error initializing camera {camera_id}: {e}")
            try:
                if 'cap' in locals():
                    cap.release()
            except:
                pass
            return False, None
    
    def _configure_camera(self, cap: cv2.VideoCapture, camera_id: int) -> None:
        """配置摄像头参数"""
        try:
            # 设置分辨率
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.resolution_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.resolution_height)
            
            # 设置FPS
            cap.set(cv2.CAP_PROP_FPS, self.config.fps)
            
            # 设置缓冲区大小
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 减少延迟
            
            # 设置亮度
            if hasattr(cv2, 'CAP_PROP_BRIGHTNESS'):
                cap.set(cv2.CAP_PROP_BRIGHTNESS, self.config.brightness / 100.0)
            
            # 设置对比度
            if hasattr(cv2, 'CAP_PROP_CONTRAST'):
                cap.set(cv2.CAP_PROP_CONTRAST, self.config.contrast / 100.0)
            
            # 设置饱和度
            if hasattr(cv2, 'CAP_PROP_SATURATION'):
                cap.set(cv2.CAP_PROP_SATURATION, self.config.saturation / 100.0)
            
            # 设置曝光控制
            if hasattr(cv2, 'CAP_PROP_AUTO_EXPOSURE'):
                if self.config.auto_exposure:
                    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
                else:
                    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                    if hasattr(cv2, 'CAP_PROP_EXPOSURE'):
                        cap.set(cv2.CAP_PROP_EXPOSURE, self.config.exposure)
            
            # 设置增益
            if hasattr(cv2, 'CAP_PROP_GAIN'):
                cap.set(cv2.CAP_PROP_GAIN, self.config.gain)
            
            # 设置白平衡
            if hasattr(cv2, 'CAP_PROP_WHITE_BALANCE_BLUE_U'):
                cap.set(cv2.CAP_PROP_WHITE_BALANCE_BLUE_U, self.config.white_balance)
            
        except Exception as e:
            self.logger.warning(f"Error configuring camera {camera_id}: {e}")
    
    def get_active_camera_ids(self) -> List[int]:
        """获取活跃摄像头ID列表"""
        return [i for i, active in enumerate(self.active_cameras) if active]
    
    def is_initialization_complete(self) -> bool:
        """检查初始化是否完成"""
        return self.initialization_complete
    
    def capture_frames(self) -> List[Optional[CameraFrame]]:
        """捕获所有活跃摄像头的帧"""
        if not self.initialization_complete:
            return [None] * self.config.count
        
        frames = []
        current_time = time.time()
        
        for camera_id, (cap, active) in enumerate(zip(self.cameras, self.active_cameras)):
            if not active or cap is None:
                frames.append(None)
                continue
            
            try:
                ret, frame = cap.read()
                if ret and frame is not None:
                    camera_frame = CameraFrame(
                        camera_id=camera_id,
                        frame=frame,
                        timestamp=current_time,
                        is_valid=True
                    )
                    frames.append(camera_frame)
                else:
                    frames.append(None)
            except Exception as e:
                self.logger.error(f"Error capturing frame from camera {camera_id}: {e}")
                frames.append(None)
        
        with self.frames_lock:
            self.current_frames = frames
        
        return frames
    
    def get_current_frames(self) -> List[Optional[CameraFrame]]:
        """获取当前帧"""
        with self.frames_lock:
            return self.current_frames.copy() if self.current_frames else []
    
    def activate_cameras(self) -> None:
        """激活摄像头（兼容性方法）"""
        self.logger.info("Activating cameras due to MQTT message update")
        if self.initialization_complete:
            self.logger.info("Camera activation completed successfully")
        else:
            self.logger.warning("Cameras not yet initialized")
    
    def start_continuous_capture(self) -> None:
        """开始连续捕获"""
        if not self.initialization_complete:
            self.logger.warning("Cannot start capture - initialization not complete")
            return
        
        self.capture_active = True
        self.logger.info("Started continuous frame capture")
    
    def stop_continuous_capture(self) -> None:
        """停止连续捕获"""
        self.capture_active = False
        self.logger.info("Stopping continuous frame capture")
    
    def release_cameras(self) -> None:
        """释放摄像头资源"""
        self.logger.info("Releasing camera resources")
        
        self.capture_active = False
        
        for camera_id, cap in enumerate(self.cameras):
            if cap is not None:
                try:
                    cap.release()
                    self.logger.debug(f"Released camera {camera_id}")
                except Exception as e:
                    self.logger.error(f"Error releasing camera {camera_id}: {e}")
        
        self.cameras.clear()
        self.active_cameras.clear()
        self.current_frames.clear()
        
        # 等待初始化线程结束
        if self.initialization_thread and self.initialization_thread.is_alive():
            self.initialization_thread.join(timeout=2.0)
        
        self.logger.info("Camera resources released")