"""
Main Controller Component

Coordinates all system components and manages the main event loop
for continuous monitoring.
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, List
from .config import SystemConfig
from .mqtt_client import MQTTClient
from .camera_manager import CameraManager
from .light_detector import RedLightDetector
from .trigger_publisher import TriggerPublisher
from .visual_monitor import VisualMonitor


class MainController:
    """
    Main controller to coordinate all components and manage system flow.
    
    Handles system initialization, startup sequence, and main event loop
    for continuous monitoring.
    """
    
    def __init__(self, config: SystemConfig):
        """
        Initialize main controller with system configuration
        
        Args:
            config: Complete system configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # System state
        self.running = False
        self.initialized = False
        self.shutdown_requested = False
        
        # Component instances
        self.mqtt_client: Optional[MQTTClient] = None
        self.camera_manager: Optional[CameraManager] = None
        self.light_detector: Optional[RedLightDetector] = None
        self.trigger_publisher: Optional[TriggerPublisher] = None
        self.visual_monitor: Optional[VisualMonitor] = None
        
        # Threading
        self.main_loop_thread: Optional[threading.Thread] = None
        self.monitoring_active = False
        
        self.logger.info("MainController initialized")
    
    def initialize_system(self) -> bool:
        """
        Set up all components and establish connections
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Initializing MQTT Camera Monitoring System")
            
            # Initialize MQTT client
            self.logger.info("Initializing MQTT client...")
            self.mqtt_client = MQTTClient(self.config.mqtt)
            if not self.mqtt_client.connect():
                self.logger.error("Failed to connect MQTT client")
                return False
            
            # Set up MQTT message callback
            self.mqtt_client.set_message_callback(self._handle_mqtt_message)
            
            # Initialize camera manager
            self.logger.info("Initializing camera manager...")
            self.camera_manager = CameraManager(self.config.cameras)
            try:
                active_cameras = self.camera_manager.initialize_cameras()
                self.logger.info(f"Initialized {len(active_cameras)} cameras: {active_cameras}")
            except RuntimeError as e:
                self.logger.error(f"Camera initialization failed: {e}")
                return False
            
            # Set up camera activation callback for baseline establishment
            self.camera_manager.set_activation_callback(self._on_camera_activation)
            
            # Initialize red light detector
            self.logger.info("Initializing red light detector...")
            self.light_detector = RedLightDetector(self.config.red_light_detection)
            
            # Initialize trigger publisher
            self.logger.info("Initializing trigger publisher...")
            self.trigger_publisher = TriggerPublisher(self.config.mqtt)
            if not self.trigger_publisher.connect():
                self.logger.error("Failed to connect trigger publisher")
                return False
            
            # Initialize visual monitor
            self.logger.info("Initializing visual monitor...")
            self.visual_monitor = VisualMonitor(
                self.config.visual_monitor, 
                self.config.cameras.count
            )
            if not self.visual_monitor.create_windows():
                self.logger.error("Failed to create visual monitor windows")
                return False
            
            # Display test frames to verify camera initialization
            self.camera_manager.display_test_frames()
            
            self.initialized = True
            self.logger.info("System initialization completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during system initialization: {e}")
            return False
    
    def run(self) -> None:
        """
        Main entry point to start the monitoring system
        
        Initializes all components and starts the main monitoring loop.
        """
        try:
            # Initialize system
            if not self.initialize_system():
                self.logger.error("System initialization failed, exiting")
                return
            
            # Start main monitoring loop
            self.logger.info("Starting main monitoring loop")
            self.running = True
            self.run_monitoring_loop()
            
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down")
        except Exception as e:
            self.logger.error(f"Error in main run loop: {e}")
        finally:
            self.shutdown()
    
    def run_monitoring_loop(self) -> None:
        """
        Main event loop for continuous monitoring
        
        Processes camera frames, detects red light changes, and manages
        the monitoring workflow.
        """
        self.logger.info("Main monitoring loop started")
        self.monitoring_active = True
        
        try:
            while self.running and not self.shutdown_requested:
                try:
                    # Check if cameras are active and capturing
                    if not self.camera_manager.is_capture_active():
                        # Wait for MQTT message to activate cameras
                        time.sleep(0.1)
                        continue
                    
                    # Get current frames from all cameras
                    frames = self.camera_manager.get_frames()
                    
                    # Process frames for red light detection
                    detection_results = []
                    trigger_needed = False
                    trigger_camera_ids = []
                    
                    for camera_id, frame in enumerate(frames):
                        if frame is None or not frame.is_valid:
                            detection_results.append(None)
                            # Show error in visual monitor for this camera
                            if frame is None:
                                self.visual_monitor.show_error(camera_id, "Camera disconnected")
                            else:
                                self.visual_monitor.show_error(camera_id, "Invalid frame")
                            continue
                        
                        # Process frame for red light detection
                        result = self.light_detector.process_camera_frame(frame)
                        
                        # Check if trigger is needed
                        if result.get('should_trigger', False):
                            trigger_needed = True
                            trigger_camera_ids.append(camera_id)
                            
                            # Log detailed trigger information
                            baseline_count = result.get('baseline_count', 0)
                            current_count = result.get('current_count', 0)
                            baseline_area = result.get('baseline_area', 0.0)
                            current_area = result.get('current_area', 0.0)
                            
                            self.logger.info(
                                f"Trigger condition detected for camera {camera_id}: "
                                f"count {baseline_count} -> {current_count}, "
                                f"area {baseline_area:.2f} -> {current_area:.2f}"
                            )
                        
                        # Store detection for visual display
                        detection = result.get('detection')
                        detection_results.append(detection)
                    
                    # Update visual monitor with frames and detection results
                    self.visual_monitor.update_display(frames, detection_results)
                    
                    # Log trigger summary if needed
                    if trigger_needed:
                        self.logger.info(f"Trigger needed from cameras: {trigger_camera_ids}")
                    
                    # Handle trigger if needed
                    if trigger_needed:
                        self._handle_trigger_event()
                    
                    # Small delay to prevent excessive CPU usage
                    time.sleep(0.033)  # ~30 FPS processing rate
                    
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop iteration: {e}")
                    
                    # Check if components are still healthy
                    if not self._check_component_health():
                        self.logger.error("Component health check failed, requesting shutdown")
                        self.request_shutdown()
                        break
                    
                    time.sleep(0.1)  # Brief pause before continuing
            
        except Exception as e:
            self.logger.error(f"Fatal error in monitoring loop: {e}")
        finally:
            self.monitoring_active = False
            self.logger.info("Main monitoring loop ended")
    
    def _handle_mqtt_message(self, message_data: Dict[str, Any]) -> None:
        """
        Handle incoming MQTT messages and trigger camera activation
        
        Args:
            message_data: MQTT message data with update information
        """
        try:
            self.logger.debug(f"Processing MQTT message: {message_data}")
            
            # Extract message details for logging
            topic = message_data.get('topic', 'unknown')
            payload = message_data.get('payload', {})
            count_of_ones = payload.get('count_of_ones', 0) if payload else 0
            
            self.logger.info(f"MQTT message received on topic '{topic}' with {count_of_ones} ones")
            
            # Check if this is an update that should trigger camera activation
            is_update = message_data.get('is_update', False)
            
            if is_update:
                self.logger.info("MQTT message update detected, activating cameras")
                self._handle_mqtt_update()
            else:
                self.logger.debug("MQTT message received but no update detected")
                
        except Exception as e:
            self.logger.error(f"Error handling MQTT message: {e}")
    
    def _handle_mqtt_update(self) -> None:
        """
        Process MQTT message update and activate camera monitoring
        
        This method coordinates the response to MQTT message updates by:
        1. Activating cameras for continuous capture
        2. Starting baseline establishment process
        3. Beginning continuous monitoring
        """
        try:
            # Activate cameras through camera manager
            if self.camera_manager.activate_on_mqtt_update():
                self.logger.info("Cameras activated successfully")
                
                # Reset any previous baselines
                self.light_detector.reset_baselines()
                
                # Start baseline establishment process
                self.light_detector.start_baseline_establishment()
                self.logger.info("Baseline establishment process started")
                
            else:
                self.logger.error("Failed to activate cameras")
                
        except Exception as e:
            self.logger.error(f"Error handling MQTT update: {e}")
    
    def _on_camera_activation(self) -> None:
        """
        Callback function called when cameras are activated
        
        This is used to coordinate baseline establishment timing
        with camera activation.
        """
        try:
            self.logger.debug("Camera activation callback triggered")
            
            # The baseline establishment is already started in _handle_mqtt_update
            # This callback can be used for additional coordination if needed
            
        except Exception as e:
            self.logger.error(f"Error in camera activation callback: {e}")
    
    def _handle_trigger_event(self) -> None:
        """
        Handle red light decrease/area change detection and publish trigger
        
        This method is called when a trigger condition is detected
        (red light count decrease or area change).
        """
        try:
            self.logger.info("Handling trigger event - red light change detected")
            
            # Get current baseline status for logging
            baseline_status = self.light_detector.get_baseline_status()
            self.logger.debug(f"Baseline status at trigger: {baseline_status}")
            
            # Publish trigger message
            if self.trigger_publisher.publish_trigger():
                self.logger.info("Trigger message published successfully")
                
                # Reset camera activation trigger for next cycle
                self.camera_manager.reset_activation_trigger()
                
                # Reset baselines for next monitoring cycle
                self.light_detector.reset_baselines()
                
                # Stop current capture to wait for next MQTT update
                self.camera_manager.stop_capture()
                
                # Clean up frame buffers
                self.camera_manager.cleanup_frame_buffers()
                
                self.logger.info("System reset and ready for next MQTT trigger")
                
            else:
                self.logger.error("Failed to publish trigger message - retrying...")
                # Attempt retry after brief delay
                time.sleep(0.5)
                if self.trigger_publisher.publish_trigger():
                    self.logger.info("Trigger message published successfully on retry")
                else:
                    self.logger.error("Failed to publish trigger message after retry")
                
        except Exception as e:
            self.logger.error(f"Error handling trigger event: {e}")
    
    def shutdown(self) -> None:
        """
        Gracefully shutdown all system components
        
        Stops monitoring, disconnects from MQTT, releases cameras,
        and cleans up resources.
        """
        try:
            self.logger.info("Shutting down MQTT Camera Monitoring System")
            self.shutdown_requested = True
            self.running = False
            
            # Stop monitoring loop
            if self.monitoring_active:
                self.logger.info("Stopping monitoring loop...")
                # Wait briefly for loop to finish
                time.sleep(0.5)
            
            # Stop camera capture
            if self.camera_manager:
                self.logger.info("Stopping camera capture...")
                self.camera_manager.stop_capture()
                time.sleep(0.2)  # Allow capture threads to finish
            
            # Close visual monitor
            if self.visual_monitor:
                self.logger.info("Closing visual monitor...")
                self.visual_monitor.close_windows()
            
            # Disconnect MQTT clients
            if self.mqtt_client:
                self.logger.info("Disconnecting MQTT client...")
                self.mqtt_client.disconnect()
            
            if self.trigger_publisher:
                self.logger.info("Disconnecting trigger publisher...")
                self.trigger_publisher.disconnect()
            
            # Release camera resources
            if self.camera_manager:
                self.logger.info("Releasing camera resources...")
                self.camera_manager.release_cameras()
            
            self.logger.info("System shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get current system status information
        
        Returns:
            Dict containing comprehensive system status
        """
        try:
            status = {
                'initialized': self.initialized,
                'running': self.running,
                'monitoring_active': self.monitoring_active,
                'shutdown_requested': self.shutdown_requested
            }
            
            # Add component status if available
            if self.mqtt_client:
                status['mqtt'] = self.mqtt_client.get_connection_status()
            
            if self.camera_manager:
                status['cameras'] = {
                    'capture_active': self.camera_manager.is_capture_active(),
                    'camera_status': self.camera_manager.get_camera_status(),
                    'activation_status': self.camera_manager.get_activation_status()
                }
            
            if self.light_detector:
                status['light_detection'] = self.light_detector.get_baseline_status()
            
            if self.trigger_publisher:
                status['trigger_publisher'] = self.trigger_publisher.get_status()
            
            if self.visual_monitor:
                status['visual_monitor'] = self.visual_monitor.get_window_status()
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}
    
    def is_running(self) -> bool:
        """
        Check if system is currently running
        
        Returns:
            bool: True if system is running
        """
        return self.running and not self.shutdown_requested
    
    def _check_component_health(self) -> bool:
        """
        Check health of all system components
        
        Returns:
            bool: True if all components are healthy, False otherwise
        """
        try:
            # Check MQTT client connection
            if not self.mqtt_client or not self.mqtt_client.connected:
                self.logger.warning("MQTT client not connected")
                return False
            
            # Check trigger publisher connection
            if not self.trigger_publisher or not self.trigger_publisher.connected:
                self.logger.warning("Trigger publisher not connected")
                return False
            
            # Check if any cameras are still active
            if self.camera_manager:
                active_cameras = sum(self.camera_manager.active_cameras)
                if active_cameras == 0:
                    self.logger.warning("No active cameras available")
                    return False
            
            # Check visual monitor
            if not self.visual_monitor or not self.visual_monitor.is_active():
                self.logger.warning("Visual monitor not active")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking component health: {e}")
            return False
    
    def request_shutdown(self) -> None:
        """
        Request graceful system shutdown
        
        This can be called from signal handlers or other components
        to initiate shutdown.
        """
        self.logger.info("Shutdown requested")
        self.shutdown_requested = True
        self.running = False