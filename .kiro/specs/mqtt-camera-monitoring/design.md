# Design Document

## Overview

The MQTT Camera Monitoring System builds upon the existing `final_production_system.py` by adding a PySide GUI interface for configuration and monitoring. The core detection logic, visual processing, and MQTT handling remain unchanged. The system adds a graphical interface to configure camera parameters (delay time, comparison threshold, camera IDs, mask paths) and provides real-time monitoring of system status, baseline establishment events, and trigger activities.

## Architecture

The system extends the existing `final_production_system.py` with a PySide GUI wrapper:

```
┌─────────────────────────────────────────────────────────────┐
│                    PySide GUI Interface                     │
│  ┌─────────────────┐              ┌─────────────────┐      │
│  │ Camera Config   │              │ System Status   │      │
│  │ Panel (Left)    │              │ Panel (Right)   │      │
│  │ - Camera IDs    │              │ - MQTT Status   │      │
│  │ - Mask Paths    │              │ - Baseline Info │      │
│  │ - Enable/Disable│              │ - Trigger Events│      │
│  └─────────────────┘              └─────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Existing FinalProductionSystem                 │
│  ┌─────────────────┐    ┌─────────────────┐               │
│  │   MQTT Client   │    │  Camera Manager │               │
│  │ - changeState   │    │ - Multi-camera  │               │
│  │ - Timing Logic  │    │ - Mask Support  │               │
│  │ - Trigger Pub   │    │ - Red Detection │               │
│  └─────────────────┘    └─────────────────┘               │
│                              │                             │
│                    ┌─────────────────┐                    │
│                    │ Detection Loop  │                    │
│                    │ - Baseline Est  │                    │
│                    │ - 0.3s Monitor  │                    │
│                    │ - Visual Display│                    │
│                    └─────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### PySide GUI Component
- **Purpose**: Provide graphical interface for configuration and monitoring
- **Interfaces**:
  - `create_main_window()`: Initialize main GUI window with left and right panels
  - `setup_camera_config_panel()`: Create left panel with camera configuration controls
  - `setup_system_status_panel()`: Create right panel with system status information
  - `update_camera_info(camera_id, baseline, current, triggered)`: Update camera monitoring info
  - `update_mqtt_status(connected, last_message)`: Update MQTT connection status
  - `log_baseline_event(timestamp, cameras)`: Log baseline establishment events
  - `log_trigger_event(device_id, timestamp)`: Log receiver trigger events
  - `apply_camera_config(camera_configs)`: Apply camera configuration changes

### MQTT Client Component
- **Purpose**: Handle MQTT communication with enhanced timing logic
- **Interfaces**:
  - `connect(broker_host, client_id)`: Connect to MQTT broker
  - `subscribe(topic)`: Subscribe to specified topic
  - `on_message_callback(message)`: Process incoming messages with timing logic
  - `publish(topic, payload)`: Send messages to broker
  - `parse_state_message(json_str)`: Parse JSON and extract state array
  - `check_message_timing(current_message, delay_threshold)`: Check if 0.4s delay passed and message changed
  - `trigger_baseline_establishment()`: Signal baseline establishment when conditions met

### Camera Manager Component
- **Purpose**: Manage USB camera operations with mask support
- **Interfaces**:
  - `initialize_cameras(camera_configs)`: Initialize cameras based on GUI configuration
  - `enable_camera(camera_id, mask_path)`: Enable specific camera with mask file
  - `disable_camera(camera_id)`: Disable specific camera
  - `get_masked_frame(camera_id)`: Retrieve frame with mask applied
  - `validate_mask_file(mask_path)`: Validate mask file format and accessibility
  - `update_camera_config(camera_id, config)`: Update individual camera configuration
  - `release_cameras()`: Clean up camera resources

### Light Detector Component
- **Purpose**: Analyze masked camera regions for red light detection
- **Interfaces**:
  - `detect_red_lights_in_mask(frame, mask)`: Count red lights within masked region
  - `set_baseline(camera_id, count)`: Store baseline red light count for specific camera
  - `start_monitoring_cycle()`: Begin 0.2s monitoring cycle for all enabled cameras
  - `check_threshold_decrease(camera_id, current_count, threshold)`: Compare with baseline using threshold
  - `reset_baselines()`: Clear all baselines when new changeState occurs
  - `get_monitoring_status()`: Return current monitoring state for all cameras

### Main Controller Component
- **Purpose**: Coordinate all components and manage configuration
- **Interfaces**:
  - `initialize_system(gui_config)`: Set up all components with GUI configuration
  - `run_monitoring_loop()`: Main event loop with 0.2s timing
  - `handle_changestate_update()`: Process changeState with 0.4s delay logic
  - `handle_threshold_trigger(camera_id)`: Process threshold decrease detection
  - `update_system_config(new_config)`: Apply configuration changes from GUI
  - `get_system_status()`: Return current system status for GUI display

## Data Models

### Camera Configuration Model
```python
{
    "camera_id": int,           # Physical camera ID (0-5)
    "enabled": bool,            # Whether camera is active
    "mask_path": str,           # Path to mask image file
    "baseline_count": int,      # Current baseline red light count
    "current_count": int,       # Current detected red light count
    "triggered": bool,          # Whether camera has triggered receiver
    "last_update": datetime     # Last detection update timestamp
}
```

### System Configuration Model
```python
{
    "delay_time": float,        # Delay time in seconds (default 0.4)
    "monitoring_interval": float, # Monitoring frequency in seconds (default 0.2)
    "comparison_threshold": int,  # Red light decrease threshold (default 2)
    "mqtt_broker": str,         # MQTT broker address
    "mqtt_client_id": str,      # MQTT client identifier
    "max_cameras": int          # Maximum supported cameras (6)
}
```

### MQTT Message Model
```python
{
    "state": [1, 2, 0, 1, 2, 0, ...],  # Array of integers (0, 1, or 2)
    "timestamp": datetime,              # Message received timestamp
    "content_changed": bool,            # Whether content differs from previous
    "delay_elapsed": bool               # Whether 0.4s delay has passed
}
```

### GUI Status Model
```python
{
    "mqtt_status": {
        "connected": bool,
        "last_message_time": datetime,
        "connection_info": str
    },
    "baseline_events": List[{
        "timestamp": datetime,
        "triggered_cameras": List[int],
        "message_content": str
    }],
    "trigger_events": List[{
        "device_id": int,
        "timestamp": datetime,
        "camera_id": int,
        "baseline_count": int,
        "trigger_count": int
    }],
    "system_health": {
        "cameras_initialized": int,
        "cameras_enabled": int,
        "monitoring_active": bool,
        "last_error": str
    }
}
```

### Masked Frame Model
```python
{
    "camera_id": int,
    "original_frame": numpy.ndarray,    # Full camera frame
    "mask": numpy.ndarray,              # Binary mask image
    "masked_frame": numpy.ndarray,      # Frame with mask applied
    "red_light_count": int,             # Count within masked region
    "detection_regions": List[Tuple[int, int, int, int]]  # Bounding boxes
}
```
## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: JSON Message Parsing
*For any* valid JSON message containing a "state" array, the MQTT system should successfully parse the message and extract the state array without errors.
**Validates: Requirements 1.3**

### Property 2: Timing-Based Baseline Trigger
*For any* pair of changeState messages where content differs and 0.4 seconds have elapsed, the system should trigger baseline establishment.
**Validates: Requirements 1.4**

### Property 3: Baseline Establishment for Enabled Cameras
*For any* set of enabled cameras, when baseline is triggered, the system should establish red light count baselines for all enabled cameras only.
**Validates: Requirements 1.5**

### Property 4: Masked Region Detection
*For any* camera frame and mask combination, red light detection should only count lights within the masked region boundaries.
**Validates: Requirements 2.2**

### Property 5: Threshold-Based Triggering
*For any* camera with baseline count and current count, when the decrease exceeds the configured threshold, the system should send a trigger message.
**Validates: Requirements 2.3**

### Property 6: Baseline Reset on New Message
*For any* new changeState update, the system should reset all baselines and restart monitoring cycles.
**Validates: Requirements 2.4**

### Property 7: Disabled Camera Exclusion
*For any* camera configuration where cameras are disabled, the system should skip monitoring for those specific camera IDs.
**Validates: Requirements 2.5**

### Property 8: Dynamic Configuration Updates
*For any* parameter change through the GUI, the system should apply changes to active monitoring without requiring restart.
**Validates: Requirements 3.2**

### Property 9: Camera Configuration Validation
*For any* camera being enabled, the system should require both camera ID and mask file path to be specified.
**Validates: Requirements 3.3**

### Property 10: Threshold Update Application
*For any* new comparison threshold value, the red light detector should use the updated threshold for subsequent baseline comparisons.
**Validates: Requirements 3.4**

### Property 11: Timing Parameter Updates
*For any* new delay time value, the MQTT system should use the updated timing for changeState message processing.
**Validates: Requirements 3.5**

### Property 12: GUI Configuration Elements
*For any* camera configuration interface, the GUI should provide fields for camera ID, mask file path, and enable/disable controls.
**Validates: Requirements 4.2**

### Property 13: Real-time Camera Status Updates
*For any* enabled camera state change, the GUI should display current baseline count, detection count, and trigger status.
**Validates: Requirements 4.3**

### Property 14: Real-time Monitoring Updates
*For any* active monitoring state, the GUI should update detection information in real-time.
**Validates: Requirements 4.4**

### Property 15: Configuration Change Validation
*For any* camera configuration change, the GUI should validate inputs and apply changes to the monitoring system.
**Validates: Requirements 4.5**

### Property 16: MQTT Status Updates
*For any* MQTT connection state change, the GUI should update and display the current connection status.
**Validates: Requirements 5.2**

### Property 17: Baseline Event Logging
*For any* changeState message that triggers baseline establishment, the GUI should log and display the baseline trigger event.
**Validates: Requirements 5.3**

### Property 18: Trigger Event Logging
*For any* receiver trigger sent, the GUI should display device ID trigger information with timestamps.
**Validates: Requirements 5.4**

### Property 19: Error Display
*For any* system error that occurs, the GUI should display error messages and system health indicators.
**Validates: Requirements 5.5**

### Property 20: Malformed JSON Handling
*For any* malformed JSON message received, the system should handle parsing errors gracefully without crashing and log the error.
**Validates: Requirements 6.1**

### Property 21: Camera Failure Recovery
*For any* camera initialization failure, the system should report failed cameras and continue with available cameras.
**Validates: Requirements 6.2**

### Property 22: MQTT Reconnection
*For any* MQTT connection loss event, the system should automatically attempt reconnection and update GUI status.
**Validates: Requirements 6.3**

### Property 23: Mask File Validation
*For any* missing or invalid mask file, the system should log the error and disable the affected camera.
**Validates: Requirements 6.4**

### Property 24: Message Delivery Reliability
*For any* trigger message publication attempt, the system should confirm delivery or retry on failure.
**Validates: Requirements 6.5**

## Error Handling

### MQTT Connection Errors
- **Connection Timeout**: Implement exponential backoff retry mechanism with GUI status updates
- **Authentication Failure**: Log error, update GUI status, and attempt reconnection with correct credentials
- **Network Interruption**: Automatic reconnection with connection state monitoring and GUI notifications

### Camera Operation Errors
- **Camera Not Found**: Continue with available cameras, log missing camera IDs, update GUI status
- **Frame Capture Failure**: Skip failed frame, continue with next capture cycle, maintain GUI error indicators
- **USB Device Disconnection**: Attempt camera reinitialization, fallback to available cameras, notify GUI

### Mask File Errors
- **Missing Mask File**: Log error, disable affected camera, update GUI with error status
- **Invalid Mask Format**: Validate mask dimensions and format, disable camera if incompatible
- **Mask Loading Failure**: Handle file access errors gracefully, provide GUI feedback

### GUI Configuration Errors
- **Invalid Camera ID**: Validate camera ID range (0-5), provide user feedback
- **Invalid File Paths**: Check mask file accessibility before applying configuration
- **Configuration Conflicts**: Prevent duplicate camera ID assignments, validate parameter ranges

### Detection Processing Errors
- **Invalid Frame Data**: Skip processing for corrupted frames, log error, maintain monitoring cycle
- **Color Detection Failure**: Use fallback detection method or skip frame, continue with other cameras
- **Memory Allocation Issues**: Implement frame buffer management and cleanup, monitor system resources

### JSON Processing Errors
- **Malformed JSON**: Log parsing error, continue monitoring for next message, update GUI status
- **Missing State Field**: Handle gracefully with default empty state array, log warning
- **Invalid Data Types**: Validate and sanitize input data before processing, provide error feedback

## Testing Strategy

### Unit Testing Framework
The system will use **pytest** as the primary testing framework for Python, providing:
- Simple test discovery and execution
- Fixture support for test setup and teardown
- Parametrized testing for multiple input scenarios
- Mock support for external dependencies (MQTT broker, cameras, GUI components)

### Property-Based Testing Framework
The system will use **Hypothesis** for property-based testing, configured with:
- Minimum 100 iterations per property test
- Custom generators for JSON messages, camera configurations, mask files, and timing scenarios
- Shrinking capabilities to find minimal failing examples
- Integration with pytest for unified test execution

### Unit Testing Approach
Unit tests will focus on:
- Individual component functionality (MQTT client, camera manager, light detector, GUI components)
- Specific examples demonstrating correct behavior
- Edge cases like empty configurations, single-camera scenarios, invalid mask files
- Error conditions and exception handling
- Integration points between components and GUI
- GUI widget behavior and user interaction scenarios

### Property-Based Testing Approach
Property tests will verify:
- Universal properties that hold across all valid inputs
- JSON parsing correctness for any valid message format
- Timing logic accuracy for any message timing scenarios
- Mask-based detection consistency across different frame and mask combinations
- Configuration validation for any parameter combinations
- GUI update behavior for any system state changes
- Error handling robustness for any type of failure scenario

Each property-based test must:
- Run a minimum of 100 iterations
- Include a comment explicitly referencing the design document property
- Use the format: '**Feature: mqtt-camera-monitoring, Property {number}: {property_text}**'
- Generate realistic test data that matches production scenarios including GUI interactions

### GUI Testing Approach
GUI tests will include:
- Widget creation and layout verification
- User interaction simulation (button clicks, text input, checkbox changes)
- Real-time update verification for status displays
- Configuration validation and error handling
- Event handling and callback verification

### Testing Dependencies
- **pytest**: Unit testing framework
- **hypothesis**: Property-based testing library
- **pytest-mock**: Mocking support for external dependencies
- **pytest-qt**: PySide/Qt testing support for GUI components
- **opencv-python**: Required for camera frame and mask testing
- **paho-mqtt**: MQTT client library for integration testing
- **PySide6**: GUI framework for interface testing