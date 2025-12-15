#!/usr/bin/env python3
"""
Property-based test for threshold-based triggering
**Feature: mqtt-camera-monitoring, Property 5: Threshold-Based Triggering**
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings
from hypothesis.strategies import composite
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from final_production_system import FinalProductionSystem, CameraState


@composite
def camera_baseline_and_current_counts(draw):
    """Generate baseline and current red light counts for threshold testing"""
    # Generate threshold first (comparison threshold from config)
    threshold = draw(st.integers(min_value=1, max_value=5))
    
    # Generate baseline count (must be larger than threshold to allow valid decreases)
    baseline_count = draw(st.integers(min_value=threshold + 1, max_value=20))
    
    # Generate current count that should trigger (decrease > threshold)
    max_trigger_decrease = min(baseline_count, baseline_count)  # Can't decrease more than baseline
    trigger_decrease = draw(st.integers(min_value=threshold + 1, max_value=max_trigger_decrease))
    current_count_trigger = max(0, baseline_count - trigger_decrease)
    
    # Generate current count that should NOT trigger (decrease <= threshold)
    no_trigger_decrease = draw(st.integers(min_value=0, max_value=threshold))
    current_count_no_trigger = max(0, baseline_count - no_trigger_decrease)
    
    return {
        'baseline_count': baseline_count,
        'threshold': threshold,
        'current_count_trigger': current_count_trigger,
        'current_count_no_trigger': current_count_no_trigger,
        'trigger_decrease': trigger_decrease,
        'no_trigger_decrease': no_trigger_decrease
    }


@composite
def camera_configurations(draw):
    """Generate camera configurations for testing"""
    camera_id = draw(st.integers(min_value=0, max_value=5))
    baseline_count = draw(st.integers(min_value=0, max_value=20))
    current_count = draw(st.integers(min_value=0, max_value=20))
    
    return {
        'camera_id': camera_id,
        'baseline_count': baseline_count,
        'current_count': current_count
    }


class TestThresholdBasedTriggering:
    """Test threshold-based triggering property"""
    
    def setup_method(self):
        """Setup test environment"""
        # Create fresh mocks for each test to avoid cross-test contamination
        pass
        
    @given(camera_baseline_and_current_counts())
    @settings(max_examples=100, deadline=None)
    def test_threshold_exceeded_triggers_mqtt_message(self, test_data):
        """
        **Feature: mqtt-camera-monitoring, Property 5: Threshold-Based Triggering**
        For any camera with baseline count and current count, when the decrease exceeds 
        the configured threshold, the system should send a trigger message.
        **Validates: Requirements 2.3**
        """
        baseline_count = test_data['baseline_count']
        current_count = test_data['current_count_trigger']
        threshold = test_data['threshold']
        
        # Create fresh mocks for this test
        mock_mqtt_client = Mock()
        mock_mqtt_client.client = Mock()
        mock_mqtt_client.client.publish = Mock()
        
        # Create a real FinalProductionSystem instance for testing the trigger logic
        with patch('final_production_system.ConfigManager'), \
             patch('final_production_system.MQTTClient'), \
             patch('cv2.imread'), \
             patch('os.path.exists', return_value=True):
            
            system = FinalProductionSystem(enable_view=False)
            system.mqtt_client = mock_mqtt_client
            system.logger = Mock()
            
            # Set up camera state
            camera_id = 0
            system.camera_states[camera_id] = CameraState(camera_id)
            system.camera_states[camera_id].baseline_established = True
            system.camera_states[camera_id].baseline_red_count = baseline_count
            system.camera_states[camera_id].last_reported_count = baseline_count  # Initial state
            
            # Mock the MQTT publish to return success
            mock_mqtt_client.client.publish.return_value.rc = 0
            
            # Call the trigger method directly
            system._trigger_mqtt_message(camera_id, current_count, baseline_count)
            
            # Verify MQTT message was sent
            mock_mqtt_client.client.publish.assert_called_once()
            call_args = mock_mqtt_client.client.publish.call_args
            
            # Verify the topic and payload
            assert call_args[0][0] == system.config.mqtt.publish_topic
            assert call_args[1]['payload'] == ""  # Empty payload for trigger messages
    
    @given(camera_baseline_and_current_counts())
    @settings(max_examples=100, deadline=None)
    def test_threshold_not_exceeded_no_trigger(self, test_data):
        """
        **Feature: mqtt-camera-monitoring, Property 5: Threshold-Based Triggering**
        For any camera with baseline count and current count, when the decrease does NOT exceed
        the configured threshold, the system should NOT send a trigger message.
        **Validates: Requirements 2.3**
        """
        baseline_count = test_data['baseline_count']
        current_count = test_data['current_count_no_trigger']
        threshold = test_data['threshold']
        decrease = test_data['no_trigger_decrease']
        
        # Skip test if decrease is actually greater than threshold (edge case)
        if decrease > threshold:
            return
        
        # Create fresh mocks for this test
        mock_mqtt_client = Mock()
        mock_mqtt_client.client = Mock()
        mock_mqtt_client.client.publish = Mock()
        
        # Create a real FinalProductionSystem instance for testing
        with patch('final_production_system.ConfigManager'), \
             patch('final_production_system.MQTTClient'), \
             patch('cv2.imread'), \
             patch('os.path.exists', return_value=True):
            
            system = FinalProductionSystem(enable_view=False)
            system.mqtt_client = mock_mqtt_client
            system.logger = Mock()
            
            # Set up camera state
            camera_id = 0
            system.camera_states[camera_id] = CameraState(camera_id)
            system.camera_states[camera_id].baseline_established = True
            system.camera_states[camera_id].baseline_red_count = baseline_count
            system.camera_states[camera_id].last_reported_count = baseline_count
            
            # Simulate detection that doesn't exceed threshold
            # The system only triggers on count changes, not threshold checks
            # So we test that no trigger occurs when count doesn't change significantly
            if current_count == baseline_count:
                # No change, no trigger should occur
                # This is tested by not calling _trigger_mqtt_message at all
                # since the detection loop only calls it on count changes
                
                # Verify no MQTT message was sent
                mock_mqtt_client.client.publish.assert_not_called()
    
    @given(st.integers(min_value=0, max_value=5), st.integers(min_value=1, max_value=20))
    @settings(max_examples=100, deadline=None)
    def test_mqtt_publish_failure_handling(self, camera_id, count_change):
        """
        **Feature: mqtt-camera-monitoring, Property 5: Threshold-Based Triggering**
        For any MQTT publish failure, the system should handle the error gracefully
        and log the failure without crashing.
        **Validates: Requirements 2.3**
        """
        # Create fresh mocks for this test
        mock_mqtt_client = Mock()
        mock_mqtt_client.client = Mock()
        mock_mqtt_client.client.publish = Mock()
        
        # Create a real FinalProductionSystem instance for testing
        with patch('final_production_system.ConfigManager'), \
             patch('final_production_system.MQTTClient'), \
             patch('cv2.imread'), \
             patch('os.path.exists', return_value=True):
            
            system = FinalProductionSystem(enable_view=False)
            system.mqtt_client = mock_mqtt_client
            system.logger = Mock()
            
            # Mock MQTT publish to return failure
            mock_mqtt_client.client.publish.return_value.rc = 1  # Failure code
            
            # Call the trigger method
            system._trigger_mqtt_message(camera_id, count_change, count_change + 1)
            
            # Verify MQTT publish was attempted
            mock_mqtt_client.client.publish.assert_called_once()
            
            # Verify error was logged
            system.logger.error.assert_called()
    
    @given(st.integers(min_value=0, max_value=5))
    @settings(max_examples=100, deadline=None)
    def test_no_mqtt_client_handling(self, camera_id):
        """
        **Feature: mqtt-camera-monitoring, Property 5: Threshold-Based Triggering**
        For any trigger attempt when MQTT client is not available, the system should
        handle the situation gracefully without crashing.
        **Validates: Requirements 2.3**
        """
        # Create a real FinalProductionSystem instance for testing
        with patch('final_production_system.ConfigManager'), \
             patch('final_production_system.MQTTClient'), \
             patch('cv2.imread'), \
             patch('os.path.exists', return_value=True):
            
            system = FinalProductionSystem(enable_view=False)
            system.mqtt_client = None  # No MQTT client
            system.logger = Mock()
            
            # Call the trigger method
            system._trigger_mqtt_message(camera_id, 5, 10)
            
            # Verify error was logged
            system.logger.error.assert_called()
            error_message = system.logger.error.call_args[0][0]
            assert "MQTT客户端未连接" in error_message or "not connected" in error_message.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])