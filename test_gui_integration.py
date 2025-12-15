#!/usr/bin/env python3
"""
Basic test for GUI integration functionality
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_gui_system_wrapper():
    """Test GUI System Wrapper basic functionality"""
    try:
        from mqtt_camera_monitoring.gui_system_wrapper import GuiSystemWrapper
        
        # Create wrapper
        wrapper = GuiSystemWrapper()
        print("✓ GUI System Wrapper created successfully")
        
        # Test camera configuration
        camera_configs = [
            {
                'camera_id': 0,
                'enabled': True,
                'physical_camera_id': 0,
                'mask_path': 'fmask.png',
                'baseline_count': 0,
                'threshold': 2
            }
        ]
        
        result = wrapper.configure_cameras(camera_configs)
        print(f"✓ Camera configuration: {result}")
        
        # Test system parameters
        params = {
            'delay_time': 0.4,
            'monitoring_interval': 0.2,
            'global_threshold': 2
        }
        
        result = wrapper.update_system_parameters(params)
        print(f"✓ System parameters update: {result}")
        
        # Test validation (should fail without mask file)
        valid, error_msg = wrapper.validate_camera_configuration()
        print(f"✓ Configuration validation: {valid}, {error_msg}")
        
        return True
        
    except Exception as e:
        print(f"✗ GUI System Wrapper test failed: {e}")
        return False

def test_gui_main_application():
    """Test GUI Main Application basic functionality"""
    try:
        from mqtt_camera_monitoring.gui_main_application import MqttCameraMonitoringApp
        
        # Create application (without running it)
        app = MqttCameraMonitoringApp()
        print("✓ GUI Main Application created successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ GUI Main Application test failed: {e}")
        return False

def main():
    """Run basic tests"""
    print("Testing GUI Integration Components...")
    print("=" * 50)
    
    success = True
    
    # Test GUI System Wrapper
    print("\n1. Testing GUI System Wrapper:")
    if not test_gui_system_wrapper():
        success = False
    
    # Test GUI Main Application
    print("\n2. Testing GUI Main Application:")
    if not test_gui_main_application():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All basic tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())