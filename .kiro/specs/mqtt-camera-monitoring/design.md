# Design Document

## Overview

The MQTT Camera Monitoring System is a Python-based application with PySide GUI that integrates MQTT messaging with configurable USB camera monitoring. The system connects to an MQTT broker to receive state change messages, implements enhanced timing logic for baseline establishment, and monitors up to 6 cameras using individual mask regions. The system provides real-time configuration and monitoring through a graphical interface.

## Architecture

The system follows a modular architecture with GUI-driven configuration and real-time monitoring:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PySide GUI    │    │   MQTT Client   │    │  Camera Manager │
│                 │    │                 │    │                 │
│ - Config Panel  │    │ - Connect       │    │ - Initialize    │
│ - Status Panel  │    │ - Subscribe     │    │ - Mask Support  │
│ - Real-time UI  │    │ - Timing Logic  │    │ - Multi-camera  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐    ┌─────────────────┐
                    │ Main Controller │    │ Light Detector  │
                    │                 │    │                 │
                    │ - Coordinate    │    │ - Masked Region │
                    │ - Config Mgmt   │    │ - Baseline Comp │
                    │ - Event Loop    │    │ - 0.2s Monitor  │
                    └─────────────────┘    └─────────────────┘
```

## Components and Interfaces

### MQTT Client Component
- **Purpose**: Handle all MQTT communication
- **Interfaces**:
  - `connect(broker_host, client_id)`: Connect to MQTT broker
  - `subscribe(topic)`: Subscribe to specified topic
  - `on_message_callback(message)`: Process incoming messages
  - `publish(topic, payload)`: Send messages to broker
  - `parse_state_message(json_str)`: Parse JSON and count values

### Camera Manager Component
- **Purpose**: Manage USB camera operations with dynamic parameter configuration
- **Interfaces**:
  - `initialize_cameras(count, config)`: Initialize cameras with configuration parameters
  - `start_capture()`: Begin capturing from all cameras
  - `get_frames()`: Retrieve current frames from all cameras
  - `set_brightness(value)`: Adjust brightness for all cameras
  - `set_exposure(value)`: Configure exposure time for all cameras
  - `update_parameters(config)`: Apply runtime parameter updates
  - `release_cameras()`: Clean up camera resources

### Light Detector Component
- **Purpose**: Analyze camera frames for red light detection with size/area tracking
- **Interfaces**:
  - `detect_red_lights(frame)`: Count red lights and calculate total area in a single frame
  - `set_baseline(counts, areas)`: Store initial red light counts and areas within 1 second
  - `check_changes(current_counts, current_areas)`: Compare counts and areas with baseline
  - `update_baseline(counts, areas)`: Update baseline after trigger
  - `get_detection_boxes(frame)`: Return bounding boxes for detected red lights

### Visual Monitor Component
- **Purpose**: Display camera feeds with detection overlays
- **Interfaces**:
  - `create_windows(camera_count)`: Initialize display windows for all cameras
  - `update_display(frames, detection_boxes)`: Update display with frames and green box overlays
  - `show_error(camera_id, error_msg)`: Display error indicators for failed cameras
  - `close_windows()`: Clean up display resources

### Main Controller Component
- **Purpose**: Coordinate all components and manage system flow
- **Interfaces**:
  - `initialize_system()`: Set up all components
  - `run_monitoring_loop()`: Main event loop
  - `handle_mqtt_update()`: Process MQTT message updates
  - `handle_light_decrease()`: Process light count decreases

## Data Models

### State Message Model
```python
{
    "state": [1, 2, 0, 1, 2, 0, ...]  # Array of integers (0, 1, or 2)
}
```

### Camera Frame Model
```python
{
    "camera_id": int,
    "frame": numpy.ndarray,  # OpenCV frame data
    "timestamp": datetime,
    "red_light_count": int,
    "red_light_total_area": float,
    "detection_boxes": List[Tuple[int, int, int, int]]  # (x, y, width, height)
}
```

### Camera Configuration Model
```python
{
    "brightness": int,        # Camera brightness (0-100)
    "exposure": int,         # Exposure time in milliseconds
    "contrast": int,         # Contrast setting (0-100)
    "saturation": int,       # Saturation setting (0-100)
    "auto_exposure": bool    # Enable/disable auto exposure
}
```

### System State Model
```python
{
    "mqtt_connected": bool,
    "cameras_active": bool,
    "baseline_counts": List[int],      # Red light counts per camera
    "baseline_areas": List[float],     # Red light total areas per camera
    "baseline_timestamp": datetime,    # When baseline was established
    "last_message_count": int,         # Count of 1s in last MQTT message
    "message_updated": bool,
    "visual_monitor_active": bool
}
```
## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: JSON Message Parsing
*For any* valid JSON message containing a "state" array, the MQTT system should successfully parse the message and extract the state array without errors.
**Validates: Requirements 1.3**

### Property 2: Value Counting Accuracy
*For any* state array containing integers, counting the occurrences of value 1 should return the correct count that matches manual counting.
**Validates: Requirements 1.4**

### Property 3: Message Update Detection
*For any* two consecutive MQTT messages, the system should correctly identify whether the second message represents an update from the first based on content comparison.
**Validates: Requirements 1.5**

### Property 4: Camera Activation on Update
*For any* MQTT message update event, all available cameras should be activated and begin capturing frames.
**Validates: Requirements 2.2**

### Property 5: Baseline Count Establishment
*For any* set of camera frames captured during activation, the red light detector should establish baseline counts for each camera feed.
**Validates: Requirements 2.3**

### Property 6: Continuous Light Monitoring
*For any* active camera feed, the red light detector should continuously track and update red light counts during monitoring periods.
**Validates: Requirements 2.4**

### Property 7: Trigger on Light Decrease
*For any* camera feed where red light count decreases below baseline before the next MQTT trigger, the system should send an empty message to the "receiver/triggered" topic.
**Validates: Requirements 2.5**

### Property 8: Graceful JSON Error Handling
*For any* malformed JSON message received, the system should handle parsing errors without crashing and log appropriate error messages.
**Validates: Requirements 3.1**

### Property 9: Camera Failure Recovery
*For any* camera initialization failure, the system should report the failed cameras and continue operating with the remaining functional cameras.
**Validates: Requirements 3.2**

### Property 10: MQTT Reconnection
*For any* MQTT connection loss event, the system should automatically attempt to reconnect to the broker without manual intervention.
**Validates: Requirements 3.3**

### Property 11: Detection Error Resilience
*For any* red light detection failure on a single camera, the system should log the error and continue monitoring the other cameras without interruption.
**Validates: Requirements 3.4**

### Property 12: Message Delivery Reliability
*For any* trigger message publication attempt, the system should either confirm successful delivery or retry the operation on failure.
**Validates: Requirements 3.5**

### Property 13: Baseline Timing Accuracy
*For any* camera activation event, the baseline measurements should be established within exactly 1 second of trigger activation.
**Validates: Requirements 2.3**

### Property 14: Area Change Detection
*For any* red light area change that exceeds the configured threshold, the system should trigger message publication even if count remains the same.
**Validates: Requirements 2.5**

### Property 15: Visual Overlay Accuracy
*For any* detected red light, the visual monitor should display a green bounding box that accurately encompasses the detected light position.
**Validates: Requirements 4.2**

### Property 16: Dynamic Parameter Application
*For any* camera parameter update, the changes should be applied to all cameras without requiring system restart.
**Validates: Requirements 5.4**

## Error Handling

### MQTT Connection Errors
- **Connection Timeout**: Implement exponential backoff retry mechanism
- **Authentication Failure**: Log error and attempt reconnection with correct credentials
- **Network Interruption**: Automatic reconnection with connection state monitoring

### Camera Operation Errors
- **Camera Not Found**: Continue with available cameras, log missing camera IDs
- **Frame Capture Failure**: Skip failed frame, continue with next capture cycle
- **USB Device Disconnection**: Attempt camera reinitialization, fallback to available cameras

### Image Processing Errors
- **Invalid Frame Data**: Skip processing for corrupted frames, log error
- **Color Detection Failure**: Use fallback detection method or skip frame
- **Memory Allocation Issues**: Implement frame buffer management and cleanup

### JSON Processing Errors
- **Malformed JSON**: Log parsing error, continue monitoring for next message
- **Missing State Field**: Handle gracefully with default empty state array
- **Invalid Data Types**: Validate and sanitize input data before processing

## Testing Strategy

### Unit Testing Framework
The system will use **pytest** as the primary testing framework for Python, providing:
- Simple test discovery and execution
- Fixture support for test setup and teardown
- Parametrized testing for multiple input scenarios
- Mock support for external dependencies (MQTT broker, cameras)

### Property-Based Testing Framework
The system will use **Hypothesis** for property-based testing, configured with:
- Minimum 100 iterations per property test
- Custom generators for JSON messages, camera frames, and state arrays
- Shrinking capabilities to find minimal failing examples
- Integration with pytest for unified test execution

### Unit Testing Approach
Unit tests will focus on:
- Individual component functionality (MQTT client, camera manager, light detector)
- Specific examples demonstrating correct behavior
- Edge cases like empty arrays, single-camera scenarios
- Error conditions and exception handling
- Integration points between components

### Property-Based Testing Approach
Property tests will verify:
- Universal properties that hold across all valid inputs
- JSON parsing correctness for any valid message format
- Count accuracy for any state array composition
- Camera behavior consistency across different frame inputs
- Error handling robustness for any type of failure scenario

Each property-based test must:
- Run a minimum of 100 iterations
- Include a comment explicitly referencing the design document property
- Use the format: '**Feature: mqtt-camera-monitoring, Property {number}: {property_text}**'
- Generate realistic test data that matches production scenarios

### Testing Dependencies
- **pytest**: Unit testing framework
- **hypothesis**: Property-based testing library
- **pytest-mock**: Mocking support for external dependencies
- **opencv-python**: Required for camera frame testing
- **paho-mqtt**: MQTT client library for integration testing