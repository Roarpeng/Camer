#!/usr/bin/env python3
"""
Test GUI Log Integration

Tests the log management integration in the GUI system wrapper.
"""

import os
import sys
import tempfile
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mqtt_camera_monitoring.gui_system_wrapper import GuiSystemWrapper
from mqtt_camera_monitoring.data_models import LogLevel, LogCategory


def test_gui_wrapper_log_methods():
    """Test that GUI wrapper has log management methods"""
    print("Testing GUI wrapper log methods...")
    
    # Create a temporary config file
    temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
    temp_config.write("""
mqtt:
  broker_host: "localhost"
  broker_port: 1883
  client_id: "test_client"
  subscribe_topic: "test/topic"
  publish_topic: "test/publish"

cameras: []
""")
    temp_config.close()
    
    try:
        # Mock the path utilities to avoid file system issues
        with patch('mqtt_camera_monitoring.gui_system_wrapper.ensure_config_in_exe_dir') as mock_ensure:
            mock_ensure.return_value = temp_config.name
            
            wrapper = GuiSystemWrapper(temp_config.name)
            
            # Test that log management components are initialized
            assert hasattr(wrapper, 'log_manager'), "Should have log_manager attribute"
            assert hasattr(wrapper, 'log_viewer'), "Should have log_viewer attribute"
            assert hasattr(wrapper, 'log_viewer_gui'), "Should have log_viewer_gui attribute"
            
            # Test log management methods exist
            methods_to_test = [
                'log_connection_event',
                'log_performance_event', 
                'log_error_with_context',
                'search_logs',
                'get_recent_logs',
                'get_log_table_headers',
                'get_log_entry_details',
                'get_error_summary',
                'get_log_statistics',
                'export_logs',
                'start_log_auto_refresh',
                'stop_log_auto_refresh',
                'cleanup_old_logs',
                'compress_rotated_logs',
                'get_log_search_interface_data'
            ]
            
            for method_name in methods_to_test:
                assert hasattr(wrapper, method_name), f"Should have {method_name} method"
                assert callable(getattr(wrapper, method_name)), f"{method_name} should be callable"
            
            # Test basic log functionality
            entry_id = wrapper.log_connection_event(
                event_type="test_connect",
                connection_state="connected",
                details={"test": "value"}
            )
            
            assert entry_id, "Should return log entry ID"
            
            # Test recent logs
            recent_logs = wrapper.get_recent_logs(10)
            assert isinstance(recent_logs, list), "Should return list of logs"
            
            # Test table headers
            headers = wrapper.get_log_table_headers()
            assert isinstance(headers, list), "Should return list of headers"
            assert len(headers) > 0, "Should have at least one header"
            
            # Test error summary
            error_summary = wrapper.get_error_summary(24)
            assert isinstance(error_summary, dict), "Should return error summary dict"
            
            # Test log statistics
            stats = wrapper.get_log_statistics()
            assert isinstance(stats, dict), "Should return statistics dict"
            
            # Test search interface data
            search_data = wrapper.get_log_search_interface_data()
            assert isinstance(search_data, dict), "Should return search interface data"
            assert 'log_levels' in search_data, "Should have log_levels"
            assert 'categories' in search_data, "Should have categories"
            
            # Clean up
            wrapper.shutdown()
            
            print("✓ GUI wrapper log methods test passed")
            
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_config.name)
        except:
            pass


def test_log_integration_in_callbacks():
    """Test that log integration works in system callbacks"""
    print("Testing log integration in callbacks...")
    
    temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
    temp_config.write("""
mqtt:
  broker_host: "localhost"
  broker_port: 1883
  client_id: "test_client"
  subscribe_topic: "test/topic"
  publish_topic: "test/publish"

cameras: []
""")
    temp_config.close()
    
    try:
        with patch('mqtt_camera_monitoring.gui_system_wrapper.ensure_config_in_exe_dir') as mock_ensure:
            mock_ensure.return_value = temp_config.name
            
            wrapper = GuiSystemWrapper(temp_config.name)
            
            # Test error logging with context
            test_error = ValueError("Test error for logging")
            entry_id = wrapper.log_error_with_context(
                component="test_component",
                error=test_error,
                context={"test_context": "value"},
                user_action="test_action"
            )
            
            assert entry_id, "Should log error with context"
            
            # Test performance logging
            perf_entry_id = wrapper.log_performance_event(
                metric_name="test_metric",
                metric_value=100.0,
                threshold=50.0,
                details={"unit": "ms"}
            )
            
            assert perf_entry_id, "Should log performance event"
            
            # Verify logs are in memory
            recent_logs = wrapper.get_recent_logs(10)
            assert len(recent_logs) > 0, "Should have recent logs"
            
            wrapper.shutdown()
            
            print("✓ Log integration in callbacks test passed")
            
    finally:
        try:
            os.unlink(temp_config.name)
        except:
            pass


def test_log_search_functionality():
    """Test log search functionality in GUI wrapper"""
    print("Testing log search functionality...")
    
    temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
    temp_config.write("""
mqtt:
  broker_host: "localhost"
  broker_port: 1883
  client_id: "test_client"
  subscribe_topic: "test/topic"
  publish_topic: "test/publish"

cameras: []
""")
    temp_config.close()
    
    try:
        with patch('mqtt_camera_monitoring.gui_system_wrapper.ensure_config_in_exe_dir') as mock_ensure:
            mock_ensure.return_value = temp_config.name
            
            wrapper = GuiSystemWrapper(temp_config.name)
            
            # Add some test logs
            wrapper.log_connection_event("connect", "connected", {"test": "connection"})
            wrapper.log_performance_event("latency", 150.0, 100.0, {"unit": "ms"})
            
            # Test search by text
            search_results = wrapper.search_logs(
                search_text="connection",
                max_results=10
            )
            
            assert isinstance(search_results, list), "Should return list of search results"
            
            # Test search by level
            search_results = wrapper.search_logs(
                level_filter=LogLevel.WARNING,
                max_results=10
            )
            
            assert isinstance(search_results, list), "Should return list for level filter"
            
            # Test search by category
            search_results = wrapper.search_logs(
                category_filter=LogCategory.CONNECTION,
                max_results=10
            )
            
            assert isinstance(search_results, list), "Should return list for category filter"
            
            wrapper.shutdown()
            
            print("✓ Log search functionality test passed")
            
    finally:
        try:
            os.unlink(temp_config.name)
        except:
            pass


def run_all_tests():
    """Run all GUI log integration tests"""
    print("Running GUI log integration tests...")
    print("=" * 50)
    
    try:
        test_gui_wrapper_log_methods()
        test_log_integration_in_callbacks()
        test_log_search_functionality()
        
        print("=" * 50)
        print("✓ All GUI log integration tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)