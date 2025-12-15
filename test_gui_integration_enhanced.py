#!/usr/bin/env python3
"""
Test script for enhanced GUI integration with MQTT reliability components.
Tests the integration of connection manager, diagnostic tool, and health monitor.
"""

import sys
import os
import time
import logging
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gui_wrapper_initialization():
    """Test that the enhanced GUI wrapper initializes correctly"""
    try:
        from mqtt_camera_monitoring.gui_system_wrapper import GuiSystemWrapper
        
        logger.info("Testing GUI wrapper initialization...")
        
        # Create wrapper instance
        wrapper = GuiSystemWrapper("test_config.yaml")
        
        # Check that enhanced components are initialized
        assert hasattr(wrapper, 'diagnostic_tool'), "Diagnostic tool not initialized"
        assert hasattr(wrapper, 'health_monitor'), "Health monitor not initialized"
        assert hasattr(wrapper, 'connection_manager'), "Connection manager attribute missing"
        
        # Check that new methods are available
        assert hasattr(wrapper, 'run_manual_diagnostics'), "Manual diagnostics method missing"
        assert hasattr(wrapper, 'get_connection_statistics'), "Connection statistics method missing"
        assert hasattr(wrapper, 'trigger_manual_diagnostic_button'), "Manual diagnostic button method missing"
        
        logger.info("✓ GUI wrapper initialization test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ GUI wrapper initialization test failed: {e}")
        return False

def test_diagnostic_functionality():
    """Test diagnostic functionality"""
    try:
        from mqtt_camera_monitoring.gui_system_wrapper import GuiSystemWrapper
        
        logger.info("Testing diagnostic functionality...")
        
        wrapper = GuiSystemWrapper("test_config.yaml")
        
        # Mock the diagnostic tool to avoid actual network calls
        with patch.object(wrapper.diagnostic_tool, 'run_full_diagnostics') as mock_diagnostics:
            # Create a mock diagnostic report
            from mqtt_camera_monitoring.diagnostic_tool import DiagnosticReport, DiagnosticStatus
            from datetime import datetime
            
            mock_report = Mock()
            mock_report.is_successful = True
            mock_report.overall_status = Mock()
            mock_report.overall_status.value = "passed"
            mock_report.recommendations = ["系统配置正确"]
            mock_report.timestamp = datetime.now()
            mock_report.network_test = None
            mock_report.broker_test = None
            mock_report.config_validation = None
            
            mock_diagnostics.return_value = mock_report
            
            # Test manual diagnostics
            result = wrapper.run_manual_diagnostics()
            
            assert result is not None, "Diagnostic result is None"
            assert result.is_successful, "Diagnostic should be successful"
            
            # Test diagnostic report formatting
            formatted_report = wrapper.get_diagnostic_report_for_display()
            assert formatted_report['status'] == 'passed', "Formatted report status incorrect"
            
        logger.info("✓ Diagnostic functionality test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Diagnostic functionality test failed: {e}")
        return False

def test_connection_statistics():
    """Test connection statistics functionality"""
    try:
        from mqtt_camera_monitoring.gui_system_wrapper import GuiSystemWrapper
        
        logger.info("Testing connection statistics...")
        
        wrapper = GuiSystemWrapper("test_config.yaml")
        
        # Test getting connection statistics
        stats = wrapper.get_connection_statistics()
        
        assert isinstance(stats, dict), "Connection statistics should be a dictionary"
        
        # Check required fields
        required_fields = [
            'connection_state', 'health_status', 'uptime', 'message_success_rate',
            'average_latency', 'reconnection_count', 'error_count', 'quality_score'
        ]
        
        for field in required_fields:
            assert field in stats, f"Required field '{field}' missing from statistics"
        
        logger.info("✓ Connection statistics test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Connection statistics test failed: {e}")
        return False

def test_health_summary():
    """Test connection health summary functionality"""
    try:
        from mqtt_camera_monitoring.gui_system_wrapper import GuiSystemWrapper
        
        logger.info("Testing health summary...")
        
        wrapper = GuiSystemWrapper("test_config.yaml")
        
        # Test getting health summary
        summary = wrapper.get_connection_health_summary()
        
        assert isinstance(summary, dict), "Health summary should be a dictionary"
        
        # Check required fields
        required_fields = [
            'overall_status', 'connection_state', 'health_level', 'quality_score',
            'issues', 'recommendations', 'last_update'
        ]
        
        for field in required_fields:
            assert field in summary, f"Required field '{field}' missing from health summary"
        
        logger.info("✓ Health summary test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Health summary test failed: {e}")
        return False

def test_callback_setup():
    """Test that monitoring callbacks are set up correctly"""
    try:
        from mqtt_camera_monitoring.gui_system_wrapper import GuiSystemWrapper
        
        logger.info("Testing callback setup...")
        
        wrapper = GuiSystemWrapper("test_config.yaml")
        
        # Test setting status callbacks
        test_callback = Mock()
        wrapper.set_status_callback('test_callback', test_callback)
        
        assert 'test_callback' in wrapper.status_callbacks, "Status callback not set"
        assert wrapper.status_callbacks['test_callback'] == test_callback, "Status callback not stored correctly"
        
        # Check that health monitor has callbacks
        assert len(wrapper.health_monitor.status_callbacks) > 0, "Health monitor status callbacks not set"
        assert len(wrapper.health_monitor.quality_callbacks) > 0, "Health monitor quality callbacks not set"
        assert len(wrapper.health_monitor.report_callbacks) > 0, "Health monitor report callbacks not set"
        
        logger.info("✓ Callback setup test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Callback setup test failed: {e}")
        return False

def test_mqtt_configuration_validation():
    """Test MQTT configuration validation with enhanced reliability"""
    try:
        from mqtt_camera_monitoring.gui_system_wrapper import GuiSystemWrapper
        
        logger.info("Testing MQTT configuration validation...")
        
        wrapper = GuiSystemWrapper("test_config.yaml")
        
        # Mock the diagnostic tool validation
        with patch.object(wrapper.diagnostic_tool, 'run_full_diagnostics') as mock_diagnostics:
            # Create a mock successful validation
            mock_report = Mock()
            mock_report.is_successful = True
            mock_diagnostics.return_value = mock_report
            
            # Test valid configuration
            valid_config = {
                'broker_host': '192.168.1.100',
                'broker_port': 1883,
                'client_id': 'test_client'
            }
            
            result = wrapper.update_mqtt_configuration(valid_config)
            assert result == True, "Valid MQTT configuration should be accepted"
            
            # Test that configuration was stored
            effective_config = wrapper.get_effective_mqtt_config()
            assert effective_config['broker_host'] == '192.168.1.100', "MQTT configuration not updated"
            
        logger.info("✓ MQTT configuration validation test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ MQTT configuration validation test failed: {e}")
        return False

def main():
    """Run all integration tests"""
    logger.info("Starting enhanced GUI integration tests...")
    
    tests = [
        test_gui_wrapper_initialization,
        test_diagnostic_functionality,
        test_connection_statistics,
        test_health_summary,
        test_callback_setup,
        test_mqtt_configuration_validation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Test {test.__name__} crashed: {e}")
            failed += 1
    
    logger.info(f"\nTest Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        logger.info("🎉 All enhanced GUI integration tests passed!")
        return True
    else:
        logger.error(f"❌ {failed} tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)