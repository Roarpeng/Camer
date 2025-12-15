#!/usr/bin/env python3
"""
Test script to validate GUI structure without running the actual GUI
"""

import sys
import os

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_gui_imports():
    """Test that GUI modules can be imported"""
    try:
        # Test importing the GUI module
        from mqtt_camera_monitoring import gui_main_window
        print("✓ GUI main window module imported successfully")
        
        # Test class definitions
        assert hasattr(gui_main_window, 'MainWindow'), "MainWindow class not found"
        assert hasattr(gui_main_window, 'GuiApplication'), "GuiApplication class not found"
        print("✓ Required GUI classes found")
        
        # Test MainWindow methods
        main_window_methods = [
            'setup_window_properties',
            'setup_ui', 
            'create_left_panel',
            'create_right_panel'
        ]
        
        for method in main_window_methods:
            assert hasattr(gui_main_window.MainWindow, method), f"MainWindow.{method} method not found"
        print("✓ MainWindow methods defined correctly")
        
        # Test GuiApplication methods
        gui_app_methods = [
            'initialize',
            'show',
            'run',
            'quit'
        ]
        
        for method in gui_app_methods:
            assert hasattr(gui_main_window.GuiApplication, method), f"GuiApplication.{method} method not found"
        print("✓ GuiApplication methods defined correctly")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except AssertionError as e:
        print(f"✗ Structure error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_main_entry_point():
    """Test that main entry point exists"""
    try:
        # Check if gui_main.py exists and has main function
        import gui_main
        assert hasattr(gui_main, 'main'), "main() function not found in gui_main.py"
        print("✓ Main entry point exists")
        return True
        
    except ImportError as e:
        print(f"✗ Cannot import gui_main: {e}")
        return False
    except AssertionError as e:
        print(f"✗ Main entry point error: {e}")
        return False

def test_requirements_updated():
    """Test that requirements.txt includes PySide6"""
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
        
        assert 'PySide6' in content, "PySide6 not found in requirements.txt"
        print("✓ PySide6 added to requirements.txt")
        return True
        
    except FileNotFoundError:
        print("✗ requirements.txt not found")
        return False
    except AssertionError as e:
        print(f"✗ Requirements error: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Testing GUI Main Window Structure ===")
    print()
    
    tests = [
        ("GUI Module Structure", test_gui_imports),
        ("Main Entry Point", test_main_entry_point), 
        ("Requirements Updated", test_requirements_updated)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! GUI main window structure is correctly implemented.")
        return 0
    else:
        print("✗ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())