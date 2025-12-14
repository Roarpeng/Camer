# Requirements Document

## Introduction

This system implements an MQTT-based monitoring solution that connects to a broker to receive state change messages and controls USB cameras based on message updates. The system monitors red light counts in camera feeds and sends trigger messages when light counts decrease.

## Glossary

- **MQTT_System**: The main system that handles MQTT communication and camera monitoring
- **State_Message**: JSON message containing an array of state values (0, 1, or 2)
- **Camera_Monitor**: Component that captures and analyzes video feeds from USB cameras
- **Red_Light_Detector**: Algorithm that counts red lights in camera video feeds and tracks their size/area
- **Trigger_Publisher**: Component that publishes empty messages to the trigger topic
- **Visual_Monitor**: Component that displays camera feeds with visual overlays for detected red lights
- **Baseline_Measurement**: Initial red light count and size measurements taken within 1 second of trigger activation

## Requirements

### Requirement 1

**User Story:** As a system operator, I want to connect to an MQTT broker and monitor state change messages, so that I can track system state updates and count specific values.

#### Acceptance Criteria

1. WHEN the system starts THEN the MQTT_System SHALL connect to broker at 192.168.10.80 with client ID "receiver"
2. WHEN connected to the broker THEN the MQTT_System SHALL subscribe to the "changeState" topic
3. WHEN a message is received on "changeState" topic THEN the MQTT_System SHALL parse the JSON content and extract the state array
4. WHEN parsing the state array THEN the MQTT_System SHALL count the number of occurrences of value 1
5. WHEN processing each message THEN the MQTT_System SHALL return whether the message represents an update from the previous message

### Requirement 2

**User Story:** As a monitoring operator, I want to control USB cameras based on MQTT message updates, so that I can capture video feeds when system state changes occur.

#### Acceptance Criteria

1. WHEN the system initializes THEN the Camera_Monitor SHALL open 6 USB cameras and create video windows
2. WHEN an MQTT message update is detected THEN the Camera_Monitor SHALL activate all cameras to start capturing
3. WHEN cameras are activated THEN the Red_Light_Detector SHALL establish baseline measurements within 1 second including red light count and total area per camera
4. WHILE cameras are monitoring THEN the Red_Light_Detector SHALL continuously track red light counts and areas in all feeds
5. WHEN red light count decreases OR total red light area changes in any camera feed before the next MQTT trigger THEN the Trigger_Publisher SHALL send an empty message to "receiver/triggered" topic

### Requirement 3

**User Story:** As a system administrator, I want reliable message parsing and error handling, so that the system operates robustly in production environments.

#### Acceptance Criteria

1. WHEN receiving malformed JSON messages THEN the MQTT_System SHALL handle parsing errors gracefully and log the error
2. WHEN camera initialization fails THEN the Camera_Monitor SHALL report which cameras failed and continue with available cameras
3. WHEN MQTT connection is lost THEN the MQTT_System SHALL attempt to reconnect automatically
4. WHEN red light detection fails THEN the Red_Light_Detector SHALL log the error and continue monitoring other cameras
5. WHEN publishing trigger messages THEN the Trigger_Publisher SHALL confirm message delivery or retry on failure

### Requirement 4

**User Story:** As a monitoring operator, I want to visually monitor all camera feeds with detection overlays, so that I can observe the system's red light detection in real-time.

#### Acceptance Criteria

1. WHEN the system starts THEN the Visual_Monitor SHALL create display windows for all 6 camera feeds
2. WHEN red lights are detected THEN the Visual_Monitor SHALL draw green rectangular boxes around each detected red light position
3. WHILE monitoring is active THEN the Visual_Monitor SHALL continuously update the display with current camera frames and detection overlays
4. WHEN detection status changes THEN the Visual_Monitor SHALL update the overlay indicators in real-time
5. WHEN a camera feed fails THEN the Visual_Monitor SHALL display an error indicator in the corresponding window

### Requirement 5

**User Story:** As a system administrator, I want to dynamically configure camera parameters, so that I can optimize camera settings during debugging and testing phases.

#### Acceptance Criteria

1. WHEN the system loads configuration THEN the Camera_Monitor SHALL read camera parameter settings from configuration file
2. WHEN brightness settings are specified THEN the Camera_Monitor SHALL apply brightness adjustments to all cameras
3. WHEN exposure time settings are specified THEN the Camera_Monitor SHALL configure exposure parameters for all cameras
4. WHEN configuration file is updated THEN the Camera_Monitor SHALL allow runtime parameter updates without system restart
5. WHEN invalid camera parameters are provided THEN the Camera_Monitor SHALL log warnings and use default values