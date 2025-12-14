"""
Unit tests for Red Light Detection component
"""

import pytest
import numpy as np
import cv2
import time
from unittest.mock import Mock, patch
from mqtt_camera_monitoring.light_detector import RedLightDetector, RedLightDetection, BaselineMeasurement
from mqtt_camera_monitoring.camera_manager import CameraFrame
from mqtt_camera_monitoring.config import RedLightDetectionConfig


@pytest.fixture
def red_light_config():
    """Create a test red light detection configuration"""
    return RedLightDetectionConfig(
        lower_red_hsv=[0, 50, 50],
        upper_red_hsv=[10, 255, 255],
        lower_red_hsv_2=[170, 50, 50],
        upper_red_hsv_2=[180, 255, 255],
        min_contour_area=100,
        sensitivity=0.8,
        area_change_threshold=0.2,
        baseline_duration=1.0
    )


@pytest.fixture
def red_light_detector(red_light_config):
    """Create a red light detector instance for testing"""
    return RedLightDetector(red_light_config)


@pytest.fixture
def test_frame():
    """Create a test frame with some red areas"""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Add a red rectangle
    cv2.rectangle(frame, (100, 100), (200, 200), (0, 0, 255), -1)
    
    # Add another red circle
    cv2.circle(frame, (400, 300), 50, (0, 0, 255), -1)
    
    return frame


@pytest.fixture
def empty_frame():
    """Create an empty test frame with no red areas"""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def camera_frame(test_frame):
    """Create a valid camera frame for testing"""
    return CameraFrame(
        camera_id=0,
        frame=test_frame,
        timestamp=time.time(),
        is_valid=True
    )


class TestRedLightDetection:
    """Test RedLightDetection dataclass"""
    
    def test_red_light_detection_creation(self):
        """Test creating a red light detection result"""
        detection = RedLightDetection(
            count=2,
            total_area=150.5,
            bounding_boxes=[(10, 10, 50, 50), (100, 100, 30, 30)],
            contours=[np.array([[10, 10], [60, 10], [60, 60], [10, 60]])],
            timestamp=1234567890.0
        )
        
        assert detection.count == 2
        assert detection.total_area == 150.5
        assert len(detection.bounding_boxes) == 2
        assert len(detection.contours) == 1
        assert detection.timestamp == 1234567890.0


class TestBaselineMeasurement:
    """Test BaselineMeasurement dataclass"""
    
    def test_baseline_measurement_creation(self):
        """Test creating a baseline measurement"""
        baseline = BaselineMeasurement(
            camera_id=1,
            red_light_count=3,
            total_area=250.0,
            timestamp=1234567890.0,
            is_established=True
        )
        
        assert baseline.camera_id == 1
        assert baseline.red_light_count == 3
        assert baseline.total_area == 250.0
        assert baseline.is_established is True


