#!/usr/bin/env python3
"""
Property-based test for baseline reset on new message
**Feature: mqtt-camera-monitoring, Property 6: Baseline Reset on New Message**
"""

import pytest
import time
import json
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings
from hypothesis.strategies import composite
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from final_production_system import FinalProductionSystem, CameraState


@composite
def camera_states_with_baselines(draw):
    """Generate camera states with established baselines"""
    num_cameras = draw(st.integers(min_value=1, max_value=6))
    camera_states = {}
    
    for camera_id in range(num_cameras):
        baseline_count = draw(st.integers(min_value=0, max_value=20))
        current_count = draw(st.integers(min_value=0, max_value=20))
        last_reported = draw(st.integers(min_value=0, max_value=20))
        
        camera_states[camera_id] = {
            'baseline_red_count': baseline_count,
            'current_red_count': current_count,
            'last_reported_count': last_reported,
            'baseline_established': True,
            'baseline_time': time.time() - 10.0  # Established 10 seconds ago
        }
    
    return camera_states


@composite
def mqtt_message_data(draw):
    """Generate MQTT message data for testing"""
    # Generate state array
    state_array = draw(st.lists(st.integers(min_value=0, max_value=2), min_size=1, max_size=20))
    
    # Count ones in the array
    ones_count = state_array.count(1)
    
    # Generate message properties
    is_update = draw(st.booleans())
    
    return {
        'payload': {
            'state': state_array,
            'count_of_ones': ones_count
        },
        'is_update': is_update,
        'timestamp': time.time()
    }


