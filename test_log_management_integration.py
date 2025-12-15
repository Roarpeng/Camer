#!/usr/bin/env python3
"""
Test Log Management Integration

Tests the enhanced log management system integration in the GUI system wrapper.
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mqtt_camera_monitoring.log_manager import EnhancedLogManager, LogSearchFilter
from mqtt_camera_monitoring.log_viewer import LogViewerInterface, LogViewerGUI
from mqtt_camera_monitoring.data_models import LogLevel, LogCategory


def test_log_manager_initialization():
    """Test that the log manager initializes correctly"""
    print("Testing log manager initialization...")
    
    temp_dir = tempfile.mkdtemp()
    try:
        log_manager = EnhancedLogManager(
            log_directory=temp_dir,
            max_file_size=1024 * 1024,  # 1MB
            backup_count=3,
            compression_enabled=True,
            memory_buffer_size=100
        )
        
        # Test basic logging
        entry_id = log_manager.log_event(
            level=LogLevel.INFO,
            category=LogCategory.SYSTEM,
            component="test",
            message="Test log entry",
            details={"test": "value"}
        )
        
        assert entry_id, "Log entry ID should be returned"
        
        # Test memory buffer
        recent_logs = log_manager.get_recent_logs(10)
        assert len(recent_logs) > 0, "Should have recent logs in memory buffer"
        assert recent_logs[0].message == "Test log entry", "Log message should match"
        
        log_manager.shutdown()
        print("✓ Log manager initialization test passed")
        
    finally:
        # Clean up manually with retry
        import time
        for i in range(3):
            try:
                shutil.rmtree(temp_dir)
                break
            except PermissionError:
                time.sleep(0.1)
                continue


def test_log_viewer_integration():
    """Test that the log viewer integrates correctly with log manager"""
    print("Testing log viewer integration...")
    
    temp_dir = tempfile.mkdtemp()
    try:
        log_manager = EnhancedLogManager(log_directory=temp_dir)
        log_viewer = LogViewerInterface(log_manager)
        log_viewer_gui = LogViewerGUI(log_viewer)
        
        # Add some test log entries
        log_manager.log_event(
            level=LogLevel.INFO,
            category=LogCategory.CONNECTION,
            component="mqtt_client",
            message="Connection established"
        )
        
        log_manager.log_event(
            level=LogLevel.ERROR,
            category=LogCategory.ERROR,
            component="camera_manager",
            message="Camera initialization failed"
        )
        
        # Test search functionality
        display_entries = log_viewer.search_and_display(
            search_text="connection",
            max_results=10
        )
        
        assert len(display_entries) > 0, "Should find connection-related logs"
        
        # Test GUI table format
        table_data = log_viewer_gui.get_display_data_for_table()
        headers = log_viewer_gui.get_table_headers()
        
        assert len(headers) > 0, "Should have table headers"
        assert len(table_data) > 0, "Should have table data"
        
        log_manager.shutdown()
        print("✓ Log viewer integration test passed")
        
    finally:
        import time
        for i in range(3):
            try:
                shutil.rmtree(temp_dir)
                break
            except PermissionError:
                time.sleep(0.1)
                continue


def test_connection_event_logging():
    """Test connection event logging functionality"""
    print("Testing connection event logging...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        log_manager = EnhancedLogManager(log_directory=temp_dir)
        
        # Test connection event logging
        entry_id = log_manager.log_connection_event(
            event_type="connect",
            connection_state="connected",
            details={"broker": "192.168.1.100", "port": 1883},
            error_message=None
        )
        
        assert entry_id, "Connection event should be logged"
        
        # Test error connection event
        error_entry_id = log_manager.log_connection_event(
            event_type="connect_failed",
            connection_state="disconnected",
            details={"broker": "192.168.1.100", "port": 1883},
            error_message="Connection timeout"
        )
        
        assert error_entry_id, "Error connection event should be logged"
        
        # Verify logs are in memory buffer
        recent_logs = log_manager.get_recent_logs(10)
        connection_logs = [log for log in recent_logs if log.category == LogCategory.CONNECTION]
        
        assert len(connection_logs) >= 2, "Should have connection logs"
        
        log_manager.shutdown()
        print("✓ Connection event logging test passed")


def test_performance_event_logging():
    """Test performance event logging functionality"""
    print("Testing performance event logging...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        log_manager = EnhancedLogManager(log_directory=temp_dir)
        
        # Test performance event logging
        entry_id = log_manager.log_performance_event(
            metric_name="connection_latency",
            metric_value=150.5,
            threshold=100.0,
            details={"unit": "ms", "measurement_time": datetime.now().isoformat()}
        )
        
        assert entry_id, "Performance event should be logged"
        
        # Verify log level is WARNING due to threshold exceeded
        recent_logs = log_manager.get_recent_logs(10)
        perf_logs = [log for log in recent_logs if log.category == LogCategory.PERFORMANCE]
        
        assert len(perf_logs) > 0, "Should have performance logs"
        assert perf_logs[0].level == LogLevel.WARNING, "Should be WARNING level due to threshold"
        
        log_manager.shutdown()
        print("✓ Performance event logging test passed")


def test_error_logging_with_context():
    """Test error logging with context functionality"""
    print("Testing error logging with context...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        log_manager = EnhancedLogManager(log_directory=temp_dir)
        
        # Create a test exception
        try:
            raise ValueError("Test error for logging")
        except Exception as e:
            entry_id = log_manager.log_error_with_context(
                component="test_component",
                error=e,
                context={"method": "test_method", "line": 123},
                user_action="test_action"
            )
            
            assert entry_id, "Error should be logged with context"
        
        # Verify error log
        recent_logs = log_manager.get_recent_logs(10)
        error_logs = [log for log in recent_logs if log.level == LogLevel.ERROR]
        
        assert len(error_logs) > 0, "Should have error logs"
        assert error_logs[0].error_details is not None, "Should have error details"
        assert error_logs[0].stack_trace is not None, "Should have stack trace"
        
        log_manager.shutdown()
        print("✓ Error logging with context test passed")


def test_log_search_and_filtering():
    """Test log search and filtering functionality"""
    print("Testing log search and filtering...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        log_manager = EnhancedLogManager(log_directory=temp_dir)
        
        # Add various log entries
        log_manager.log_event(LogLevel.INFO, LogCategory.SYSTEM, "system", "System started")
        log_manager.log_event(LogLevel.ERROR, LogCategory.CONNECTION, "mqtt", "Connection failed")
        log_manager.log_event(LogLevel.WARNING, LogCategory.PERFORMANCE, "monitor", "High latency detected")
        
        # Test search by level
        filter_criteria = LogSearchFilter(
            log_level=LogLevel.ERROR,
            max_results=10
        )
        
        search_result = log_manager.search_logs(filter_criteria)
        assert search_result.total_matches > 0, "Should find error logs"
        assert all(entry.level == LogLevel.ERROR for entry in search_result.entries), "All results should be ERROR level"
        
        # Test search by category
        filter_criteria = LogSearchFilter(
            category=LogCategory.CONNECTION,
            max_results=10
        )
        
        search_result = log_manager.search_logs(filter_criteria)
        assert search_result.total_matches > 0, "Should find connection logs"
        assert all(entry.category == LogCategory.CONNECTION for entry in search_result.entries), "All results should be CONNECTION category"
        
        # Test search by message pattern
        filter_criteria = LogSearchFilter(
            message_pattern="connection",
            max_results=10
        )
        
        search_result = log_manager.search_logs(filter_criteria)
        assert search_result.total_matches > 0, "Should find logs with 'connection' in message"
        
        log_manager.shutdown()
        print("✓ Log search and filtering test passed")


def test_log_export_functionality():
    """Test log export functionality"""
    print("Testing log export functionality...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        log_manager = EnhancedLogManager(log_directory=temp_dir)
        
        # Add some test logs
        log_manager.log_event(LogLevel.INFO, LogCategory.SYSTEM, "test", "Test log 1")
        log_manager.log_event(LogLevel.ERROR, LogCategory.ERROR, "test", "Test error log")
        
        # Test JSON export
        filter_criteria = LogSearchFilter(max_results=10)
        export_path = log_manager.export_logs(filter_criteria, "json")
        
        assert os.path.exists(export_path), "Export file should exist"
        assert export_path.endswith('.json'), "Export file should be JSON"
        
        # Test CSV export
        export_path = log_manager.export_logs(filter_criteria, "csv")
        
        assert os.path.exists(export_path), "CSV export file should exist"
        assert export_path.endswith('.csv'), "Export file should be CSV"
        
        log_manager.shutdown()
        print("✓ Log export functionality test passed")


def run_all_tests():
    """Run all log management tests"""
    print("Running log management integration tests...")
    print("=" * 50)
    
    try:
        test_log_manager_initialization()
        test_log_viewer_integration()
        test_connection_event_logging()
        test_performance_event_logging()
        test_error_logging_with_context()
        test_log_search_and_filtering()
        test_log_export_functionality()
        
        print("=" * 50)
        print("✓ All log management integration tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)