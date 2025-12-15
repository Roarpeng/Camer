# Requirements Document

## Introduction

This system implements an MQTT-based monitoring solution with a PySide GUI that connects to a broker to receive state change messages and controls USB cameras based on message updates. The system monitors red light counts in camera feeds using configurable masks and sends trigger messages when light counts decrease below baseline thresholds. The system supports up to 6 cameras with individual configuration and provides real-time monitoring through a graphical interface.

## Glossary

- **MQTT_System**: The main system that handles MQTT communication and camera monitoring
- **State_Message**: JSON message containing an array of state values (0, 1, or 2)
- **Camera_Monitor**: Component that captures and analyzes video feeds from USB cameras using mask regions
- **Red_Light_Detector**: Algorithm that counts red lights in masked camera regions and tracks changes
- **Trigger_Publisher**: Component that publishes empty messages to the receiver topic
- **GUI_Interface**: PySide-based graphical user interface for system configuration and monitoring
- **Baseline_Measurement**: Initial red light count measurements taken after 0.4s delay when changeState updates
- **Camera_Mask**: Image mask file that defines the detection region for each camera
- **Detection_Parameters**: Configurable settings including delay time, comparison threshold, camera ID, and mask path

## Requirements

### Requirement 1

**User Story:** As a system operator, I want to connect to an MQTT broker and monitor state change messages with enhanced timing logic, so that I can establish baselines only when messages change and sufficient time has passed.

#### Acceptance Criteria

1. WHEN the system starts THEN the MQTT_System SHALL connect to broker at 192.168.10.80 with client ID "receiver"
2. WHEN connected to the broker THEN the MQTT_System SHALL subscribe to the "changeState" topic
3. WHEN a message is received on "changeState" topic THEN the MQTT_System SHALL parse the JSON content and extract the state array
4. WHEN a changeState message differs from the previous message AND 0.4 seconds have elapsed since the last update THEN the MQTT_System SHALL trigger baseline establishment
5. WHEN baseline is triggered THEN the Camera_Monitor SHALL capture frames and establish red light count baselines for all enabled cameras

### Requirement 2

**User Story:** As a monitoring operator, I want to monitor camera feeds with configurable masks and detection parameters, so that I can accurately detect changes in specific regions of interest.

#### Acceptance Criteria

1. WHEN baseline is established THEN the Red_Light_Detector SHALL monitor camera feeds every 0.2 seconds using the configured mask for each enabled camera
2. WHEN monitoring active cameras THEN the Red_Light_Detector SHALL count red lights only within the masked region for each camera
3. WHEN red light count decreases by more than the configured threshold compared to baseline THEN the Trigger_Publisher SHALL send an empty message to "receiver/triggered" topic
4. WHEN a new changeState update occurs THEN the system SHALL re-establish baselines and reset monitoring cycles
5. WHEN cameras are not enabled THEN the Camera_Monitor SHALL skip monitoring for those specific camera IDs

### Requirement 3

**User Story:** As a system administrator, I want to configure monitoring parameters dynamically, so that I can adjust detection sensitivity and camera settings without restarting the system.

#### Acceptance Criteria

1. WHEN the system loads THEN the Detection_Parameters SHALL include configurable delay time, comparison threshold, camera ID mappings, and mask file paths
2. WHEN parameters are updated through the GUI THEN the system SHALL apply changes to active monitoring without requiring restart
3. WHEN a camera is enabled THEN the operator SHALL specify both camera ID and corresponding mask file path
4. WHEN comparison threshold is modified THEN the Red_Light_Detector SHALL use the new threshold for subsequent baseline comparisons
5. WHEN delay time is changed THEN the MQTT_System SHALL use the new timing for changeState message processing

### Requirement 4

**User Story:** As a monitoring operator, I want a PySide GUI interface to configure cameras and monitor system status, so that I can easily manage up to 6 cameras and view real-time information.

#### Acceptance Criteria

1. WHEN the GUI starts THEN the GUI_Interface SHALL display a left panel with camera configuration controls for up to 6 cameras
2. WHEN configuring a camera THEN the GUI_Interface SHALL provide fields for camera ID, mask file path, and enable/disable checkbox
3. WHEN a camera is enabled THEN the GUI_Interface SHALL display current baseline red light count, current detection count, and trigger status
4. WHEN cameras are monitoring THEN the GUI_Interface SHALL update detection information in real-time
5. WHEN camera configuration changes THEN the GUI_Interface SHALL validate inputs and apply changes to the monitoring system

### Requirement 5

**User Story:** As a system administrator, I want to monitor overall system status and MQTT information, so that I can track system health and troubleshoot issues.

#### Acceptance Criteria

1. WHEN the GUI starts THEN the GUI_Interface SHALL display a right panel with overall system status information
2. WHEN MQTT connection status changes THEN the GUI_Interface SHALL update and display current MQTT connection state
3. WHEN changeState messages trigger baseline establishment THEN the GUI_Interface SHALL log and display baseline trigger events
4. WHEN receiver triggers are sent THEN the GUI_Interface SHALL display device ID trigger information with timestamps
5. WHEN system errors occur THEN the GUI_Interface SHALL display error messages and system health indicators

### Requirement 6

**User Story:** As a system administrator, I want reliable error handling and system recovery, so that the monitoring system operates robustly in production environments.

#### Acceptance Criteria

1. WHEN receiving malformed JSON messages THEN the MQTT_System SHALL handle parsing errors gracefully and log the error
2. WHEN camera initialization fails THEN the Camera_Monitor SHALL report which cameras failed and continue with available cameras
3. WHEN MQTT connection is lost THEN the MQTT_System SHALL attempt to reconnect automatically and update GUI status
4. WHEN mask files are missing or invalid THEN the Red_Light_Detector SHALL log the error and disable the affected camera
5. WHEN publishing trigger messages THEN the Trigger_Publisher SHALL confirm message delivery or retry on failure