class TestBaselineResetOnNewMessage:
    """Test baseline reset on new message property"""
    
    def setup_method(self):
        """Setup test environment"""
        pass
    
    @given(camera_states_with_baselines(), mqtt_message_data())
    @settings(max_examples=100, deadline=None)
    def test_new_changestate_update_resets_baselines(self, camera_states_data, message_data):
        """
        **Feature: mqtt-camera-monitoring, Property 6: Baseline Reset on New Message**
        For any new changeState update, the system should reset all baselines and restart monitoring cycles.
        **Validates: Requirements 2.4**
        """
        # Skip if not an update or if ones count is 144 (special case)
        if not message_data['is_update'] or message_data['payload']['count_of_ones'] == 144:
            return
        
        # Skip if ones count is 0 (another special case)
        if message_data['payload']['count_of_ones'] == 0:
            return
        
        # Create a real FinalProductionSystem instance for testing
        with patch('final_production_system.ConfigManager'), \
             patch('final_production_system.MQTTClient'), \
             patch('cv2.imread'), \
             patch('os.path.exists', return_value=True):
            
            system = FinalProductionSystem(enable_view=False)
            system.logger = Mock()
            
            # Set up camera states with established baselines
            for camera_id, state_data in camera_states_data.items():
                system.camera_states[camera_id] = CameraState(camera_id)
                system.camera_states[camera_id].baseline_red_count = state_data['baseline_red_count']
                system.camera_states[camera_id].current_red_count = state_data['current_red_count']
                system.camera_states[camera_id].last_reported_count = state_data['last_reported_count']
                system.camera_states[camera_id].baseline_established = state_data['baseline_established']
                system.camera_states[camera_id].baseline_time = state_data['baseline_time']
            
            # Verify baselines are initially established
            for camera_id in camera_states_data.keys():
                assert system.camera_states[camera_id].baseline_established, f"Camera {camera_id} baseline should be initially established"
                assert system.camera_states[camera_id].baseline_red_count >= 0, f"Camera {camera_id} should have valid baseline count"
            
            # Process the MQTT message
            system._handle_mqtt_message(message_data)
            
            # Verify all baselines are reset
            for camera_id in camera_states_data.keys():
                state = system.camera_states[camera_id]
                assert not state.baseline_established, f"Camera {camera_id} baseline should be reset after new message"
                assert state.baseline_red_count == -1, f"Camera {camera_id} baseline count should be reset to -1"
                assert state.current_red_count == -1, f"Camera {camera_id} current count should be reset to -1"
                assert state.last_reported_count == -1, f"Camera {camera_id} last reported count should be reset to -1"
                assert state.baseline_time == 0.0, f"Camera {camera_id} baseline time should be reset to 0.0"
                assert not state.stable_period_logged, f"Camera {camera_id} stable period logged should be reset"
    
    @given(camera_states_with_baselines())
    @settings(max_examples=100, deadline=None)
    def test_144_ones_invalidates_previous_baselines(self, camera_states_data):
        """
        **Feature: mqtt-camera-monitoring, Property 6: Baseline Reset on New Message**
        For any message with 144 ones, the system should invalidate previous baselines without establishing new ones.
        **Validates: Requirements 2.4**
        """
        # Create message with 144 ones
        message_data = {
            'payload': {
                'count_of_ones': 144,
                'state': [1] * 144
            },
            'is_update': True,
            'timestamp': time.time()
        }
        
        # Create a real FinalProductionSystem instance for testing
        with patch('final_production_system.ConfigManager'), \
             patch('final_production_system.MQTTClient'), \
             patch('cv2.imread'), \
             patch('os.path.exists', return_value=True):
            
            system = FinalProductionSystem(enable_view=False)
            system.logger = Mock()
            
            # Set up camera states with established baselines
            for camera_id, state_data in camera_states_data.items():
                system.camera_states[camera_id] = CameraState(camera_id)
                system.camera_states[camera_id].baseline_red_count = state_data['baseline_red_count']
                system.camera_states[camera_id].current_red_count = state_data['current_red_count']
                system.camera_states[camera_id].last_reported_count = state_data['last_reported_count']
                system.camera_states[camera_id].baseline_established = state_data['baseline_established']
                system.camera_states[camera_id].baseline_time = state_data['baseline_time']
            
            # Verify baselines are initially established
            for camera_id in camera_states_data.keys():
                assert system.camera_states[camera_id].baseline_established, f"Camera {camera_id} baseline should be initially established"
            
            # Process the 144 ones message
            system._handle_mqtt_message(message_data)
            
            # Verify all baselines are invalidated
            for camera_id in camera_states_data.keys():
                state = system.camera_states[camera_id]
                assert not state.baseline_established, f"Camera {camera_id} baseline should be invalidated by 144 ones"
                assert state.baseline_red_count == -1, f"Camera {camera_id} baseline count should be reset to -1"
                assert state.current_red_count == -1, f"Camera {camera_id} current count should be reset to -1"
                assert state.last_reported_count == -1, f"Camera {camera_id} last reported count should be reset to -1"
            
            # Verify system does not trigger baseline establishment
            assert not system.mqtt_triggered, "System should not trigger baseline establishment for 144 ones"
    
    @given(camera_states_with_baselines())
    @settings(max_examples=100, deadline=None)
    def test_zero_ones_skips_baseline_establishment(self, camera_states_data):
        """
        **Feature: mqtt-camera-monitoring, Property 6: Baseline Reset on New Message**
        For any message with 0 ones, the system should skip baseline establishment.
        **Validates: Requirements 2.4**
        """
        # Create message with 0 ones
        message_data = {
            'payload': {
                'count_of_ones': 0,
                'state': [0, 2, 0, 2]  # No ones
            },
            'is_update': True,
            'timestamp': time.time()
        }
        
        # Create a real FinalProductionSystem instance for testing
        with patch('final_production_system.ConfigManager'), \
             patch('final_production_system.MQTTClient'), \
             patch('cv2.imread'), \
             patch('os.path.exists', return_value=True):
            
            system = FinalProductionSystem(enable_view=False)
            system.logger = Mock()
            
            # Set up camera states with established baselines
            for camera_id, state_data in camera_states_data.items():
                system.camera_states[camera_id] = CameraState(camera_id)
                system.camera_states[camera_id].baseline_red_count = state_data['baseline_red_count']
                system.camera_states[camera_id].current_red_count = state_data['current_red_count']
                system.camera_states[camera_id].last_reported_count = state_data['last_reported_count']
                system.camera_states[camera_id].baseline_established = state_data['baseline_established']
                system.camera_states[camera_id].baseline_time = state_data['baseline_time']
            
            # Store initial baseline states
            initial_states = {}
            for camera_id in camera_states_data.keys():
                state = system.camera_states[camera_id]
                initial_states[camera_id] = {
                    'baseline_established': state.baseline_established,
                    'baseline_red_count': state.baseline_red_count,
                    'current_red_count': state.current_red_count,
                    'last_reported_count': state.last_reported_count
                }
            
            # Process the 0 ones message
            system._handle_mqtt_message(message_data)
            
            # Verify baselines remain unchanged (0 ones should be skipped)
            for camera_id in camera_states_data.keys():
                state = system.camera_states[camera_id]
                initial = initial_states[camera_id]
                
                # For 0 ones, the system should skip processing entirely
                # So baselines should remain as they were
                assert state.baseline_established == initial['baseline_established'], f"Camera {camera_id} baseline established should remain unchanged for 0 ones"
                assert state.baseline_red_count == initial['baseline_red_count'], f"Camera {camera_id} baseline count should remain unchanged for 0 ones"
            
            # Verify system does not trigger baseline establishment
            assert not system.mqtt_triggered, "System should not trigger baseline establishment for 0 ones"
    
    @given(camera_states_with_baselines())
    @settings(max_examples=100, deadline=None)
    def test_no_update_preserves_baselines(self, camera_states_data):
        """
        **Feature: mqtt-camera-monitoring, Property 6: Baseline Reset on New Message**
        For any message that is not an update (same content), baselines should be preserved.
        **Validates: Requirements 2.4**
        """
        # Create message that is not an update
        message_data = {
            'payload': {
                'count_of_ones': 5,  # Valid count, not 0 or 144
                'state': [1, 0, 1, 2, 1, 0, 1, 2, 1]
            },
            'is_update': False,  # Not an update
            'timestamp': time.time()
        }
        
        # Create a real FinalProductionSystem instance for testing
        with patch('final_production_system.ConfigManager'), \
             patch('final_production_system.MQTTClient'), \
             patch('cv2.imread'), \
             patch('os.path.exists', return_value=True):
            
            system = FinalProductionSystem(enable_view=False)
            system.logger = Mock()
            
            # Set up camera states with established baselines
            for camera_id, state_data in camera_states_data.items():
                system.camera_states[camera_id] = CameraState(camera_id)
                system.camera_states[camera_id].baseline_red_count = state_data['baseline_red_count']
                system.camera_states[camera_id].current_red_count = state_data['current_red_count']
                system.camera_states[camera_id].last_reported_count = state_data['last_reported_count']
                system.camera_states[camera_id].baseline_established = state_data['baseline_established']
                system.camera_states[camera_id].baseline_time = state_data['baseline_time']
            
            # Store initial baseline states
            initial_states = {}
            for camera_id in camera_states_data.keys():
                state = system.camera_states[camera_id]
                initial_states[camera_id] = {
                    'baseline_established': state.baseline_established,
                    'baseline_red_count': state.baseline_red_count,
                    'current_red_count': state.current_red_count,
                    'last_reported_count': state.last_reported_count,
                    'baseline_time': state.baseline_time
                }
            
            # Process the non-update message
            system._handle_mqtt_message(message_data)
            
            # Verify baselines are preserved (no update should skip processing)
            for camera_id in camera_states_data.keys():
                state = system.camera_states[camera_id]
                initial = initial_states[camera_id]
                
                assert state.baseline_established == initial['baseline_established'], f"Camera {camera_id} baseline established should be preserved for non-update"
                assert state.baseline_red_count == initial['baseline_red_count'], f"Camera {camera_id} baseline count should be preserved for non-update"
                assert state.current_red_count == initial['current_red_count'], f"Camera {camera_id} current count should be preserved for non-update"
                assert state.last_reported_count == initial['last_reported_count'], f"Camera {camera_id} last reported count should be preserved for non-update"
                assert state.baseline_time == initial['baseline_time'], f"Camera {camera_id} baseline time should be preserved for non-update"
            
            # Verify system does not trigger baseline establishment
            assert not system.mqtt_triggered, "System should not trigger baseline establishment for non-update"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])