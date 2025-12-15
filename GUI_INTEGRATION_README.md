# GUI Integration for MQTT Camera Monitoring System

This document describes the GUI wrapper implementation that integrates the existing `FinalProductionSystem` with a PySide GUI interface.

## Overview

The GUI integration consists of three main components:

1. **GuiSystemWrapper** (`mqtt_camera_monitoring/gui_system_wrapper.py`) - Wrapper class that interfaces with the existing FinalProductionSystem
2. **MainWindow** (`mqtt_camera_monitoring/gui_main_window.py`) - PySide GUI interface (already implemented)
3. **MqttCameraMonitoringApp** (`mqtt_camera_monitoring/gui_main_application.py`) - Main application that connects GUI and system

## Key Features

### Multi-Camera Support
- Supports up to 6 USB cameras (Camera 0-5)
- Individual configuration for each camera (enable/disable, camera ID, mask file, threshold)
- Ensures cameras use 1920x1080 resolution to match mask files
- No additional camera parameters applied (uses cameras directly as in existing system)

### Dynamic Configuration
- Real-time parameter updates without system restart
- Individual mask files for each enabled camera
- GUI-configured baseline counts and comparison thresholds
- Automatic configuration file saving

### System Integration
- Wraps existing FinalProductionSystem without modifying core logic
- Maintains all existing MQTT functionality
- Preserves red light detection algorithms
- Supports both GUI and command-line modes

## Usage

### Starting the GUI Application

```bash
# Using the main entry point
python gui_main.py

# Or directly
python -m mqtt_camera_monitoring.gui_main_application
```

### Configuration

1. **Camera Configuration** (Left Panel):
   - Enable/disable individual cameras (0-5)
   - Select physical camera ID for each enabled camera
   - Choose mask file path (must be 1920x1080 resolution)
   - Set individual comparison thresholds

2. **System Parameters** (Left Panel):
   - Delay time (default 0.4s) - time before baseline establishment
   - Global threshold (default 2) - applies to all cameras
   - Monitoring interval (default 0.2s) - detection frequency

3. **System Control** (Left Panel):
   - Start/Stop monitoring system buttons
   - System status indicator

4. **System Status** (Right Panel):
   - MQTT connection status
   - Baseline establishment events log
   - Trigger events log
   - System health indicators

### Starting/Stopping the System

1. Configure cameras and parameters in the GUI
2. Click "启动监控系统" (Start Monitoring System) button
3. System validates configuration and starts monitoring
4. Click "停止监控系统" (Stop Monitoring System) to stop

## Implementation Details

### Camera Initialization
- Only enabled cameras are initialized
- Each camera uses its configured physical camera ID (0-5)
- Cameras maintain 1920x1080 resolution for mask compatibility
- No camera parameter modifications (as per requirements)

### Mask File Handling
- Individual mask files applied to each enabled camera
- Mask files must be 1920x1080 resolution
- Validation ensures mask files exist and are readable

### Threshold Configuration
- Individual thresholds for each camera
- Global threshold setting updates all cameras
- Thresholds applied dynamically during detection

### Configuration Persistence
- Automatic saving to config.yaml file
- Configuration loaded on startup
- Real-time updates saved immediately

## Error Handling

### Validation
- Camera ID range validation (0-5)
- Duplicate camera ID prevention
- Mask file existence and format validation
- Resolution compatibility checking (1920x1080)

### Runtime Errors
- Camera initialization failure handling
- MQTT connection error recovery
- Mask file loading error handling
- Graceful degradation with partial camera failures

## Files Created/Modified

### New Files
- `mqtt_camera_monitoring/gui_system_wrapper.py` - System integration wrapper
- `mqtt_camera_monitoring/gui_main_application.py` - Main GUI application
- `gui_main.py` - Entry point for GUI application

### Modified Files
- `mqtt_camera_monitoring/gui_main_window.py` - Added system control buttons

## Testing

Run basic integration tests:

```bash
python test_gui_integration.py
```

## Requirements Compliance

This implementation satisfies the following requirements:

- **3.2**: Dynamic parameter updates without restart
- **6.4**: Mask file validation and 1920x1080 resolution compatibility
- **4.1, 5.1**: GUI interface for configuration and monitoring
- **1.1-6.5**: All original system functionality preserved

## Future Enhancements

- Visual camera feed display in GUI
- Advanced error reporting and diagnostics
- Configuration import/export functionality
- System performance monitoring
- Multi-language support