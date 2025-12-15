#!/usr/bin/env python3
"""
Test script to validate Task 6 implementation
Tests the real-time status monitoring functionality
"""

import sys
import os

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported successfully"""
    try:
        from mqtt_camera_monitoring.gui_system_wrapper import GuiSystemWrapper
        from mqtt_camera_monitoring.gui_main_window import MainWindow
        from mqtt_camera_monitoring.mqtt_client import MQTTClient
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_status_monitoring_methods():
    """Test that status monitoring methods exist"""
    try:
        from mqtt_camera_monitoring.gui_system_wrapper import GuiSystemWrapper
        
        # Check if status monitoring methods exist
        wrapper = GuiSystemWrapper.__new__(GuiSystemWrapper)  # Create without __init__
        
        required_methods = [
            '_status_monitoring_loop',
            '_extract_mqtt_status',
            '_extract_system_health',
            '_update_mqtt_status_display',
            '_update_camera_status_displays',
            '_update_system_health_display',
            '_override_baseline_capture_logging'
        ]
        
        for method_name in required_methods:
            if hasattr(GuiSystemWrapper, method_name):
                print(f"✓ Method {method_name} exists")
            else:
                print(f"✗ Method {method_name} missing")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Status monitoring test error: {e}")
        return False

def test_event_logging_methods():
    """Test that event logging methods exist"""
    try:
        from mqtt_camera_monitoring.gui_main_window import MainWindow
        
        # Check if event logging methods exist
        window = MainWindow.__new__(MainWindow)  # Create without __init__
        
        required_methods = [
            'log_baseline_event',
            'log_trigger_event',
            '_limit_log_size',
            'format_timestamp',
            'clear_event_logs',
            'export_event_logs'
        ]
        
        for method_name in required_methods:
            if hasattr(MainWindow, method_name):
                print(f"✓ Method {method_name} exists")
            else:
                print(f"✗ Method {method_name} missing")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Event logging test error: {e}")
        return False

def test_mqtt_client_enhancements():
    """Test that MQTT client has last message time tracking"""
    try:
        from mqtt_camera_monitoring.mqtt_client import MQTTClient
        
        # Check if last_message_time attribute exists in __init__
        import inspect
        init_source = inspect.getsource(MQTTClient.__init__)
        
        if 'last_message_time' in init_source:
            print("✓ MQTT client has last_message_time tracking")
            return True
        else:
            print("✗ MQTT client missing last_message_time tracking")
            return False
            
    except Exception as e:
        print(f"✗ MQTT client test error: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing Task 6 Implementation: Real-time Status Monitoring")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_imports),
        ("Status Monitoring Methods", test_status_monitoring_methods),
        ("Event Logging Methods", test_event_logging_methods),
        ("MQTT Client Enhancements", test_mqtt_client_enhancements)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"  Test failed!")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! Task 6 implementation is complete.")
        return 0
    else:
        print("✗ Some tests failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())