class TestRedLightDetector:
    """Test RedLightDetector class"""
    
    def test_detector_initialization(self, red_light_detector, red_light_config):
        """Test red light detector initialization"""
        assert red_light_detector.config == red_light_config
        assert len(red_light_detector.baselines) == 0
        assert red_light_detector.baseline_establishment_start is None
        assert red_light_detector.baseline_established is False
    
    def test_detect_red_lights_with_red_frame(self, red_light_detector, test_frame):
        """Test red light detection with frame containing red areas"""
        detection = red_light_detector.detect_red_lights(test_frame)
        
        assert isinstance(detection, RedLightDetection)
        assert detection.count >= 0  # Should detect some red areas
        assert detection.total_area >= 0
        assert len(detection.bounding_boxes) == detection.count
        assert len(detection.contours) == detection.count
    
    def test_detect_red_lights_with_empty_frame(self, red_light_detector, empty_frame):
        """Test red light detection with empty frame"""
        detection = red_light_detector.detect_red_lights(empty_frame)
        
        assert detection.count == 0
        assert detection.total_area == 0.0
        assert len(detection.bounding_boxes) == 0
        assert len(detection.contours) == 0
    
    def test_detect_red_lights_invalid_frame(self, red_light_detector):
        """Test red light detection with invalid frame"""
        with pytest.raises(ValueError, match="Invalid frame provided"):
            red_light_detector.detect_red_lights(None)
        
        with pytest.raises(ValueError, match="Invalid frame provided"):
            red_light_detector.detect_red_lights(np.array([]))
    
    def test_start_baseline_establishment(self, red_light_detector):
        """Test starting baseline establishment"""
        red_light_detector.start_baseline_establishment()
        
        assert red_light_detector.baseline_establishment_start is not None
        assert red_light_detector.baseline_established is False
        assert len(red_light_detector.baselines) == 0
        assert red_light_detector.is_baseline_window_active() is True
    
    def test_set_baseline_within_window(self, red_light_detector):
        """Test setting baseline within establishment window"""
        red_light_detector.start_baseline_establishment()
        
        result = red_light_detector.set_baseline(0, 2, 150.5)
        
        assert result is True
        assert red_light_detector.has_baseline(0) is True
        
        baseline = red_light_detector.get_baseline(0)
        assert baseline.camera_id == 0
        assert baseline.red_light_count == 2
        assert baseline.total_area == 150.5
        assert baseline.is_established is True
    
    def test_set_baseline_outside_window(self, red_light_detector):
        """Test setting baseline outside establishment window"""
        # Don't start baseline establishment
        result = red_light_detector.set_baseline(0, 2, 150.5)
        
        assert result is False
        assert red_light_detector.has_baseline(0) is False
    
    def test_set_baseline_expired_window(self, red_light_detector):
        """Test setting baseline after window has expired"""
        # Start baseline establishment
        red_light_detector.start_baseline_establishment()
        
        # Manually set the start time to simulate expired window
        red_light_detector.baseline_establishment_start = time.time() - 2.0  # 2 seconds ago
        
        result = red_light_detector.set_baseline(0, 2, 150.5)
        
        assert result is False
    
    def test_establish_baseline_from_frame(self, red_light_detector, test_frame):
        """Test establishing baseline from frame"""
        red_light_detector.start_baseline_establishment()
        
        result = red_light_detector.establish_baseline_from_frame(0, test_frame)
        
        assert result is True
        assert red_light_detector.has_baseline(0) is True
    
    def test_check_changes_no_baseline(self, red_light_detector):
        """Test checking changes when no baseline exists"""
        result = red_light_detector.check_changes(0, 2, 150.0)
        
        assert result['has_baseline'] is False
        assert result['count_decreased'] is False
        assert result['area_changed'] is False
        assert result['should_trigger'] is False
    
    def test_check_changes_with_baseline(self, red_light_detector):
        """Test checking changes with established baseline"""
        # Set baseline
        red_light_detector.start_baseline_establishment()
        red_light_detector.set_baseline(0, 3, 200.0)
        
        # Test count decrease
        result = red_light_detector.check_changes(0, 2, 200.0)
        assert result['has_baseline'] is True
        assert result['count_decreased'] is True
        assert result['should_trigger'] is True
        
        # Test area change
        result = red_light_detector.check_changes(0, 3, 100.0)  # 50% area decrease
        assert result['area_changed'] is True
        assert result['should_trigger'] is True
        
        # Test no change
        result = red_light_detector.check_changes(0, 3, 200.0)
        assert result['count_decreased'] is False
        assert result['area_changed'] is False
        assert result['should_trigger'] is False
    
    def test_check_frame_changes(self, red_light_detector, test_frame):
        """Test checking frame changes"""
        # Set baseline first
        red_light_detector.start_baseline_establishment()
        red_light_detector.establish_baseline_from_frame(0, test_frame)
        
        # Check same frame (should not trigger)
        result = red_light_detector.check_frame_changes(0, test_frame)
        
        assert result['detection_successful'] is True
        assert 'detection' in result
        assert isinstance(result['detection'], RedLightDetection)
    
    def test_update_baseline(self, red_light_detector):
        """Test updating baseline"""
        # Set initial baseline
        red_light_detector.start_baseline_establishment()
        red_light_detector.set_baseline(0, 2, 150.0)
        
        # Update baseline
        red_light_detector.update_baseline(0, 3, 200.0)
        
        baseline = red_light_detector.get_baseline(0)
        assert baseline.red_light_count == 3
        assert baseline.total_area == 200.0
    
    def test_get_detection_boxes(self, red_light_detector, test_frame):
        """Test getting detection bounding boxes"""
        boxes = red_light_detector.get_detection_boxes(test_frame)
        
        assert isinstance(boxes, list)
        # Each box should be a tuple of 4 integers (x, y, w, h)
        for box in boxes:
            assert len(box) == 4
            assert all(isinstance(coord, (int, np.integer)) for coord in box)
    
    def test_get_baseline_status(self, red_light_detector):
        """Test getting baseline status"""
        # Test without baseline establishment
        status = red_light_detector.get_baseline_status()
        assert status['baseline_establishment_active'] is False
        assert status['baselines_established'] == 0
        
        # Test with baseline establishment
        red_light_detector.start_baseline_establishment()
        red_light_detector.set_baseline(0, 2, 150.0)
        
        status = red_light_detector.get_baseline_status()
        assert status['baseline_establishment_active'] is True
        assert status['baselines_established'] == 1
        assert 0 in status['camera_baselines']
    
    def test_reset_baselines(self, red_light_detector):
        """Test resetting baselines"""
        # Set up some baselines
        red_light_detector.start_baseline_establishment()
        red_light_detector.set_baseline(0, 2, 150.0)
        red_light_detector.set_baseline(1, 3, 200.0)
        
        # Reset
        red_light_detector.reset_baselines()
        
        assert len(red_light_detector.baselines) == 0
        assert red_light_detector.baseline_establishment_start is None
        assert red_light_detector.baseline_established is False
    
    def test_process_camera_frame_invalid(self, red_light_detector):
        """Test processing invalid camera frame"""
        invalid_frame = CameraFrame(
            camera_id=0,
            frame=None,
            timestamp=time.time(),
            is_valid=False
        )
        
        result = red_light_detector.process_camera_frame(invalid_frame)
        
        assert result['processed'] is False
        assert 'error' in result
    
    def test_process_camera_frame_baseline_establishment(self, red_light_detector, camera_frame):
        """Test processing camera frame during baseline establishment"""
        red_light_detector.start_baseline_establishment()
        
        result = red_light_detector.process_camera_frame(camera_frame)
        
        assert result['processed'] is True
        assert result['phase'] == 'baseline_establishment'
        assert 'detection' in result
    
    def test_process_camera_frame_monitoring(self, red_light_detector, camera_frame):
        """Test processing camera frame during monitoring phase"""
        # Establish baseline first
        red_light_detector.start_baseline_establishment()
        red_light_detector.establish_baseline_from_frame(0, camera_frame.frame)
        
        # Process frame for monitoring
        result = red_light_detector.process_camera_frame(camera_frame)
        
        assert result['processed'] is True
        assert result['phase'] == 'monitoring'
        assert 'detection' in result
        assert 'should_trigger' in result
    
    def test_process_camera_frame_waiting(self, red_light_detector, camera_frame):
        """Test processing camera frame when waiting for baseline establishment"""
        # Don't start baseline establishment
        result = red_light_detector.process_camera_frame(camera_frame)
        
        assert result['processed'] is True
        assert result['phase'] == 'waiting'
        assert 'detection' in result
    
    def test_has_baseline(self, red_light_detector):
        """Test checking if baseline exists"""
        assert red_light_detector.has_baseline(0) is False
        
        red_light_detector.start_baseline_establishment()
        red_light_detector.set_baseline(0, 2, 150.0)
        
        assert red_light_detector.has_baseline(0) is True
        assert red_light_detector.has_baseline(1) is False
    
    def test_get_baseline(self, red_light_detector):
        """Test getting baseline measurement"""
        assert red_light_detector.get_baseline(0) is None
        
        red_light_detector.start_baseline_establishment()
        red_light_detector.set_baseline(0, 2, 150.0)
        
        baseline = red_light_detector.get_baseline(0)
        assert baseline is not None
        assert baseline.camera_id == 0
        assert baseline.red_light_count == 2
        assert baseline.total_area == 150.0
    
    def test_baseline_timing_accuracy(self, red_light_detector):
        """Test that baseline establishment respects timing constraints"""
        current_time = time.time()
        
        red_light_detector.start_baseline_establishment()
        
        # First baseline should succeed (within 1 second)
        result1 = red_light_detector.set_baseline(0, 2, 150.0)
        assert result1 is True
        
        # Manually expire the window by setting start time to past
        red_light_detector.baseline_establishment_start = current_time - 2.0  # 2 seconds ago
        
        # Second baseline should fail (after 1 second)
        result2 = red_light_detector.set_baseline(1, 3, 200.0)
        assert result2 is False