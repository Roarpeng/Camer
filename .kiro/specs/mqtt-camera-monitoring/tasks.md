# Implementation Plan

- [x] 1. Set up project structure and dependencies
  - Create main project directory structure with separate modules
  - Set up requirements.txt with necessary Python packages (paho-mqtt, opencv-python, numpy, pytest, hypothesis)
  - Initialize configuration management for MQTT broker settings
  - _Requirements: 1.1, 2.1_

- [x] 2. Implement MQTT client component
  - [x] 2.1 Create MQTT connection and subscription functionality
    - Implement MQTTClient class with connection to 192.168.10.80
    - Add subscription to "changeState" topic with client ID "receiver"
    - Implement connection error handling and logging
    - _Requirements: 1.1, 1.2, 3.3_

  - [x] 2.2 Implement JSON message parsing and state counting
    - Add JSON parsing functionality for state messages
    - Implement counting logic for value "1" in state arrays
    - Add message update detection by comparing consecutive messages
    - _Requirements: 1.3, 1.4, 1.5_

  - [ ]* 2.3 Write property test for JSON message parsing
    - **Property 1: JSON Message Parsing**
    - **Validates: Requirements 1.3**

  - [ ]* 2.4 Write property test for value counting accuracy
    - **Property 2: Value Counting Accuracy**
    - **Validates: Requirements 1.4**

  - [ ]* 2.5 Write property test for message update detection
    - **Property 3: Message Update Detection**
    - **Validates: Requirements 1.5**

  - [ ]* 2.6 Write property test for graceful JSON error handling
    - **Property 8: Graceful JSON Error Handling**
    - **Validates: Requirements 3.1**

- [x] 3. Implement camera manager component
  - [x] 3.1 Create USB camera initialization and management
    - Implement CameraManager class to handle 6 USB cameras
    - Add camera detection and initialization logic
    - Create video window display functionality
    - _Requirements: 2.1, 3.2_

  - [ ] 3.2 Implement camera activation and frame capture with dynamic parameters
    - Add camera activation triggered by MQTT updates
    - Implement continuous frame capture from all cameras
    - Add dynamic camera parameter configuration (brightness, exposure, etc.)
    - Add frame buffer management and cleanup
    - _Requirements: 2.2, 2.4, 5.1, 5.2, 5.3_

  - [ ]* 3.3 Write property test for camera failure recovery
    - **Property 9: Camera Failure Recovery**
    - **Validates: Requirements 3.2**

  - [ ]* 3.4 Write property test for camera activation on update
    - **Property 4: Camera Activation on Update**
    - **Validates: Requirements 2.2**

- [x] 4. Implement red light detection component
  - [x] 4.1 Create red light detection algorithm
    - Implement RedLightDetector class with color detection
    - Add HSV color space conversion for red light detection
    - Implement contour detection and counting logic
    - _Requirements: 2.3, 2.4_

  - [x] 4.2 Implement baseline tracking and comparison with area detection
    - Add baseline red light count and area storage per camera
    - Implement 1-second baseline establishment timing
    - Implement continuous monitoring with count and area comparison
    - Add decrease/change detection logic for both count and area
    - _Requirements: 2.3, 2.4, 2.5_

  - [ ]* 4.3 Write property test for baseline count establishment
    - **Property 5: Baseline Count Establishment**
    - **Validates: Requirements 2.3**

  - [ ]* 4.4 Write property test for continuous light monitoring
    - **Property 6: Continuous Light Monitoring**
    - **Validates: Requirements 2.4**

  - [ ]* 4.5 Write property test for trigger on light decrease
    - **Property 7: Trigger on Light Decrease**
    - **Validates: Requirements 2.5**

  - [ ]* 4.6 Write property test for detection error resilience
    - **Property 11: Detection Error Resilience**
    - **Validates: Requirements 3.4**

- [-] 5. Implement trigger publisher component
  - [x] 5.1 Create MQTT trigger message publisher
    - Implement TriggerPublisher class for sending empty messages
    - Add publishing to "receiver/triggered" topic
    - Implement message delivery confirmation and retry logic
    - _Requirements: 2.5, 3.5_

  - [ ]* 5.2 Write property test for message delivery reliability
    - **Property 12: Message Delivery Reliability**
    - **Validates: Requirements 3.5**

- [x] 6. Implement visual monitoring component
  - [x] 6.1 Create visual monitor for camera feeds with detection overlays
    - Implement VisualMonitor class for displaying all 6 camera feeds
    - Add green bounding box overlays for detected red lights
    - Implement real-time display updates with detection status
    - Add error indicators for failed cameras
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 6.2 Write property test for baseline timing accuracy
    - **Property 13: Baseline Timing Accuracy**
    - **Validates: Requirements 2.3**

  - [ ]* 6.3 Write property test for area change detection
    - **Property 14: Area Change Detection**
    - **Validates: Requirements 2.5**

  - [ ]* 6.4 Write property test for visual overlay accuracy
    - **Property 15: Visual Overlay Accuracy**
    - **Validates: Requirements 4.2**

  - [ ]* 6.5 Write property test for dynamic parameter application
    - **Property 16: Dynamic Parameter Application**
    - **Validates: Requirements 5.4**

- [x] 7. Implement main controller and system integration
  - [x] 7.1 Create main controller class
    - Implement MainController to coordinate all components
    - Add system initialization and startup sequence
    - Implement main event loop for continuous monitoring
    - _Requirements: 1.1, 2.1, 2.2_

  - [x] 7.2 Integrate MQTT, camera, and visual monitoring components
    - Connect MQTT message updates to camera activation
    - Link red light decrease/area change detection to trigger publishing
    - Integrate visual monitor with detection system
    - Add proper error handling and system state management
    - _Requirements: 2.2, 2.5, 4.3, 4.4_

  - [ ]* 7.3 Write property test for MQTT reconnection
    - **Property 10: MQTT Reconnection**
    - **Validates: Requirements 3.3**

- [x] 8. Checkpoint - Ensure core implementation works
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Add configuration and logging
  - [x] 9.1 Implement configuration management
    - Create configuration file for MQTT broker settings
    - Add camera configuration options (count, resolution)
    - Implement red light detection sensitivity settings
    - _Requirements: 1.1, 2.1_

  - [x] 9.2 Add comprehensive logging system
    - Implement structured logging for all components
    - Add error logging for connection failures and camera issues
    - Create monitoring logs for red light count changes
    - _Requirements: 3.1, 3.2, 3.4_

- [x] 10. Create main application entry point
  - [x] 10.1 Implement main application script
    - Create main.py with command-line interface
    - Add graceful shutdown handling for cameras and MQTT
    - Implement signal handling for clean system exit
    - _Requirements: 1.1, 2.1_

  - [ ]* 10.2 Write integration tests for complete system flow
    - Test end-to-end message processing and camera triggering
    - Verify complete workflow from MQTT message to trigger publication
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.5_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.