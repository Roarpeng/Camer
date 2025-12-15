#!/usr/bin/env python3
"""
Simple Log Management Test

Tests the enhanced log management system integration without file operations.
"""

import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mqtt_camera_monitoring.data_models import LogLevel, LogCategory, LogEntry


def test_log_entry_creation():
    """Test LogEntry data model creation"""
    print("Testing LogEntry creation...")
    
    entry = LogEntry(
        entry_id="test-123",
        timestamp=datetime.now(),
        level=LogLevel.INFO,
        category=LogCategory.SYSTEM,
        component="test_component",
        message="Test message",
        details={"key": "value"}
    )
    
    assert entry.entry_id == "test-123"
    assert entry.level == LogLevel.INFO
    assert entry.category == LogCategory.SYSTEM
    assert entry.component == "test_component"
    assert entry.message == "Test message"
    assert entry.details["key"] == "value"
    
    print("✓ LogEntry creation test passed")


def test_log_levels_and_categories():
    """Test log levels and categories enums"""
    print("Testing log levels and categories...")
    
    # Test log levels
    levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]
    assert len(levels) == 5
    assert LogLevel.ERROR.value == "ERROR"
    
    # Test log categories
    categories = [LogCategory.SYSTEM, LogCategory.CONNECTION, LogCategory.PERFORMANCE, 
                 LogCategory.CONFIGURATION, LogCategory.ERROR, LogCategory.DIAGNOSTIC]
    assert len(categories) == 6
    assert LogCategory.CONNECTION.value == "connection"
    
    print("✓ Log levels and categories test passed")


def test_gui_system_wrapper_import():
    """Test that GUI system wrapper can be imported with log management"""
    print("Testing GUI system wrapper import...")
    
    try:
        from mqtt_camera_monitoring.gui_system_wrapper import GuiSystemWrapper
        print("✓ GUI system wrapper import test passed")
        return True
    except ImportError as e:
        print(f"✗ GUI system wrapper import failed: {e}")
        return False


def test_log_manager_import():
    """Test that log manager components can be imported"""
    print("Testing log manager imports...")
    
    try:
        from mqtt_camera_monitoring.log_manager import EnhancedLogManager, LogSearchFilter
        from mqtt_camera_monitoring.log_viewer import LogViewerInterface, LogViewerGUI
        print("✓ Log manager imports test passed")
        return True
    except ImportError as e:
        print(f"✗ Log manager import failed: {e}")
        return False


def test_log_entry_serialization():
    """Test LogEntry serialization"""
    print("Testing LogEntry serialization...")
    
    entry = LogEntry(
        entry_id="test-456",
        timestamp=datetime.now(),
        level=LogLevel.WARNING,
        category=LogCategory.PERFORMANCE,
        component="performance_monitor",
        message="High latency detected",
        details={"latency_ms": 150, "threshold_ms": 100}
    )
    
    # Test to_dict
    entry_dict = entry.to_dict()
    assert entry_dict["entry_id"] == "test-456"
    assert entry_dict["level"] == "WARNING"
    assert entry_dict["category"] == "performance"
    assert entry_dict["component"] == "performance_monitor"
    assert entry_dict["details"]["latency_ms"] == 150
    
    # Test from_dict
    restored_entry = LogEntry.from_dict(entry_dict)
    assert restored_entry.entry_id == entry.entry_id
    assert restored_entry.level == entry.level
    assert restored_entry.category == entry.category
    assert restored_entry.component == entry.component
    assert restored_entry.message == entry.message
    
    print("✓ LogEntry serialization test passed")


def run_all_tests():
    """Run all simple log management tests"""
    print("Running simple log management tests...")
    print("=" * 50)
    
    try:
        test_log_entry_creation()
        test_log_levels_and_categories()
        
        if not test_log_manager_import():
            return False
            
        if not test_gui_system_wrapper_import():
            return False
            
        test_log_entry_serialization()
        
        print("=" * 50)
        print("✓ All simple log management tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)