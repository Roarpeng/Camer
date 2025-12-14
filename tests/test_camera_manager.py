"""
Unit and property tests for Camera Manager component
"""

import pytest
import numpy as np
import cv2
from unittest.mock import Mock, patch, MagicMock
from mqtt_camera_monitoring.camera_manager import CameraManager, CameraFrame
from mqtt_camera_monitoring.config import CameraConfig


@pytest.fixture
def camera_config():
    """Create a test camera configuration"""
    return CameraConfig(
        count=2,
        resolution_width=640,
        resolution_height=480,
        fps=30,
        buffer_size=1,
        brightness=50,
        exposure=100,
        contrast=50,
        saturation=50,
        auto_exposure=True
    )


@pytest.fixture
def camera_manager(camera_config):
    """Create a camera manager instance for testing"""
    return CameraManager(camera_config)


class TestCameraFrame:
    """Test CameraFrame dataclass"""
    
    def test_camera_frame_creation(self):
        """Test creating a camera frame"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        camera_frame = CameraFrame(
            camera_id=0,
            frame=frame,
            timestamp=1234567890.0,
            is_valid=True
        )
        
        assert camera_frame.camera_id == 0
        assert camera_frame.frame.shape == (480, 640, 3)
        assert camera_frame.timestamp == 1234567890.0
        assert camera_frame.is_valid is True
    
    def test_camera_frame_copy(self):
        """Test copying a camera frame"""
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 255
        original = CameraFrame(
            camera_id=1,
            frame=frame,
            timestamp=1234567890.0,
            is_valid=True
        )
        
        copied = original.copy()
        
        assert copied.camera_id == original.camera_id
        assert copied.timestamp == original.timestamp
        assert copied.is_valid == original.is_valid
        assert np.array_equal(copied.frame, original.frame)
        
        # Verify it's a deep copy
        copied.frame[0, 0, 0] = 0
        assert not np.array_equal(copied.frame, original.frame)


class TestCameraManager:
    """Test CameraManager class"""
    
    def test_camera_manager_initialization(self, camera_manager, camera_config):
        """Test camera manager initialization"""
        assert camera_manager.config == camera_config
        assert camera_manager.cameras == []
        assert camera_manager.active_cameras == []
        assert camera_manager.capture_active is False
    
    @patch('cv2.VideoCapture')
    @patch('cv2.namedWindow')
    @patch('cv2.resizeWindow')
    def test_initialize_cameras_success(self, mock_resize, mock_window, mock_capture, camera_manager):
        """Test successful camera initialization"""
        # Mock successful camera capture
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_capture.return_value = mock_cap
        
        result = camera_manager.initialize_cameras()
        
        assert result == [0, 1]  # Both cameras should be initialized
        assert len(camera_manager.cameras) == 2
        assert all(camera_manager.active_cameras)
        assert mock_capture.call_count == 2
    
    @patch('cv2.VideoCapture')
    def test_initialize_cameras_failure(self, mock_capture, camera_manager):
        """Test camera initialization with failures"""
        # Mock failed camera capture
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_capture.return_value = mock_cap
        
        with pytest.raises(RuntimeError, match="No cameras could be initialized"):
            camera_manager.initialize_cameras()
    
    @patch('cv2.VideoCapture')
    @patch('cv2.namedWindow')
    @patch('cv2.resizeWindow')
    def test_initialize_cameras_partial_success(self, mock_resize, mock_window, mock_capture, camera_manager):
        """Test camera initialization with partial success"""
        def mock_capture_side_effect(camera_id):
            mock_cap = Mock()
            if camera_id == 0:
                # First camera succeeds
                mock_cap.isOpened.return_value = True
                mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
            else:
                # Second camera fails
                mock_cap.isOpened.return_value = False
            return mock_cap
        
        mock_capture.side_effect = mock_capture_side_effect
        
        result = camera_manager.initialize_cameras()
        
        assert result == [0]  # Only first camera should be initialized
        assert len(camera_manager.cameras) == 2
        assert camera_manager.active_cameras == [True, False]
    
    def test_get_active_camera_ids(self, camera_manager):
        """Test getting active camera IDs"""
        camera_manager.active_cameras = [True, False, True, False]
        
        result = camera_manager.get_active_camera_ids()
        
        assert result == [0, 2]
    
    def test_set_brightness(self, camera_manager):
        """Test setting brightness"""
        # Mock cameras
        mock_cap1 = Mock()
        mock_cap2 = Mock()
        camera_manager.cameras = [mock_cap1, mock_cap2]
        camera_manager.active_cameras = [True, True]
        
        camera_manager.set_brightness(75)
        
        assert camera_manager.config.brightness == 75
    
    def test_set_brightness_invalid_value(self, camera_manager):
        """Test setting invalid brightness value"""
        original_brightness = camera_manager.config.brightness
        
        camera_manager.set_brightness(150)  # Invalid value
        
        assert camera_manager.config.brightness == original_brightness  # Should not change
    
    def test_update_parameters(self, camera_manager):
        """Test updating camera parameters"""
        # Mock cameras
        mock_cap = Mock()
        camera_manager.cameras = [mock_cap]
        camera_manager.active_cameras = [True]
        
        new_params = {
            'brightness': 80,
            'exposure': 200,
            'contrast': 60,
            'saturation': 70
        }
        
        camera_manager.update_parameters(new_params)
        
        assert camera_manager.config.brightness == 80
        assert camera_manager.config.exposure == 200
        assert camera_manager.config.contrast == 60
        assert camera_manager.config.saturation == 70
    
    def test_get_camera_status(self, camera_manager):
        """Test getting camera status"""
        camera_manager.active_cameras = [True, False, True]
        
        result = camera_manager.get_camera_status()
        
        expected = {0: True, 1: False, 2: True}
        assert result == expected
    
    @patch('cv2.destroyAllWindows')
    def test_release_cameras(self, mock_destroy, camera_manager):
        """Test releasing camera resources"""
        # Mock cameras
        mock_cap1 = Mock()
        mock_cap2 = Mock()
        camera_manager.cameras = [mock_cap1, mock_cap2]
        camera_manager.active_cameras = [True, True]
        camera_manager.capture_active = True
        
        camera_manager.release_cameras()
        
        assert camera_manager.capture_active is False
        mock_cap1.release.assert_called_once()
        mock_cap2.release.assert_called_once()
        mock_destroy.assert_called_once()
        assert len(camera_manager.cameras) == 0
    
    def test_cleanup_frame_buffers(self, camera_manager):
        """Test cleaning up frame buffers"""
        # Set up some mock frames
        camera_manager.cameras = [Mock(), Mock()]
        camera_manager.current_frames = [Mock(), Mock()]
        
        camera_manager.cleanup_frame_buffers()
        
        assert len(camera_manager.current_frames) == 2
        assert all(frame is None for frame in camera_manager.current_frames)
    
    def test_activate_on_mqtt_update_success(self, camera_manager):
        """Test successful camera activation on MQTT update"""
        # Mock cameras
        mock_cap = Mock()
        camera_manager.cameras = [mock_cap]
        camera_manager.active_cameras = [True]
        
        # Mock callback
        callback_called = []
        def test_callback():
            callback_called.append(True)
        
        camera_manager.set_activation_callback(test_callback)
        
        result = camera_manager.activate_on_mqtt_update()
        
        assert result is True
        assert camera_manager.is_activation_triggered() is True
        assert len(callback_called) == 1
    
    def test_activate_on_mqtt_update_no_cameras(self, camera_manager):
        """Test activation when no cameras are active"""
        camera_manager.active_cameras = [False, False]
        
        result = camera_manager.activate_on_mqtt_update()
        
        assert result is False
        assert camera_manager.is_activation_triggered() is False
    
    def test_activation_callback_management(self, camera_manager):
        """Test setting and using activation callback"""
        callback_called = []
        def test_callback():
            callback_called.append(True)
        
        camera_manager.set_activation_callback(test_callback)
        
        # Mock cameras for activation
        camera_manager.cameras = [Mock()]
        camera_manager.active_cameras = [True]
        
        camera_manager.activate_on_mqtt_update()
        
        assert len(callback_called) == 1
    
    def test_activation_trigger_reset(self, camera_manager):
        """Test resetting activation trigger"""
        camera_manager.activation_triggered = True
        
        camera_manager.reset_activation_trigger()
        
        assert camera_manager.is_activation_triggered() is False
    
    def test_get_activation_status(self, camera_manager):
        """Test getting activation status"""
        camera_manager.cameras = [Mock(), Mock()]
        camera_manager.active_cameras = [True, False]
        camera_manager.capture_active = True
        camera_manager.activation_triggered = True
        camera_manager.activation_callback = lambda: None
        
        status = camera_manager.get_activation_status()
        
        assert status['capture_active'] is True
        assert status['activation_triggered'] is True
        assert status['active_camera_count'] == 1
        assert status['total_cameras'] == 2
        assert status['has_activation_callback'] is True
    
    def test_get_frame_buffer_status(self, camera_manager):
        """Test getting frame buffer status"""
        # Mock frame with numpy array
        mock_frame = Mock()
        mock_frame.is_valid = True
        mock_frame.frame = Mock()
        mock_frame.frame.nbytes = 1024
        
        camera_manager.current_frames = [mock_frame, None]
        camera_manager.capture_active = True
        
        status = camera_manager.get_frame_buffer_status()
        
        assert status['total_buffers'] == 2
        assert status['valid_frames'] == 1
        assert status['memory_usage_bytes'] == 1024
        assert status['capture_active'] is True
    
    def test_handle_mqtt_message_update_with_update(self, camera_manager):
        """Test handling MQTT message with update"""
        # Setup mock cameras
        camera_manager.cameras = [Mock()]
        camera_manager.active_cameras = [True]
        
        message_data = {
            'topic': 'changeState',
            'payload': {'state': [1, 0, 1], 'count_of_ones': 2},
            'is_update': True,
            'timestamp': 1234567890.0
        }
        
        result = camera_manager.handle_mqtt_message_update(message_data)
        
        assert result is True
        assert camera_manager.is_activation_triggered() is True
    
    def test_handle_mqtt_message_update_without_update(self, camera_manager):
        """Test handling MQTT message without update"""
        message_data = {
            'topic': 'changeState',
            'payload': {'state': [1, 0, 1], 'count_of_ones': 2},
            'is_update': False,
            'timestamp': 1234567890.0
        }
        
        result = camera_manager.handle_mqtt_message_update(message_data)
        
        assert result is True
        assert camera_manager.is_activation_triggered() is False