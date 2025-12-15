"""
Red Light Detection Component

Analyzes camera frames for red light detection with size/area tracking.
Implements baseline tracking and comparison for monitoring changes.
"""

import cv2
import numpy as np
import logging
import time
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from .config import RedLightDetectionConfig
from .camera_manager import CameraFrame


@dataclass
class RedLightDetection:
    """Represents detected red lights in a frame"""
    count: int
    total_area: float
    bounding_boxes: List[Tuple[int, int, int, int]]  # (x, y, width, height)
    contours: List[np.ndarray]
    timestamp: float


@dataclass
class BaselineMeasurement:
    """Baseline measurement for a camera"""
    camera_id: int
    red_light_count: int
    total_area: float
    timestamp: float
    is_established: bool


class RedLightDetector:
    """Analyzes camera frames for red light detection with size/area tracking"""
    
    def __init__(self, config: RedLightDetectionConfig):
        """
        Initialize red light detector
        
        Args:
            config: Red light detection configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Baseline tracking
        self.baselines: Dict[int, BaselineMeasurement] = {}
        self.baseline_establishment_start: Optional[float] = None
        self.baseline_established: bool = False
        
        # HSV color ranges for red detection - more relaxed for better detection
        # Red color wraps around in HSV, so we need two ranges
        self.lower_red_1 = np.array(self.config.lower_red_hsv, dtype=np.uint8)
        self.upper_red_1 = np.array(self.config.upper_red_hsv, dtype=np.uint8)
        self.lower_red_2 = np.array(self.config.lower_red_hsv_2, dtype=np.uint8)
        self.upper_red_2 = np.array(self.config.upper_red_hsv_2, dtype=np.uint8)
        
        self.logger.info("RedLightDetector initialized")
        self.logger.debug(f"Red HSV range 1: {self.lower_red_1} - {self.upper_red_1}")
        self.logger.debug(f"Red HSV range 2: {self.lower_red_2} - {self.upper_red_2}")
    
    def detect_red_lights(self, frame: np.ndarray) -> RedLightDetection:
        """
        Enhanced red light detection with improved precision
        
        Args:
            frame: Input camera frame (BGR format)
            
        Returns:
            RedLightDetection: Detection results with count, area, and bounding boxes
            
        Raises:
            ValueError: If frame is invalid
        """
        if frame is None or frame.size == 0:
            raise ValueError("Invalid frame provided for red light detection")
        
        try:
            # Pre-processing: Light Gaussian blur to reduce noise
            blur_kernel = getattr(self.config, 'gaussian_blur_kernel', 3)
            if blur_kernel > 1:
                blurred = cv2.GaussianBlur(frame, (blur_kernel, blur_kernel), 0)
            else:
                blurred = frame
            
            # Convert BGR to HSV for better color detection
            hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
            
            # Create masks for both red ranges - more aggressive detection
            mask1 = cv2.inRange(hsv, self.lower_red_1, self.upper_red_1)
            mask2 = cv2.inRange(hsv, self.lower_red_2, self.upper_red_2)
            
            # Combine masks
            red_mask = cv2.bitwise_or(mask1, mask2)
            
            # Very relaxed brightness filtering to catch dim red lights
            brightness_threshold = getattr(self.config, 'brightness_threshold', 50)
            if brightness_threshold > 0:
                brightness_mask = hsv[:, :, 2] > brightness_threshold
                red_mask = cv2.bitwise_and(red_mask, brightness_mask.astype(np.uint8) * 255)
            
            # 适度的红色检测 - 平衡检测和精度
            
            # 1. 主要使用HSV检测
            primary_mask = red_mask
            
            # 2. 红色通道优势检测 - 适中的条件
            b, g, r = cv2.split(blurred)
            # 红色通道大于蓝绿通道
            red_dominant = (r > g + 15) & (r > b + 15) & (r > 40)
            red_channel_mask = red_dominant.astype(np.uint8) * 255
            
            # 3. 组合检测结果 - 使用OR保持检测能力
            red_mask = cv2.bitwise_or(primary_mask, red_channel_mask)
            
            # Minimal morphological operations to preserve small red lights
            morph_kernel_size = getattr(self.config, 'morphology_kernel', 1)
            if morph_kernel_size > 0:
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph_kernel_size, morph_kernel_size))
                # Only remove very small noise
                red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel, iterations=1)
            
            # Optional erosion - very conservative to preserve detection
            erosion_kernel_size = getattr(self.config, 'erosion_kernel', 1)
            erosion_iterations = getattr(self.config, 'erosion_iterations', 0)
            if erosion_iterations > 0 and erosion_kernel_size > 0:
                erosion_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erosion_kernel_size, erosion_kernel_size))
                red_mask = cv2.erode(red_mask, erosion_kernel, iterations=erosion_iterations)
            
            # Find contours with hierarchy for better filtering
            contours, hierarchy = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 适度的轮廓过滤 - 平衡检测和精度
            valid_contours = []
            bounding_boxes = []
            total_area = 0.0
            
            min_area = self.config.min_contour_area
            max_area = getattr(self.config, 'max_contour_area', 80000)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # 基本面积过滤
                if area < min_area or area > max_area:
                    continue
                
                # 获取边界框
                x, y, w, h = cv2.boundingRect(contour)
                
                # 适度的形状检查
                if w > 0 and h > 0:
                    aspect_ratio = float(w) / h
                    # 放宽长宽比限制
                    if aspect_ratio < 0.2 or aspect_ratio > 5.0:
                        continue
                    
                    # 简化的紧凑性检查
                    bbox_area = w * h
                    compactness = area / bbox_area if bbox_area > 0 else 0
                    if compactness < 0.2:  # 放宽紧凑性要求
                        continue
                
                valid_contours.append(contour)
                total_area += area
                bounding_boxes.append((x, y, w, h))
            
            count = len(valid_contours)
            
            # Debug information for troubleshooting
            total_contours = len(contours)
            self.logger.debug(f"Detection stats: {total_contours} total contours -> {count} valid red lights, total area {total_area:.2f}")
            
            # Log detection parameters occasionally for verification
            if hasattr(self, '_debug_counter'):
                self._debug_counter += 1
            else:
                self._debug_counter = 1
            
            if self._debug_counter % 25 == 1:  # Every 25 detections - more frequent
                self.logger.info(f"Enhanced detection: {count} red lights found from {total_contours} contours")
                self.logger.info(f"Detection params: HSV1({self.lower_red_1}-{self.upper_red_1}), "
                               f"HSV2({self.lower_red_2}-{self.upper_red_2}), "
                               f"brightness_thresh={brightness_threshold}, min_area={min_area}")
                
                # 如果没有检测到红光，输出更多调试信息
                if count == 0:
                    self.logger.warning(f"No red lights detected! Frame shape: {frame.shape}, "
                                      f"Total contours before filtering: {total_contours}")
                    # 输出HSV统计信息
                    hsv_stats = {
                        'h_min': np.min(hsv[:,:,0]), 'h_max': np.max(hsv[:,:,0]),
                        's_min': np.min(hsv[:,:,1]), 's_max': np.max(hsv[:,:,1]),
                        'v_min': np.min(hsv[:,:,2]), 'v_max': np.max(hsv[:,:,2])
                    }
                    self.logger.info(f"HSV stats: {hsv_stats}")
            
            return RedLightDetection(
                count=count,
                total_area=total_area,
                bounding_boxes=bounding_boxes,
                contours=valid_contours,
                timestamp=time.time()
            )
            
        except Exception as e:
            self.logger.error(f"Error during red light detection: {e}")
            # Return empty detection on error
            return RedLightDetection(
                count=0,
                total_area=0.0,
                bounding_boxes=[],
                contours=[],
                timestamp=time.time()
            )
    
    def start_baseline_establishment(self) -> None:
        """
        Start the baseline establishment process
        
        This should be called when cameras are activated by MQTT update.
        The baseline will be established within the configured duration.
        """
        self.logger.info("Starting baseline establishment process")
        self.baseline_establishment_start = time.time()
        self.baseline_established = False
        self.baselines.clear()
    
    def set_baseline(self, camera_id: int, count: int, area: float) -> bool:
        """
        Store initial red light count and area measurements within 1 second
        
        Args:
            camera_id: Camera identifier
            count: Red light count
            area: Total red light area
            
        Returns:
            bool: True if baseline was set successfully, False if too late
        """
        current_time = time.time()
        
        # Check if we're within the baseline establishment window
        if (self.baseline_establishment_start is None or 
            current_time - self.baseline_establishment_start > self.config.baseline_duration):
            self.logger.warning(f"Baseline establishment window expired for camera {camera_id}")
            return False
        
        baseline = BaselineMeasurement(
            camera_id=camera_id,
            red_light_count=count,
            total_area=area,
            timestamp=current_time,
            is_established=True
        )
        
        self.baselines[camera_id] = baseline
        self.logger.info(f"Baseline set for camera {camera_id}: count={count}, area={area:.2f}")
        
        return True
    
    def is_baseline_window_active(self) -> bool:
        """
        Check if we're still within the baseline establishment window
        
        Returns:
            bool: True if baseline window is active
        """
        if self.baseline_establishment_start is None:
            return False
        
        current_time = time.time()
        return current_time - self.baseline_establishment_start <= self.config.baseline_duration
    
    def establish_baseline_from_frame(self, camera_id: int, frame: np.ndarray) -> bool:
        """
        Establish baseline from a camera frame if within the establishment window
        
        Args:
            camera_id: Camera identifier
            frame: Camera frame to analyze
            
        Returns:
            bool: True if baseline was established, False otherwise
        """
        if not self.is_baseline_window_active():
            return False
        
        try:
            detection = self.detect_red_lights(frame)
            return self.set_baseline(camera_id, detection.count, detection.total_area)
        except Exception as e:
            self.logger.error(f"Error establishing baseline for camera {camera_id}: {e}")
            return False
    
    def check_changes(self, camera_id: int, current_count: int, current_area: float) -> Dict[str, Any]:
        """
        Compare current counts and areas with baseline
        
        Args:
            camera_id: Camera identifier
            current_count: Current red light count
            current_area: Current total red light area
            
        Returns:
            Dict containing change detection results
        """
        if camera_id not in self.baselines:
            self.logger.warning(f"No baseline established for camera {camera_id}")
            return {
                'has_baseline': False,
                'count_decreased': False,
                'area_changed': False,
                'should_trigger': False,
                'baseline_count': 0,
                'baseline_area': 0.0,
                'current_count': current_count,
                'current_area': current_area
            }
        
        baseline = self.baselines[camera_id]
        
        # Check for count decrease
        count_decreased = current_count < baseline.red_light_count
        
        # Check for area change (both increase and decrease)
        area_change_ratio = abs(current_area - baseline.total_area) / max(baseline.total_area, 1.0)
        area_changed = area_change_ratio > self.config.area_change_threshold
        
        # Trigger if either count decreased OR area changed significantly
        should_trigger = count_decreased or area_changed
        
        if should_trigger:
            self.logger.info(
                f"Change detected for camera {camera_id}: "
                f"count {baseline.red_light_count} -> {current_count}, "
                f"area {baseline.total_area:.2f} -> {current_area:.2f}"
            )
        
        return {
            'has_baseline': True,
            'count_decreased': count_decreased,
            'area_changed': area_changed,
            'should_trigger': should_trigger,
            'baseline_count': baseline.red_light_count,
            'baseline_area': baseline.total_area,
            'current_count': current_count,
            'current_area': current_area,
            'area_change_ratio': area_change_ratio
        }
    
    def check_frame_changes(self, camera_id: int, frame: np.ndarray) -> Dict[str, Any]:
        """
        Analyze frame and check for changes against baseline
        
        Args:
            camera_id: Camera identifier
            frame: Camera frame to analyze
            
        Returns:
            Dict containing detection and change results
        """
        try:
            detection = self.detect_red_lights(frame)
            change_result = self.check_changes(camera_id, detection.count, detection.total_area)
            
            # Add detection info to result
            change_result.update({
                'detection': detection,
                'detection_successful': True
            })
            
            return change_result
            
        except Exception as e:
            self.logger.error(f"Error checking frame changes for camera {camera_id}: {e}")
            return {
                'has_baseline': camera_id in self.baselines,
                'count_decreased': False,
                'area_changed': False,
                'should_trigger': False,
                'detection_successful': False,
                'error': str(e)
            }
    
    def update_baseline(self, camera_id: int, count: int, area: float) -> None:
        """
        Update baseline after trigger (for next monitoring cycle)
        
        Args:
            camera_id: Camera identifier
            count: New baseline red light count
            area: New baseline total area
        """
        if camera_id in self.baselines:
            old_baseline = self.baselines[camera_id]
            self.logger.info(
                f"Updating baseline for camera {camera_id}: "
                f"count {old_baseline.red_light_count} -> {count}, "
                f"area {old_baseline.total_area:.2f} -> {area:.2f}"
            )
        
        baseline = BaselineMeasurement(
            camera_id=camera_id,
            red_light_count=count,
            total_area=area,
            timestamp=time.time(),
            is_established=True
        )
        
        self.baselines[camera_id] = baseline
    
    def get_detection_boxes(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Return bounding boxes for detected red lights
        
        Args:
            frame: Input camera frame
            
        Returns:
            List of bounding boxes as (x, y, width, height) tuples
        """
        try:
            detection = self.detect_red_lights(frame)
            return detection.bounding_boxes
        except Exception as e:
            self.logger.error(f"Error getting detection boxes: {e}")
            return []
    
    def get_baseline_status(self) -> Dict[str, Any]:
        """
        Get current baseline establishment status
        
        Returns:
            Dict containing baseline status information
        """
        current_time = time.time()
        
        return {
            'baseline_establishment_active': self.is_baseline_window_active(),
            'baseline_start_time': self.baseline_establishment_start,
            'baseline_duration': self.config.baseline_duration,
            'time_remaining': (
                self.config.baseline_duration - (current_time - self.baseline_establishment_start)
                if self.baseline_establishment_start else 0
            ),
            'baselines_established': len(self.baselines),
            'camera_baselines': {
                camera_id: {
                    'count': baseline.red_light_count,
                    'area': baseline.total_area,
                    'timestamp': baseline.timestamp
                }
                for camera_id, baseline in self.baselines.items()
            }
        }
    
    def reset_baselines(self) -> None:
        """
        Reset all baselines and establishment state
        
        This should be called when starting a new monitoring cycle.
        """
        self.logger.info("Resetting all baselines")
        self.baselines.clear()
        self.baseline_establishment_start = None
        self.baseline_established = False
    
    def has_baseline(self, camera_id: int) -> bool:
        """
        Check if baseline is established for a specific camera
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            bool: True if baseline is established
        """
        return camera_id in self.baselines and self.baselines[camera_id].is_established
    
    def get_baseline(self, camera_id: int) -> Optional[BaselineMeasurement]:
        """
        Get baseline measurement for a specific camera
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            BaselineMeasurement or None if not established
        """
        return self.baselines.get(camera_id)
    
    def process_camera_frame(self, camera_frame: CameraFrame) -> Dict[str, Any]:
        """
        Process a camera frame for red light detection and change monitoring
        
        This is the main processing method that handles both baseline establishment
        and continuous monitoring phases.
        
        Args:
            camera_frame: Camera frame to process
            
        Returns:
            Dict containing processing results
        """
        if not camera_frame.is_valid or camera_frame.frame is None:
            return {
                'camera_id': camera_frame.camera_id,
                'processed': False,
                'error': 'Invalid camera frame'
            }
        
        camera_id = camera_frame.camera_id
        
        try:
            # Detect red lights in frame
            detection = self.detect_red_lights(camera_frame.frame)
            
            # If we're in baseline establishment window and don't have baseline yet
            if self.is_baseline_window_active() and not self.has_baseline(camera_id):
                baseline_set = self.set_baseline(camera_id, detection.count, detection.total_area)
                return {
                    'camera_id': camera_id,
                    'processed': True,
                    'phase': 'baseline_establishment',
                    'baseline_set': baseline_set,
                    'detection': detection
                }
            
            # If we have baseline, check for changes
            elif self.has_baseline(camera_id):
                change_result = self.check_changes(camera_id, detection.count, detection.total_area)
                change_result.update({
                    'camera_id': camera_id,
                    'processed': True,
                    'phase': 'monitoring',
                    'detection': detection
                })
                return change_result
            
            # No baseline and not in establishment window
            else:
                return {
                    'camera_id': camera_id,
                    'processed': True,
                    'phase': 'waiting',
                    'detection': detection,
                    'message': 'Waiting for baseline establishment to start'
                }
                
        except Exception as e:
            self.logger.error(f"Error processing camera frame {camera_id}: {e}")
            return {
                'camera_id': camera_id,
                'processed': False,
                'error': str(e)
            }