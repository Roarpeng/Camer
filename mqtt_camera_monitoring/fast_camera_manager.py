"""
超快速摄像头管理器 - 优化初始化速度和稳定性
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


class FastCameraManager:
    """超快速摄像头管理器 - 专注速度和稳定性"""
    
    def __init__(self, config: CameraConfig):
        self.config = config
        self.cameras: List[Optional[cv2.VideoCapture]] = []
        self.active_cameras: List[bool] = []
        self.capture_active = False
        self.frames_lock = threading.Lock()
        self.current_frames: List[Optional[CameraFrame]] = []
        self.logger = logging.getLogger(__name__)
        
        # 快速初始化设置
        self.initialization_complete = False
        self.initialization_thread = None
        self.fast_init_timeout = 3.0  # 每个摄像头最多3秒
        
        # 状态回调
        self.progress_callback: Optional[Callable[[int, int, str], None]] = None
        self.completion_callback: Optional[Callable[[List[int]], None]] = None
        
        # 帧捕获优化
        self.frame_skip_count = {}  # 跳帧计数
        self.max_frame_skip = 3     # 最大跳帧数
        
    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        """设置进度回调"""
        self.progress_callback = callback
    
    def set_completion_callback(self, callback: Callable[[List[int]], None]) -> None:
        """设置完成回调"""
        self.completion_callback = callback
    
    def initialize_cameras_async(self) -> None:
        """超快速异步初始化"""
        if self.initialization_thread and self.initialization_thread.is_alive():
            self.logger.warning("Camera initialization already in progress")
            return
        
        self.initialization_thread = threading.Thread(
            target=self._fast_initialize_cameras,
            daemon=True
        )
        self.initialization_thread.start()
        self.logger.info("Started fast camera initialization")
    
    def _fast_initialize_cameras(self) -> None:
        """超快速并行初始化"""
        self.logger.info(f"Fast initializing {self.config.count} cameras")
        
        # 初始化数据结构
        self.cameras = [None] * self.config.count
        self.active_cameras = [False] * self.config.count
        self.current_frames = [None] * self.config.count
        self.frame_skip_count = {}
        
        successful_cameras = []
        
        # 使用更多线程并行初始化，设置超时
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.count) as executor:
            # 提交所有任务
            future_to_camera = {
                executor.submit(self._fast_init_single_camera, camera_id): camera_id
                for camera_id in range(self.config.count)
            }
            
            # 处理完成的任务，设置总超时
            try:
                for future in concurrent.futures.as_completed(future_to_camera, timeout=15):
                    camera_id = future_to_camera[future]
                    try:
                        success, cap = future.result(timeout=self.fast_init_timeout)
                        if success and cap is not None:
                            self.cameras[camera_id] = cap
                            self.active_cameras[camera_id] = True
                            successful_cameras.append(camera_id)
                            self.frame_skip_count[camera_id] = 0
                            self.logger.info(f"Camera {camera_id} fast init OK")
                        else:
                            self.logger.warning(f"Camera {camera_id} fast init failed")
                        
                        # 更新进度
                        completed = len([f for f in future_to_camera if f.done()])
                        if self.progress_callback:
                            self.progress_callback(completed, self.config.count, 
                                                 f"Cam{camera_id} {'✓' if success else '✗'}")
                            
                    except concurrent.futures.TimeoutError:
                        self.logger.warning(f"Camera {camera_id} initialization timeout")
                        if self.progress_callback:
                            completed = len([f for f in future_to_camera if f.done()])
                            self.progress_callback(completed, self.config.count, 
                                                 f"Cam{camera_id} Timeout")
                    except Exception as e:
                        self.logger.error(f"Camera {camera_id} init error: {e}")
                        if self.progress_callback:
                            completed = len([f for f in future_to_camera if f.done()])
                            self.progress_callback(completed, self.config.count, 
                                                 f"Cam{camera_id} Error")
                        
            except concurrent.futures.TimeoutError:
                self.logger.warning("Overall camera initialization timeout")
        
        # 完成初始化
        self.initialization_complete = True
        successful_cameras.sort()
        
        self.logger.info(f"Fast init complete. Active: {successful_cameras}")
        
        if self.completion_callback:
            self.completion_callback(successful_cameras)
    
    def _fast_init_single_camera(self, camera_id: int) -> Tuple[bool, Optional[cv2.VideoCapture]]:
        """超快速初始化单个摄像头"""
        try:
            # 快速打开摄像头
            cap = cv2.VideoCapture(camera_id)
            
            if not cap.isOpened():
                return False, None
            
            # 最小化配置，只设置关键参数
            self._minimal_configure_camera(cap, camera_id)
            
            # 快速测试帧捕获，最多尝试3次
            for attempt in range(3):
                ret, frame = cap.read()
                if ret and frame is not None:
                    return True, cap
                time.sleep(0.05)  # 50ms延迟
            
            # 如果3次都失败，释放摄像头
            cap.release()
            return False, None
            
        except Exception as e:
            self.logger.error(f"Fast init camera {camera_id} error: {e}")
            return False, None
    
    def _minimal_configure_camera(self, cap: cv2.VideoCapture, camera_id: int) -> None:
        """最小化摄像头配置，只设置关键参数"""
        try:
            # 只设置最关键的参数
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 最小缓冲区
            cap.set(cv2.CAP_PROP_FPS, 15)        # 适中的FPS
            
            # 设置较小的分辨率以提高速度
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            
        except Exception as e:
            # 配置失败不影响初始化
            pass
    
    def capture_frames(self) -> List[Optional[CameraFrame]]:
        """优化的帧捕获，处理丢帧问题"""
        if not self.initialization_complete:
            return [None] * self.config.count
        
        frames = []
        current_time = time.time()
        
        for camera_id, (cap, active) in enumerate(zip(self.cameras, self.active_cameras)):
            if not active or cap is None:
                frames.append(None)
                continue
            
            try:
                # 尝试捕获帧
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    # 成功捕获，重置跳帧计数
                    self.frame_skip_count[camera_id] = 0
                    
                    camera_frame = CameraFrame(
                        camera_id=camera_id,
                        frame=frame,
                        timestamp=current_time,
                        is_valid=True
                    )
                    frames.append(camera_frame)
                else:
                    # 捕获失败，增加跳帧计数
                    self.frame_skip_count[camera_id] = self.frame_skip_count.get(camera_id, 0) + 1
                    
                    # 如果跳帧太多，尝试重新初始化摄像头
                    if self.frame_skip_count[camera_id] > self.max_frame_skip:
                        self.logger.warning(f"Camera {camera_id} too many frame drops, attempting recovery")
                        self._recover_camera(camera_id)
                    
                    frames.append(None)
                    
            except Exception as e:
                self.logger.error(f"Error capturing frame from camera {camera_id}: {e}")
                frames.append(None)
                
                # 异常也计入跳帧
                self.frame_skip_count[camera_id] = self.frame_skip_count.get(camera_id, 0) + 1
        
        with self.frames_lock:
            self.current_frames = frames
        
        return frames
    
    def _recover_camera(self, camera_id: int) -> None:
        """尝试恢复有问题的摄像头"""
        try:
            # 释放旧的摄像头
            if self.cameras[camera_id] is not None:
                self.cameras[camera_id].release()
            
            # 尝试重新打开
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                self._minimal_configure_camera(cap, camera_id)
                
                # 测试捕获
                ret, frame = cap.read()
                if ret and frame is not None:
                    self.cameras[camera_id] = cap
                    self.frame_skip_count[camera_id] = 0
                    self.logger.info(f"Camera {camera_id} recovered successfully")
                    return
            
            # 恢复失败
            self.cameras[camera_id] = None
            self.active_cameras[camera_id] = False
            self.logger.error(f"Failed to recover camera {camera_id}")
            
        except Exception as e:
            self.logger.error(f"Error recovering camera {camera_id}: {e}")
    
    def get_active_camera_ids(self) -> List[int]:
        """获取活跃摄像头ID列表"""
        return [i for i, active in enumerate(self.active_cameras) if active]
    
    def is_initialization_complete(self) -> bool:
        """检查初始化是否完成"""
        return self.initialization_complete
    
    def get_current_frames(self) -> List[Optional[CameraFrame]]:
        """获取当前帧"""
        with self.frames_lock:
            return self.current_frames.copy() if self.current_frames else []
    
    def activate_cameras(self) -> None:
        """激活摄像头（兼容性方法）"""
        self.logger.info("Activating cameras")
        if self.initialization_complete:
            self.logger.info("Camera activation completed")
        else:
            self.logger.warning("Cameras not yet initialized")
    
    def start_continuous_capture(self) -> None:
        """开始连续捕获"""
        if not self.initialization_complete:
            self.logger.warning("Cannot start capture - initialization not complete")
            return
        
        self.capture_active = True
        self.logger.info("Started fast continuous capture")
    
    def stop_continuous_capture(self) -> None:
        """停止连续捕获"""
        self.capture_active = False
        self.logger.info("Stopped continuous capture")
    
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
        self.frame_skip_count.clear()
        
        # 等待初始化线程结束
        if self.initialization_thread and self.initialization_thread.is_alive():
            self.initialization_thread.join(timeout=1.0)
        
        self.logger.info("Fast camera resources released")
    
    def get_camera_stats(self) -> Dict[int, Dict[str, Any]]:
        """获取摄像头统计信息"""
        stats = {}
        for camera_id in range(len(self.cameras)):
            if self.active_cameras[camera_id]:
                stats[camera_id] = {
                    'active': True,
                    'frame_drops': self.frame_skip_count.get(camera_id, 0),
                    'status': 'OK' if self.frame_skip_count.get(camera_id, 0) < self.max_frame_skip else 'UNSTABLE'
                }
            else:
                stats[camera_id] = {
                    'active': False,
                    'frame_drops': 0,
                    'status': 'INACTIVE'
                }
        return stats