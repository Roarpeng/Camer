#!/usr/bin/env python3
"""
Main entry point for MQTT Camera Monitoring GUI Application
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mqtt_camera_monitoring.gui_main_application import main

if __name__ == "__main__":
    sys.exit(main())