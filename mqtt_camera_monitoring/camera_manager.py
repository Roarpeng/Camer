"""
Camera Manager Component

Manages USB camera operations including initialization, capture,
display, and resource cleanup.
"""

import cv2
import numpy as np
import logging
import threading
import time
from typing import List, Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass
from .config import CameraConfig


@dataclass
class CameraFrame:
    """Represents a camera frame with metadata"""
    camera_id: int
    frame: np.ndarray
    timestamp: float
    is_valid: bool
    
    def copy(self) -> 'CameraFrame':
        """Create a copy of the camera frame"""
        return CameraFrame(
            camera_id=self.camera_id,
            frame=self.frame.copy() if self.frame is not None else None,
            timestamp=self.timestamp,
            is_valid=self.is_valid
        )


class CameraManager:
    """Manages USB camera operations with dynamic parameter configuration"""
    
    def __init__(self, config: CameraConfig):
        """
        Initialize camera manager
        
        Args:
            config: Camera configuration settings
        """
        self.config = config
        self.cameras: List[Optional[cv2.VideoCapture]] = []
        self.camera_windows: List[str] = []
        self.active_cameras: List[bool] = []
        self.capture_active = False
        self.activation_triggered = False
        self.frames_lock = threading.Lock()
        self.current_frames: List[Optional[CameraFrame]] = []
        self.activation_callback: Optional[Callable[[], None]] = None
        self.logger = logging.getLogger(__name__)
        
    def initialize_cameras(self) -> List[int]:
        """
        Initialize USB cameras and create video windows
        
        Returns:
            List[int]: List of successfully initialized camera IDs
            
        Raises:
            RuntimeError: If no cameras can be initialized
        """
        self.logger.info(f"Initializing {self.config.count} USB cameras")
        
        successful_cameras = []
        self.cameras = []
        self.active_cameras = []
        self.current_frames = []
        self.camera_windows = []
        
        for camera_id in range(self.config.count):
            try:
                # Try to open camera
                cap = cv2.VideoCapture(camera_id)
                
                if not cap.isOpened():
                    self.logger.warning(f"Camera {camera_id} could not be opened")
                    self.cameras.append(None)
                    self.active_cameras.append(False)
                    self.current_frames.append(None)
                    self.camera_windows.append("")
                    continue
                
                # Configure camera parameters
                self._configure_camera(cap, camera_id)
                
                # Test frame capture
                ret, frame = cap.read()
                if not ret or frame is None:
                    self.logger.warning(f"Camera {camera_id} failed to capture test frame")
                    cap.release()
                    self.cameras.append(None)
                    self.active_cameras.append(False)
                    self.current_frames.append(None)
                    self.camera_windows.append("")
                    continue
                
                # Create display window
                window_name = f"Camera {camera_id}"
                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(window_name, 320, 240)
                
                self.cameras.append(cap)
                self.active_cameras.append(True)
                self.current_frames.append(None)
                self.camera_windows.append(window_name)
                successful_cameras.append(camera_id)
                
                self.logger.info(f"Camera {camera_id} initialized successfully")
                
            except Exception as e:
                self.logger.error(f"Error initializing camera {camera_id}: {e}")
                self.cameras.append(None)
                self.active_cameras.append(False)
                self.current_frames.append(None)
                self.camera_windows.append("")
        
        if not successful_cameras:
            raise RuntimeError("No cameras could be initialized")
        
        self.logger.info(f"Successfully initialized cameras: {successful_cameras}")
        return successful_cameras
    
    def _configure_camera(self, cap: cv2.VideoCapture, camera_id: int) -> None:
        """
        Configure camera parameters
        
        Args:
            cap: OpenCV VideoCapture object
            camera_id: Camera identifier for logging
        """
        try:
            # Set resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.resolution_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.resolution_height)
            
            # Set FPS
            cap.set(cv2.CAP_PROP_FPS, self.config.fps)
            
            # Set buffer size
            cap.set(cv2.CAP_PROP_BUFFERSIZE, self.config.buffer_size)
            
            # Set brightness
            if hasattr(cv2, 'CAP_PROP_BRIGHTNESS'):
                cap.set(cv2.CAP_PROP_BRIGHTNESS, self.config.brightness / 100.0)
            
            # Set exposure
            if not self.config.auto_exposure and hasattr(cv2, 'CAP_PROP_EXPOSURE'):
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual exposure
                cap.set(cv2.CAP_PROP_EXPOSURE, self.config.exposure / 1000.0)
            elif hasattr(cv2, 'CAP_PROP_AUTO_EXPOSURE'):
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # Auto exposure
            
            # Set contrast
            if hasattr(cv2, 'CAP_PROP_CONTRAST'):
                cap.set(cv2.CAP_PROP_CONTRAST, self.config.contrast / 100.0)
            
            # Set saturation
            if hasattr(cv2, 'CAP_PROP_SATURATION'):
                cap.set(cv2.CAP_PROP_SATURATION, self.config.saturation / 100.0)
            
            self.logger.debug(f"Camera {camera_id} parameters configured")
            
        except Exception as e:
            self.logger.warning(f"Error configuring camera {camera_id} parameters: {e}")
    
    def get_active_camera_ids(self) -> List[int]:
        """
        Get list of active camera IDs
        
        Returns:
            List[int]: List of active camera IDs
        """
        return [i for i, active in enumerate(self.active_cameras) if active]
    
    def display_test_frames(self) -> None:
        """
        Display test frames from all active cameras to verify initialization
        """
        self.logger.info("Displaying test frames from active cameras")
        
        for camera_id, (cap, active, window_name) in enumerate(
            zip(self.cameras, self.active_cameras, self.camera_windows)
        ):
            if not active or cap is None:
                continue
            
            try:
                ret, frame = cap.read()
                if ret and frame is not None:
                    cv2.imshow(window_name, frame)
                    self.logger.debug(f"Test frame displayed for camera {camera_id}")
                else:
                    self.logger.warning(f"Failed to capture test frame from camera {camera_id}")
            except Exception as e:
                self.logger.error(f"Error displaying test frame for camera {camera_id}: {e}")
        
        # Wait briefly to show frames
        cv2.waitKey(1000)
    
    def release_cameras(self) -> None:
        """
        Release all camera resources and close windows
        """
        self.logger.info("Releasing camera resources")
        
        self.capture_active = False
        
        # Release camera objects
        for camera_id, cap in enumerate(self.cameras):
            if cap is not None:
                try:
                    cap.release()
                    self.logger.debug(f"Camera {camera_id} released")
                except Exception as e:
                    self.logger.error(f"Error releasing camera {camera_id}: {e}")
        
        # Close all windows
        try:
            cv2.destroyAllWindows()
            self.logger.debug("All camera windows closed")
        except Exception as e:
            self.logger.error(f"Error closing camera windows: {e}")
        
        # Reset state
        self.cameras.clear()
        self.active_cameras.clear()
        self.current_frames.clear()
        self.camera_windows.clear()
    def start_capture(self) -> bool:
        """
        Start continuous frame capture from all active cameras
        
        Returns:
            bool: True if capture started successfully, False otherwise
        """
        if self.capture_active:
            self.logger.warning("Capture already active")
            return True
        
        active_camera_ids = self.get_active_camera_ids()
        if not active_camera_ids:
            self.logger.error("No active cameras available for capture")
            return False
        
        try:
            self.capture_active = True
            self.logger.info(f"Starting continuous frame capture for {len(active_camera_ids)} cameras")
            
            # Clean up frame buffers before starting
            self.cleanup_frame_buffers()
            
            # Start capture thread for each active camera
            for camera_id in active_camera_ids:
                thread = threading.Thread(
                    target=self._capture_loop,
                    args=(camera_id,),
                    daemon=True,
                    name=f"CameraCapture-{camera_id}"
                )
                thread.start()
                self.logger.debug(f"Started capture thread for camera {camera_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting frame capture: {e}")
            self.capture_active = False
            return False
    
    def stop_capture(self) -> None:
        """
        Stop continuous frame capture
        """
        self.logger.info("Stopping continuous frame capture")
        self.capture_active = False
    
    def _capture_loop(self, camera_id: int) -> None:
        """
        Continuous capture loop for a single camera with enhanced error handling
        
        Args:
            camera_id: Camera identifier
        """
        cap = self.cameras[camera_id]
        if cap is None:
            self.logger.error(f"Camera {camera_id} is None, cannot start capture loop")
            return
        
        self.logger.debug(f"Starting capture loop for camera {camera_id}")
        consecutive_failures = 0
        max_consecutive_failures = 10
        
        while self.capture_active:
            try:
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    # Reset failure counter on successful capture
                    consecutive_failures = 0
                    
                    camera_frame = CameraFrame(
                        camera_id=camera_id,
                        frame=frame.copy(),
                        timestamp=time.time(),
                        is_valid=True
                    )
                    
                    with self.frames_lock:
                        # Ensure current_frames list is large enough
                        while len(self.current_frames) <= camera_id:
                            self.current_frames.append(None)
                        
                        # Clean up previous frame to prevent memory leaks
                        if (camera_id < len(self.current_frames) and 
                            self.current_frames[camera_id] and 
                            self.current_frames[camera_id].frame is not None):
                            del self.current_frames[camera_id].frame
                        
                        self.current_frames[camera_id] = camera_frame
                
                else:
                    consecutive_failures += 1
                    self.logger.warning(f"Failed to capture frame from camera {camera_id} (failure {consecutive_failures}/{max_consecutive_failures})")
                    
                    # Create invalid frame placeholder
                    with self.frames_lock:
                        if camera_id < len(self.current_frames):
                            # Clean up previous frame
                            if (self.current_frames[camera_id] and 
                                self.current_frames[camera_id].frame is not None):
                                del self.current_frames[camera_id].frame
                            
                            self.current_frames[camera_id] = CameraFrame(
                                camera_id=camera_id,
                                frame=np.zeros((self.config.resolution_height, self.config.resolution_width, 3), dtype=np.uint8),
                                timestamp=time.time(),
                                is_valid=False
                            )
                    
                    # If too many consecutive failures, mark camera as inactive
                    if consecutive_failures >= max_consecutive_failures:
                        self.logger.error(f"Camera {camera_id} has failed {consecutive_failures} times, marking as inactive")
                        self.active_cameras[camera_id] = False
                        break
                
                # Adaptive delay based on FPS configuration
                frame_delay = 1.0 / max(self.config.fps, 1)
                time.sleep(frame_delay)
                
            except Exception as e:
                consecutive_failures += 1
                self.logger.error(f"Error in capture loop for camera {camera_id}: {e}")
                
                if consecutive_failures >= max_consecutive_failures:
                    self.logger.error(f"Camera {camera_id} has too many errors, stopping capture")
                    self.active_cameras[camera_id] = False
                    break
                
                time.sleep(0.1)  # Brief pause before retrying
        
        self.logger.debug(f"Capture loop ended for camera {camera_id}")
    
    def get_frames(self) -> List[Optional[CameraFrame]]:
        """
        Get current frames from all cameras
        
        Returns:
            List[Optional[CameraFrame]]: Current frames from all cameras
        """
        with self.frames_lock:
            return [frame.copy() if frame else None for frame in self.current_frames]
    
    def get_frame(self, camera_id: int) -> Optional[CameraFrame]:
        """
        Get current frame from specific camera
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            Optional[CameraFrame]: Current frame or None if not available
        """
        with self.frames_lock:
            if camera_id < len(self.current_frames):
                frame = self.current_frames[camera_id]
                return frame.copy() if frame else None
            return None
    
    def set_brightness(self, value: int) -> None:
        """
        Adjust brightness for all active cameras
        
        Args:
            value: Brightness value (0-100)
        """
        if not 0 <= value <= 100:
            self.logger.warning(f"Invalid brightness value: {value}. Must be 0-100")
            return
        
        self.config.brightness = value
        self.logger.info(f"Setting brightness to {value} for all cameras")
        
        for camera_id, (cap, active) in enumerate(zip(self.cameras, self.active_cameras)):
            if active and cap is not None:
                try:
                    if hasattr(cv2, 'CAP_PROP_BRIGHTNESS'):
                        cap.set(cv2.CAP_PROP_BRIGHTNESS, value / 100.0)
                        self.logger.debug(f"Brightness set for camera {camera_id}")
                except Exception as e:
                    self.logger.error(f"Error setting brightness for camera {camera_id}: {e}")
    
    def set_exposure(self, value: int) -> None:
        """
        Configure exposure time for all active cameras
        
        Args:
            value: Exposure time in milliseconds
        """
        if value < 0:
            self.logger.warning(f"Invalid exposure value: {value}. Must be >= 0")
            return
        
        self.config.exposure = value
        self.logger.info(f"Setting exposure to {value}ms for all cameras")
        
        for camera_id, (cap, active) in enumerate(zip(self.cameras, self.active_cameras)):
            if active and cap is not None:
                try:
                    if hasattr(cv2, 'CAP_PROP_AUTO_EXPOSURE'):
                        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual exposure
                    if hasattr(cv2, 'CAP_PROP_EXPOSURE'):
                        cap.set(cv2.CAP_PROP_EXPOSURE, value / 1000.0)
                        self.logger.debug(f"Exposure set for camera {camera_id}")
                except Exception as e:
                    self.logger.error(f"Error setting exposure for camera {camera_id}: {e}")
    
    def set_contrast(self, value: int) -> None:
        """
        Set contrast for all active cameras
        
        Args:
            value: Contrast value (0-100)
        """
        if not 0 <= value <= 100:
            self.logger.warning(f"Invalid contrast value: {value}. Must be 0-100")
            return
        
        self.config.contrast = value
        self.logger.info(f"Setting contrast to {value} for all cameras")
        
        for camera_id, (cap, active) in enumerate(zip(self.cameras, self.active_cameras)):
            if active and cap is not None:
                try:
                    if hasattr(cv2, 'CAP_PROP_CONTRAST'):
                        cap.set(cv2.CAP_PROP_CONTRAST, value / 100.0)
                        self.logger.debug(f"Contrast set for camera {camera_id}")
                except Exception as e:
                    self.logger.error(f"Error setting contrast for camera {camera_id}: {e}")
    
    def set_saturation(self, value: int) -> None:
        """
        Set saturation for all active cameras
        
        Args:
            value: Saturation value (0-100)
        """
        if not 0 <= value <= 100:
            self.logger.warning(f"Invalid saturation value: {value}. Must be 0-100")
            return
        
        self.config.saturation = value
        self.logger.info(f"Setting saturation to {value} for all cameras")
        
        for camera_id, (cap, active) in enumerate(zip(self.cameras, self.active_cameras)):
            if active and cap is not None:
                try:
                    if hasattr(cv2, 'CAP_PROP_SATURATION'):
                        cap.set(cv2.CAP_PROP_SATURATION, value / 100.0)
                        self.logger.debug(f"Saturation set for camera {camera_id}")
                except Exception as e:
                    self.logger.error(f"Error setting saturation for camera {camera_id}: {e}")
    
    def update_parameters(self, new_config: Dict[str, Any]) -> None:
        """
        Apply runtime parameter updates without system restart
        
        Args:
            new_config: Dictionary of parameter updates
        """
        self.logger.info("Updating camera parameters")
        
        # Update brightness
        if 'brightness' in new_config:
            self.set_brightness(new_config['brightness'])
        
        # Update exposure
        if 'exposure' in new_config:
            self.set_exposure(new_config['exposure'])
        
        # Update contrast
        if 'contrast' in new_config:
            self.set_contrast(new_config['contrast'])
        
        # Update saturation
        if 'saturation' in new_config:
            self.set_saturation(new_config['saturation'])
        
        # Update auto exposure
        if 'auto_exposure' in new_config:
            self.config.auto_exposure = new_config['auto_exposure']
            for camera_id, (cap, active) in enumerate(zip(self.cameras, self.active_cameras)):
                if active and cap is not None:
                    try:
                        if hasattr(cv2, 'CAP_PROP_AUTO_EXPOSURE'):
                            exposure_mode = 0.75 if self.config.auto_exposure else 0.25
                            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, exposure_mode)
                            self.logger.debug(f"Auto exposure updated for camera {camera_id}")
                    except Exception as e:
                        self.logger.error(f"Error updating auto exposure for camera {camera_id}: {e}")
        
        self.logger.info("Camera parameters updated successfully")
    
    def is_capture_active(self) -> bool:
        """
        Check if capture is currently active
        
        Returns:
            bool: True if capture is active
        """
        return self.capture_active
    
    def get_camera_status(self) -> Dict[int, bool]:
        """
        Get status of all cameras
        
        Returns:
            Dict[int, bool]: Dictionary mapping camera ID to active status
        """
        return {i: active for i, active in enumerate(self.active_cameras)}
    
    def cleanup_frame_buffers(self) -> None:
        """
        Clean up frame buffers and reset state
        """
        self.logger.info("Cleaning up frame buffers")
        
        with self.frames_lock:
            # Clear existing frames
            for frame in self.current_frames:
                if frame and hasattr(frame, 'frame') and frame.frame is not None:
                    del frame.frame
            
            self.current_frames.clear()
            # Reinitialize with None values for each camera
            self.current_frames = [None] * len(self.cameras)
        
        self.logger.debug("Frame buffers cleaned up")
    
    def get_frame_buffer_status(self) -> Dict[str, Any]:
        """
        Get current frame buffer status and memory usage information
        
        Returns:
            Dict containing buffer status details
        """
        with self.frames_lock:
            valid_frames = sum(1 for frame in self.current_frames if frame and frame.is_valid)
            total_frames = len(self.current_frames)
            
            # Calculate approximate memory usage
            memory_usage = 0
            for frame in self.current_frames:
                if frame and frame.frame is not None:
                    memory_usage += frame.frame.nbytes
            
            return {
                'total_buffers': total_frames,
                'valid_frames': valid_frames,
                'memory_usage_bytes': memory_usage,
                'memory_usage_mb': memory_usage / (1024 * 1024),
                'capture_active': self.capture_active
            }
    
    def handle_mqtt_message_update(self, message_data: Dict[str, Any]) -> bool:
        """
        Handle MQTT message update and activate cameras if needed
        
        This method demonstrates the integration between MQTT message updates
        and camera activation as specified in Requirements 2.2.
        
        Args:
            message_data: MQTT message data containing update information
            
        Returns:
            bool: True if cameras were activated successfully, False otherwise
        """
        try:
            # Check if this is an actual update (not just a duplicate message)
            is_update = message_data.get('is_update', False)
            
            if is_update:
                self.logger.info("MQTT message update detected, activating cameras")
                return self.activate_on_mqtt_update()
            else:
                self.logger.debug("MQTT message received but no update detected")
                return True
                
        except Exception as e:
            self.logger.error(f"Error handling MQTT message update: {e}")
            return False
    
    def activate_on_mqtt_update(self) -> bool:
        """
        Activate cameras in response to MQTT message update
        
        This method is called when an MQTT message update is detected.
        It starts continuous frame capture from all active cameras.
        
        Returns:
            bool: True if activation successful, False otherwise
        """
        self.logger.info("Activating cameras due to MQTT message update")
        
        if not any(self.active_cameras):
            self.logger.warning("No active cameras available for activation")
            return False
        
        try:
            # Start continuous capture if not already active
            if not self.capture_active:
                self.start_capture()
            
            # Set activation flag
            self.activation_triggered = True
            
            # Call activation callback if set (for baseline establishment)
            if self.activation_callback:
                self.activation_callback()
            
            self.logger.info("Camera activation completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during camera activation: {e}")
            return False
    
    def set_activation_callback(self, callback: Callable[[], None]) -> None:
        """
        Set callback function to be called when cameras are activated
        
        This is typically used to trigger baseline establishment in the
        red light detection component.
        
        Args:
            callback: Function to call when activation occurs
        """
        self.activation_callback = callback
        self.logger.debug("Activation callback set")
    
    def is_activation_triggered(self) -> bool:
        """
        Check if camera activation has been triggered by MQTT update
        
        Returns:
            bool: True if activation was triggered, False otherwise
        """
        return self.activation_triggered
    
    def reset_activation_trigger(self) -> None:
        """
        Reset the activation trigger flag
        
        This should be called after baseline establishment is complete
        or when starting a new monitoring cycle.
        """
        self.activation_triggered = False
        self.logger.debug("Activation trigger reset")
    
    def get_activation_status(self) -> Dict[str, Any]:
        """
        Get current activation status information
        
        Returns:
            Dict containing activation status details
        """
        return {
            'capture_active': self.capture_active,
            'activation_triggered': self.activation_triggered,
            'active_camera_count': sum(self.active_cameras),
            'total_cameras': len(self.cameras),
            'has_activation_callback': self.activation_callback is not None
        }