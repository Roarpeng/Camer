# Implementation Plan

- [x] 1. Create PySide GUI main window structure




  - Create main GUI application class with PySide6
  - Set up main window with left and right panel layout
  - Initialize basic window properties and styling
  - _Requirements: 4.1, 5.1_

- [x] 2. Implement camera configuration panel (left side)






  - [x] 2.1 Create camera configuration widgets


    - Add enable/disable checkboxes for each of 6 cameras (Camera 0-5)
    - Add camera ID selection dropdowns (0-5) for each enabled camera
    - Add mask file path input fields with file browser buttons for each enabled camera (must be 1920x1080 resolution)
    - Add baseline red light count input fields for each camera
    - Add comparison threshold input fields for each camera
    - Create 6 camera configuration rows with individual controls
    - _Requirements: 4.2, 3.3_

  - [x] 2.2 Add system parameter configuration


    - Add delay time input field (default 0.4s) with auto-save to config file
    - Add comparison threshold input field (default 2) with auto-save to config file
    - Add monitoring interval input field (default 0.2s) with auto-save to config file
    - Implement parameter validation and automatic configuration file updates
    - _Requirements: 3.1, 3.4, 3.5_

  - [ ]* 2.3 Write property test for GUI configuration elements
    - **Property 12: GUI Configuration Elements**
    - **Validates: Requirements 4.2**

  - [ ]* 2.4 Write property test for camera configuration validation
    - **Property 9: Camera Configuration Validation**
    - **Validates: Requirements 3.3**

- [x] 3. Implement system status panel (right side)





  - [x] 3.1 Create MQTT status display


    - Add MQTT connection status indicator
    - Add last message timestamp display
    - Add connection information text area
    - _Requirements: 5.2_

  - [x] 3.2 Create baseline events log


    - Add scrollable text area for baseline establishment events
    - Display timestamp and triggered cameras information
    - Add automatic scrolling to latest events
    - _Requirements: 5.3_

  - [x] 3.3 Create trigger events log


    - Add scrollable text area for receiver trigger events
    - Display device ID, timestamp, and camera information
    - Show baseline count vs trigger count details
    - _Requirements: 5.4_

  - [x] 3.4 Add system health indicators


    - Display number of cameras initialized and enabled
    - Show monitoring active status
    - Display last error messages
    - _Requirements: 5.5_

  - [ ]* 3.5 Write property test for MQTT status updates
    - **Property 16: MQTT Status Updates**
    - **Validates: Requirements 5.2**

  - [ ]* 3.6 Write property test for baseline event logging
    - **Property 17: Baseline Event Logging**
    - **Validates: Requirements 5.3**

- [x] 4. Implement camera monitoring display




  - [x] 4.1 Create camera status widgets

    - Add baseline red light count display for each of the 6 cameras (show only for enabled cameras)
    - Add current detection count display for each enabled camera
    - Add trigger status indicators for each enabled camera
    - Show "disabled" status for cameras that are not enabled
    - Update displays in real-time during monitoring
    - _Requirements: 4.3, 4.4_

  - [ ]* 4.2 Write property test for real-time camera status updates
    - **Property 13: Real-time Camera Status Updates**
    - **Validates: Requirements 4.3**

  - [ ]* 4.3 Write property test for real-time monitoring updates
    - **Property 14: Real-time Monitoring Updates**
    - **Validates: Requirements 4.4**

- [x] 5. Create GUI wrapper for existing FinalProductionSystem





  - [x] 5.1 Implement system integration class


    - Create wrapper class that interfaces with existing FinalProductionSystem
    - Modify existing system to support up to 6 USB cameras instead of current single camera
    - Ensure cameras use 1920x1080 resolution to match mask files
    - Add methods to start/stop the existing system with GUI configuration
    - Implement configuration parameter passing for enabled cameras only
    - _Requirements: 3.2_

  - [x] 5.2 Add configuration application logic


    - Implement dynamic camera enable/disable functionality (only initialize enabled cameras)
    - Apply individual mask files to each enabled camera
    - Pass GUI-configured baseline counts and comparison thresholds to each camera
    - Implement dynamic parameter updates to running system with automatic config file saving
    - Validate mask file paths and ensure 1920x1080 resolution compatibility
    - Ensure no additional camera parameters are applied (use cameras directly as in existing system)
    - _Requirements: 3.2, 6.4_

  - [ ]* 5.3 Write property test for dynamic configuration updates
    - **Property 8: Dynamic Configuration Updates**
    - **Validates: Requirements 3.2**

  - [ ]* 5.4 Write property test for configuration change validation
    - **Property 15: Configuration Change Validation**
    - **Validates: Requirements 4.5**

- [x] 6. Implement real-time status monitoring





  - [x] 6.1 Create status polling mechanism


    - Add timer-based polling of existing system status
    - Extract camera states, MQTT status, and system health
    - Update GUI displays with current information
    - _Requirements: 4.4, 5.2_

  - [x] 6.2 Add event logging integration


    - Capture baseline establishment events from existing system
    - Capture trigger events and display in GUI
    - Implement automatic log scrolling and timestamp formatting
    - _Requirements: 5.3, 5.4_

  - [ ]* 6.3 Write property test for trigger event logging
    - **Property 18: Trigger Event Logging**
    - **Validates: Requirements 5.4**

- [x] 7. Add error handling and validation





  - [x] 7.1 Implement input validation


    - Validate camera ID ranges (0-5) and prevent duplicate camera ID assignments
    - Check mask file existence, format, and ensure 1920x1080 resolution for each enabled camera
    - Validate parameter ranges for delay time, baseline counts, and comparison thresholds
    - Ensure at least one camera is enabled before starting monitoring
    - Ensure no camera parameter modifications are applied
    - _Requirements: 6.4_

  - [x] 7.2 Add error display functionality


    - Show error messages in GUI status panel
    - Display system health indicators
    - Handle camera initialization failures gracefully
    - _Requirements: 5.5, 6.2_

  - [ ]* 7.3 Write property test for error display
    - **Property 19: Error Display**
    - **Validates: Requirements 5.5**

  - [ ]* 7.4 Write property test for mask file validation
    - **Property 23: Mask File Validation**
    - **Validates: Requirements 6.4**

- [x] 8. Create main GUI application entry point




  - [x] 8.1 Implement main GUI application


    - Create main.py for GUI application startup
    - Add command-line options for GUI vs existing system modes
    - Implement proper application shutdown handling
    - _Requirements: 4.1, 5.1_

  - [x] 8.2 Add application configuration persistence


    - Save GUI configuration to file automatically when parameters change
    - Load previous configuration on startup
    - Implement real-time configuration file management (auto-save on parameter changes)
    - _Requirements: 3.1_

- [x] 9. Checkpoint - Ensure GUI integration works





  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Add comprehensive testing





  - [x]* 10.1 Write property test for timing-based baseline trigger


    - **Property 2: Timing-Based Baseline Trigger**
    - **Validates: Requirements 1.4**


  - [x]* 10.2 Write property test for threshold-based triggering

    - **Property 5: Threshold-Based Triggering**
    - **Validates: Requirements 2.3**

  - [x]* 10.3 Write property test for baseline reset on new message


    - **Property 6: Baseline Reset on New Message**
    - **Validates: Requirements 2.4**

  - [x]* 10.4 Write integration tests for GUI and system interaction


    - Test complete workflow from GUI configuration to system operation
    - Verify GUI updates reflect actual system state changes
    - _Requirements: 1.1, 2.1, 4.1, 5.1_

- [x] 11. Final checkpoint - Ensure complete system works




  - Ensure all tests pass, ask the user if questions arise.