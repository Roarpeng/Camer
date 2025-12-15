"""
Enhanced MQTT Client Component

Handles all MQTT communication including connection, subscription,
message parsing, and publishing with intelligent reconnection,
performance monitoring, and connection quality assessment.
"""

import json
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
import paho.mqtt.client as mqtt
from .config import MQTTConfig
from .data_models import (
    ConnectionMetrics, ConnectionState, ConnectionEvent, 
    MQTTConfiguration, QualityReport
)


class MQTTClientEnhanced:
    """
    Enhanced MQTT client for handling broker communication with intelligent 
    reconnection, performance monitoring, and connection quality assessment.
    
    Manages connection to MQTT broker, subscribes to state change messages,
    parses JSON payloads, publishes trigger messages, and provides detailed
    connection metrics and quality monitoring.
    """
    
    def __init__(self, config: MQTTConfig):
        """
        Initialize enhanced MQTT client with configuration
        
        Args:
            config: MQTT configuration settings
        """
        self.config = config
        self.client = mqtt.Client(client_id=config.client_id)
        self.logger = logging.getLogger(__name__)
        
        # Connection state management
        self.connection_state = ConnectionState.DISCONNECTED
        self.connected = False
        self.last_message_content = None
        self.last_message_time = None
        self.connection_start_time = None
        self.last_successful_connection = None
        
        # Callback management
        self.message_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.connection_callback: Optional[Callable[[ConnectionEvent], None]] = None
        
        # Performance monitoring
        self.metrics = ConnectionMetrics()
        self.connection_events: List[ConnectionEvent] = []
        self.message_latencies: List[float] = []
        self.publish_confirmations: Dict[int, float] = {}  # mid -> timestamp
        
        # Enhanced retry settings with exponential backoff
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = config.max_reconnect_attempts
        self.base_reconnect_delay = config.reconnect_delay
        self.max_reconnect_delay = 300  # 5 minutes maximum
        self.reconnect_thread = None
        self.stop_reconnect = False
        
        # Connection timeout handling
        self.connection_timeout = getattr(config, 'connection_timeout', 30)
        self.connection_timer = None
        
        # Quality monitoring
        self.quality_check_interval = 60  # seconds
        self.last_quality_check = None
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Set up MQTT client callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
    
    def connect_with_retry(self) -> bool:
        """
        Connect to MQTT broker with intelligent retry mechanism
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        return self._connect_internal(is_retry=False)
    
    def _connect_internal(self, is_retry: bool = False) -> bool:
        """
        Internal connection method with enhanced error handling and monitoring
        
        Args:
            is_retry: Whether this is a retry attempt
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            with self._lock:
                if self.connection_state == ConnectionState.CONNECTING:
                    self.logger.debug("Connection already in progress")
                    return False
                
                self.connection_state = ConnectionState.CONNECTING
                self.connection_start_time = time.time()
            
            self.logger.info(f"{'Reconnecting' if is_retry else 'Connecting'} to MQTT broker at {self.config.broker_host}:{self.config.broker_port}")
            
            # Record connection attempt
            self.metrics.last_connection_attempt = datetime.now()
            
            # Set connection timeout timer
            self._start_connection_timeout()
            
            # Attempt connection
            self.client.connect(
                self.config.broker_host,
                self.config.broker_port,
                self.config.keepalive
            )
            
            # Start the network loop in a separate thread
            self.client.loop_start()
            
            # Wait for connection to be established
            start_time = time.time()
            while (not self.connected and 
                   self.connection_state == ConnectionState.CONNECTING and
                   (time.time() - start_time) < self.connection_timeout):
                time.sleep(0.1)
            
            # Cancel timeout timer
            self._cancel_connection_timeout()
            
            if self.connected:
                self.logger.info("Successfully connected to MQTT broker")
                with self._lock:
                    self.reconnect_attempts = 0
                    self.connection_state = ConnectionState.CONNECTED
                    self.last_successful_connection = datetime.now()
                    self.metrics.last_successful_connection = self.last_successful_connection
                
                # Record successful connection event
                self._record_connection_event("connect", ConnectionState.CONNECTED)
                
                # Update connection uptime tracking
                self.connection_start_time = time.time()
                
                return True
            else:
                self.logger.error("Failed to connect to MQTT broker within timeout")
                with self._lock:
                    self.connection_state = ConnectionState.FAILED
                    self.metrics.last_error = "Connection timeout"
                
                # Record failed connection event
                self._record_connection_event("connect_failed", ConnectionState.FAILED, 
                                            error_message="Connection timeout")
                return False
                
        except Exception as e:
            error_msg = f"Error connecting to MQTT broker: {e}"
            self.logger.error(error_msg)
            
            with self._lock:
                self.connection_state = ConnectionState.FAILED
                self.metrics.last_error = str(e)
            
            # Record error event
            self._record_connection_event("connect_error", ConnectionState.FAILED, 
                                        error_message=str(e))
            
            self._cancel_connection_timeout()
            return False
    
    def disconnect_gracefully(self) -> None:
        """
        Gracefully disconnect from MQTT broker and clean up resources
        """
        try:
            with self._lock:
                self.stop_reconnect = True
                if self.reconnect_thread and self.reconnect_thread.is_alive():
                    self.reconnect_thread.join(timeout=5)
            
            self._cancel_connection_timeout()
            
            if self.connected:
                self.client.loop_stop()
                self.client.disconnect()
                
                with self._lock:
                    self.connected = False
                    self.connection_state = ConnectionState.DISCONNECTED
                
                # Update connection uptime
                if self.connection_start_time:
                    uptime = time.time() - self.connection_start_time
                    self.metrics.connection_uptime += uptime
                
                # Record disconnection event
                self._record_connection_event("disconnect", ConnectionState.DISCONNECTED)
                
                self.logger.info("Gracefully disconnected from MQTT broker")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from MQTT broker: {e}")
    
    def _start_connection_timeout(self):
        """Start connection timeout timer"""
        self._cancel_connection_timeout()
        self.connection_timer = threading.Timer(
            self.connection_timeout, 
            self._on_connection_timeout
        )
        self.connection_timer.start()
    
    def _cancel_connection_timeout(self):
        """Cancel connection timeout timer"""
        if self.connection_timer:
            self.connection_timer.cancel()
            self.connection_timer = None
    
    def _on_connection_timeout(self):
        """Handle connection timeout"""
        self.logger.warning(f"Connection timeout after {self.connection_timeout} seconds")
        with self._lock:
            if self.connection_state == ConnectionState.CONNECTING:
                self.connection_state = ConnectionState.FAILED
                self.metrics.last_error = "Connection timeout"
    
    def subscribe(self, topic: Optional[str] = None) -> bool:
        """
        Subscribe to MQTT topic
        
        Args:
            topic: Topic to subscribe to (uses config default if None)
            
        Returns:
            bool: True if subscription successful, False otherwise
        """
        if not self.connected:
            self.logger.error("Cannot subscribe: not connected to broker")
            return False
        
        topic = topic or self.config.subscribe_topic
        
        try:
            result, mid = self.client.subscribe(topic)
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Successfully subscribed to topic: {topic}")
                return True
            else:
                self.logger.error(f"Failed to subscribe to topic {topic}: {mqtt.error_string(result)}")
                return False
        except Exception as e:
            self.logger.error(f"Error subscribing to topic {topic}: {e}")
            return False
    
    def publish_with_confirmation(self, topic: str, payload: str = "") -> Dict[str, Any]:
        """
        Publish message to MQTT topic with confirmation tracking
        
        Args:
            topic: Topic to publish to
            payload: Message payload (empty string for trigger messages)
            
        Returns:
            Dict containing publish result with success status, message ID, and timing
        """
        if not self.connected:
            error_msg = "Cannot publish: not connected to broker"
            self.logger.error(error_msg)
            self.metrics.failed_messages += 1
            self.metrics.update_success_rate()
            return {
                'success': False,
                'error': error_msg,
                'message_id': None,
                'timestamp': datetime.now()
            }
        
        try:
            publish_time = time.time()
            result = self.client.publish(topic, payload)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                # Track publish confirmation
                self.publish_confirmations[result.mid] = publish_time
                
                # Update metrics
                self.metrics.total_messages_sent += 1
                self.metrics.update_success_rate()
                
                self.logger.debug(f"Published to topic {topic}, message ID: {result.mid}")
                
                return {
                    'success': True,
                    'message_id': result.mid,
                    'timestamp': datetime.now(),
                    'topic': topic
                }
            else:
                error_msg = f"Failed to publish to topic {topic}: {mqtt.error_string(result.rc)}"
                self.logger.error(error_msg)
                self.metrics.failed_messages += 1
                self.metrics.update_success_rate()
                
                return {
                    'success': False,
                    'error': error_msg,
                    'message_id': None,
                    'timestamp': datetime.now()
                }
                
        except Exception as e:
            error_msg = f"Error publishing to topic {topic}: {e}"
            self.logger.error(error_msg)
            self.metrics.failed_messages += 1
            self.metrics.update_success_rate()
            
            return {
                'success': False,
                'error': error_msg,
                'message_id': None,
                'timestamp': datetime.now()
            }
    
    def set_message_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Set callback function for processing received messages
        
        Args:
            callback: Function to call when message is received
        """
        self.message_callback = callback
    
    def set_connection_callback(self, callback: Callable[[ConnectionEvent], None]):
        """
        Set callback function for connection events
        
        Args:
            callback: Function to call when connection events occur
        """
        self.connection_callback = callback
    
    def _on_connect(self, client, userdata, flags, rc):
        """
        Enhanced callback for MQTT connection events
        
        Args:
            client: MQTT client instance
            userdata: User data
            flags: Connection flags
            rc: Connection result code
        """
        if rc == 0:
            with self._lock:
                self.connected = True
                self.connection_state = ConnectionState.CONNECTED
                self.last_successful_connection = datetime.now()
                self.metrics.last_successful_connection = self.last_successful_connection
            
            self.logger.info(f"Connected to MQTT broker with client ID: {self.config.client_id}")
            
            # Record successful connection event
            self._record_connection_event("connect", ConnectionState.CONNECTED)
            
            # Automatically subscribe to the configured topic
            self.subscribe()
            
            # Reset connection start time for uptime tracking
            self.connection_start_time = time.time()
            
        else:
            with self._lock:
                self.connected = False
                self.connection_state = ConnectionState.FAILED
                error_msg = f"Connection failed with result code: {rc}"
                self.metrics.last_error = error_msg
            
            self.logger.error(f"Failed to connect to MQTT broker. Result code: {rc}")
            
            # Record failed connection event
            self._record_connection_event("connect_failed", ConnectionState.FAILED, 
                                        error_message=f"Result code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """
        Enhanced callback for MQTT disconnection events
        
        Args:
            client: MQTT client instance
            userdata: User data
            rc: Disconnection result code
        """
        with self._lock:
            self.connected = False
            
            # Update connection uptime
            if self.connection_start_time:
                uptime = time.time() - self.connection_start_time
                self.metrics.connection_uptime += uptime
                self.connection_start_time = None
        
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection from MQTT broker. Result code: {rc}")
            
            with self._lock:
                self.connection_state = ConnectionState.RECONNECTING
                error_msg = f"Unexpected disconnection, result code: {rc}"
                self.metrics.last_error = error_msg
            
            # Record disconnection event
            self._record_connection_event("disconnect", ConnectionState.RECONNECTING, 
                                        error_message=error_msg)
            
            # Attempt intelligent reconnection
            self._attempt_intelligent_reconnect()
        else:
            with self._lock:
                self.connection_state = ConnectionState.DISCONNECTED
            
            self.logger.info("Cleanly disconnected from MQTT broker")
            
            # Record clean disconnection event
            self._record_connection_event("disconnect", ConnectionState.DISCONNECTED)
    
    def _on_message(self, client, userdata, msg):
        """
        Enhanced callback for received MQTT messages with performance tracking
        
        Args:
            client: MQTT client instance
            userdata: User data
            msg: Received message
        """
        try:
            receive_time = time.time()
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # Update message metrics
            self.metrics.total_messages_received += 1
            self.last_message_time = receive_time
            
            self.logger.debug(f"Received message on topic {topic}: {payload}")
            
            # Parse JSON message and process
            parsed_message = self.parse_state_message(payload)
            if parsed_message is not None:
                # Check if this is an update from the previous message
                is_update = self.is_message_update(parsed_message)
                
                # Add metadata to the parsed message
                message_data = {
                    'topic': topic,
                    'payload': parsed_message,
                    'is_update': is_update,
                    'timestamp': receive_time,
                    'receive_datetime': datetime.now()
                }
                
                # Call the message callback if set
                if self.message_callback:
                    self.message_callback(message_data)
                
        except Exception as e:
            error_msg = f"Error processing received message: {e}"
            self.logger.error(error_msg)
            with self._lock:
                self.metrics.last_error = error_msg
    
    def _on_publish(self, client, userdata, mid):
        """
        Enhanced callback for published message confirmation with latency tracking
        
        Args:
            client: MQTT client instance
            userdata: User data
            mid: Message ID
        """
        try:
            confirmation_time = time.time()
            
            # Calculate message latency if we have the publish time
            if mid in self.publish_confirmations:
                publish_time = self.publish_confirmations.pop(mid)
                latency = (confirmation_time - publish_time) * 1000  # Convert to milliseconds
                
                # Update latency metrics
                self.message_latencies.append(latency)
                
                # Keep only recent latencies (last 100 messages)
                if len(self.message_latencies) > 100:
                    self.message_latencies = self.message_latencies[-100:]
                
                # Update average latency
                self.metrics.average_latency = sum(self.message_latencies) / len(self.message_latencies)
                
                self.logger.debug(f"Message {mid} confirmed in {latency:.2f}ms")
            else:
                self.logger.debug(f"Message published successfully. Message ID: {mid}")
                
        except Exception as e:
            self.logger.error(f"Error processing publish confirmation: {e}")
    
    def _attempt_intelligent_reconnect(self):
        """
        Attempt intelligent reconnection with exponential backoff in separate thread
        """
        if self.stop_reconnect:
            return
            
        # Start reconnection in separate thread to avoid blocking
        if not self.reconnect_thread or not self.reconnect_thread.is_alive():
            self.reconnect_thread = threading.Thread(
                target=self._reconnect_worker,
                daemon=True
            )
            self.reconnect_thread.start()
    
    def _reconnect_worker(self):
        """
        Worker thread for handling reconnection attempts with exponential backoff
        """
        while not self.stop_reconnect and self.reconnect_attempts < self.max_reconnect_attempts:
            with self._lock:
                if self.connected or self.connection_state == ConnectionState.CONNECTED:
                    # Already connected, exit
                    return
                
                self.reconnect_attempts += 1
                
                # Calculate exponential backoff delay
                delay = min(
                    self.base_reconnect_delay * (2 ** (self.reconnect_attempts - 1)),
                    self.max_reconnect_delay
                )
            
            self.logger.info(f"Attempting to reconnect in {delay} seconds "
                           f"(attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            
            # Wait with periodic checks for stop signal
            for _ in range(int(delay * 10)):  # Check every 0.1 seconds
                if self.stop_reconnect:
                    return
                time.sleep(0.1)
            
            if self.stop_reconnect:
                return
            
            # Attempt reconnection
            self.logger.info(f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")
            
            # Update metrics
            with self._lock:
                self.metrics.reconnection_count += 1
            
            # Record reconnection attempt
            self._record_connection_event("reconnect_attempt", ConnectionState.RECONNECTING)
            
            if self._connect_internal(is_retry=True):
                self.logger.info("Successfully reconnected to MQTT broker")
                return
            else:
                self.logger.error(f"Reconnection attempt {self.reconnect_attempts} failed")
        
        # Maximum attempts reached
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error(f"Maximum reconnection attempts ({self.max_reconnect_attempts}) reached")
            with self._lock:
                self.connection_state = ConnectionState.FAILED
                self.metrics.last_error = f"Maximum reconnection attempts ({self.max_reconnect_attempts}) reached"
            
            # Record final failure
            self._record_connection_event("reconnect_failed", ConnectionState.FAILED,
                                        error_message="Maximum reconnection attempts reached")
    
    def parse_state_message(self, json_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON message and extract state array with value counting
        
        Args:
            json_str: JSON string containing state message
            
        Returns:
            Dict containing parsed state data with count of 1s, or None if parsing fails
        """
        try:
            # Parse JSON string
            message_data = json.loads(json_str)
            
            # Validate that 'state' field exists
            if 'state' not in message_data:
                self.logger.warning("Received message missing 'state' field")
                return None
            
            state_array = message_data['state']
            
            # Validate that state is a list
            if not isinstance(state_array, list):
                self.logger.warning("State field is not an array")
                return None
            
            # Count occurrences of value 1 in the state array
            count_of_ones = self.count_value_in_array(state_array, 1)
            
            # Return parsed data with count
            parsed_data = {
                'state': state_array,
                'count_of_ones': count_of_ones,
                'raw_message': message_data
            }
            
            self.logger.debug(f"Parsed state message: {len(state_array)} values, {count_of_ones} ones")
            return parsed_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON message: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error parsing state message: {e}")
            return None
    
    def count_value_in_array(self, array: List[Any], target_value: Any) -> int:
        """
        Count occurrences of a specific value in an array
        
        Args:
            array: List to search in
            target_value: Value to count
            
        Returns:
            int: Number of occurrences of target_value
        """
        try:
            return array.count(target_value)
        except Exception as e:
            self.logger.error(f"Error counting values in array: {e}")
            return 0
    
    def is_message_update(self, current_message: Dict[str, Any]) -> bool:
        """
        Determine if current message represents an update from the previous message
        
        Args:
            current_message: Current parsed message data
            
        Returns:
            bool: True if message is different from previous, False otherwise
        """
        try:
            # If no previous message, this is considered an update
            if self.last_message_content is None:
                self.last_message_content = current_message
                return True
            
            # Compare current message with previous message
            current_state = current_message.get('state', [])
            previous_state = self.last_message_content.get('state', [])
            
            # Check if state arrays are different
            is_different = current_state != previous_state
            
            # Update stored message for next comparison
            self.last_message_content = current_message
            
            if is_different:
                self.logger.debug("Message update detected: state array changed")
            else:
                self.logger.debug("No message update: state array unchanged")
            
            return is_different
            
        except Exception as e:
            self.logger.error(f"Error comparing messages for update detection: {e}")
            # In case of error, assume it's an update to be safe
            self.last_message_content = current_message
            return True
    
    def get_connection_metrics(self) -> ConnectionMetrics:
        """
        Get comprehensive connection performance metrics
        
        Returns:
            ConnectionMetrics: Current performance metrics
        """
        with self._lock:
            # Update current uptime if connected
            if self.connected and self.connection_start_time:
                current_uptime = time.time() - self.connection_start_time
                total_uptime = self.metrics.connection_uptime + current_uptime
            else:
                total_uptime = self.metrics.connection_uptime
            
            # Create updated metrics
            updated_metrics = ConnectionMetrics(
                connection_uptime=total_uptime,
                message_success_rate=self.metrics.message_success_rate,
                average_latency=self.metrics.average_latency,
                reconnection_count=self.metrics.reconnection_count,
                last_error=self.metrics.last_error,
                quality_score=self.metrics.quality_score,
                total_messages_sent=self.metrics.total_messages_sent,
                total_messages_received=self.metrics.total_messages_received,
                failed_messages=self.metrics.failed_messages,
                last_successful_connection=self.metrics.last_successful_connection,
                last_connection_attempt=self.metrics.last_connection_attempt
            )
            
            # Calculate and update quality score
            updated_metrics.calculate_quality_score()
            
            return updated_metrics
    
    def check_connection_quality(self) -> QualityReport:
        """
        Assess current connection quality and generate report
        
        Returns:
            QualityReport: Detailed quality assessment
        """
        metrics = self.get_connection_metrics()
        
        # Calculate individual quality scores
        connection_stability = self._calculate_stability_score()
        message_reliability = metrics.message_success_rate
        performance_score = self._calculate_performance_score()
        
        # Calculate overall quality (weighted average)
        overall_quality = (
            connection_stability * 0.4 +  # 40% weight on stability
            message_reliability * 0.4 +   # 40% weight on reliability  
            performance_score * 0.2        # 20% weight on performance
        )
        
        # Identify issues and recommendations
        issues = []
        recommendations = []
        
        if connection_stability < 70:
            issues.append("连接不稳定，频繁重连")
            recommendations.append("检查网络连接质量")
            
        if message_reliability < 90:
            issues.append("消息传输可靠性较低")
            recommendations.append("检查MQTT代理状态")
            
        if performance_score < 60:
            issues.append("连接性能较差")
            recommendations.append("优化网络配置或更换代理服务器")
            
        if metrics.average_latency > 1000:
            issues.append("消息延迟过高")
            recommendations.append("检查网络延迟和代理响应时间")
        
        return QualityReport(
            timestamp=datetime.now(),
            overall_quality=overall_quality,
            connection_stability=connection_stability,
            message_reliability=message_reliability,
            performance_score=performance_score,
            issues_detected=issues,
            recommendations=recommendations
        )
    
    def _calculate_stability_score(self) -> float:
        """Calculate connection stability score based on reconnection history"""
        if self.metrics.reconnection_count == 0:
            return 100.0
        elif self.metrics.reconnection_count <= 2:
            return 85.0
        elif self.metrics.reconnection_count <= 5:
            return 70.0
        elif self.metrics.reconnection_count <= 10:
            return 50.0
        else:
            return 25.0
    
    def _calculate_performance_score(self) -> float:
        """Calculate performance score based on latency and uptime"""
        latency_score = 100.0
        if self.metrics.average_latency > 0:
            if self.metrics.average_latency < 100:
                latency_score = 100.0
            elif self.metrics.average_latency < 500:
                latency_score = 80.0
            elif self.metrics.average_latency < 1000:
                latency_score = 60.0
            else:
                latency_score = 30.0
        
        # Consider uptime in performance score
        uptime_hours = self.metrics.connection_uptime / 3600
        uptime_score = min(100.0, uptime_hours * 10)  # 10 points per hour, max 100
        
        return (latency_score * 0.7 + uptime_score * 0.3)
    
    def _record_connection_event(self, event_type: str, state: ConnectionState, 
                                error_message: Optional[str] = None):
        """
        Record connection event for monitoring and analysis
        
        Args:
            event_type: Type of connection event
            state: Current connection state
            error_message: Optional error message
        """
        event = ConnectionEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            connection_state=state,
            error_message=error_message,
            details={
                'reconnect_attempts': self.reconnect_attempts,
                'broker_host': self.config.broker_host,
                'broker_port': self.config.broker_port
            }
        )
        
        # Keep only recent events (last 100)
        self.connection_events.append(event)
        if len(self.connection_events) > 100:
            self.connection_events = self.connection_events[-100:]
        
        # Call connection callback if set
        if self.connection_callback:
            try:
                self.connection_callback(event)
            except Exception as e:
                self.logger.error(f"Error in connection callback: {e}")
    
    def get_connection_events(self) -> List[ConnectionEvent]:
        """
        Get recent connection events
        
        Returns:
            List of recent connection events
        """
        return self.connection_events.copy()
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get current connection status and statistics (legacy compatibility)
        
        Returns:
            Dict containing connection status information
        """
        metrics = self.get_connection_metrics()
        
        return {
            'connected': self.connected,
            'connection_state': self.connection_state.value,
            'broker_host': self.config.broker_host,
            'broker_port': self.config.broker_port,
            'client_id': self.config.client_id,
            'subscribe_topic': self.config.subscribe_topic,
            'reconnect_attempts': self.reconnect_attempts,
            'max_reconnect_attempts': self.max_reconnect_attempts,
            'connection_uptime': metrics.connection_uptime,
            'message_success_rate': metrics.message_success_rate,
            'average_latency': metrics.average_latency,
            'quality_score': metrics.quality_score,
            'last_error': metrics.last_error
        }


# Maintain backward compatibility
class MQTTClient(MQTTClientEnhanced):
    """
    Backward compatibility wrapper for existing code
    """
    
    def connect(self) -> bool:
        """Legacy connect method"""
        return self.connect_with_retry()
    
    def disconnect(self):
        """Legacy disconnect method"""
        return self.disconnect_gracefully()
    
    def publish(self, topic: str, payload: str = "") -> bool:
        """Legacy publish method"""
        result = self.publish_with_confirmation(topic, payload)
        return result['success']