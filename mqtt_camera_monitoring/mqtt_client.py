"""
MQTT Client Component

Handles all MQTT communication including connection, subscription,
message parsing, and publishing.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, Callable, List
import paho.mqtt.client as mqtt
from .config import MQTTConfig


class MQTTClient:
    """
    MQTT client for handling broker communication, message parsing, and publishing.
    
    Manages connection to MQTT broker, subscribes to state change messages,
    parses JSON payloads, and publishes trigger messages.
    """
    
    def __init__(self, config: MQTTConfig):
        """
        Initialize MQTT client with configuration
        
        Args:
            config: MQTT configuration settings
        """
        self.config = config
        self.client = mqtt.Client(client_id=config.client_id)
        self.logger = logging.getLogger(__name__)
        self.connected = False
        self.last_message_content = None
        self.message_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        
        # Set up MQTT client callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
        
        # Connection retry settings
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = config.max_reconnect_attempts
        self.reconnect_delay = config.reconnect_delay
    
    def connect(self) -> bool:
        """
        Connect to MQTT broker with error handling and logging
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to MQTT broker at {self.config.broker_host}:{self.config.broker_port}")
            self.client.connect(
                self.config.broker_host,
                self.config.broker_port,
                self.config.keepalive
            )
            
            # Start the network loop in a separate thread
            self.client.loop_start()
            
            # Wait for connection to be established
            timeout = 10  # seconds
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.connected:
                self.logger.info("Successfully connected to MQTT broker")
                self.reconnect_attempts = 0
                return True
            else:
                self.logger.error("Failed to connect to MQTT broker within timeout")
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        """
        Disconnect from MQTT broker and clean up resources
        """
        try:
            if self.connected:
                self.client.loop_stop()
                self.client.disconnect()
                self.connected = False
                self.logger.info("Disconnected from MQTT broker")
        except Exception as e:
            self.logger.error(f"Error disconnecting from MQTT broker: {e}")
    
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
    
    def publish(self, topic: str, payload: str = "") -> bool:
        """
        Publish message to MQTT topic
        
        Args:
            topic: Topic to publish to
            payload: Message payload (empty string for trigger messages)
            
        Returns:
            bool: True if publish successful, False otherwise
        """
        if not self.connected:
            self.logger.error("Cannot publish: not connected to broker")
            return False
        
        try:
            result = self.client.publish(topic, payload)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Successfully published to topic: {topic}")
                return True
            else:
                self.logger.error(f"Failed to publish to topic {topic}: {mqtt.error_string(result.rc)}")
                return False
        except Exception as e:
            self.logger.error(f"Error publishing to topic {topic}: {e}")
            return False
    
    def set_message_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Set callback function for processing received messages
        
        Args:
            callback: Function to call when message is received
        """
        self.message_callback = callback
    
    def _on_connect(self, client, userdata, flags, rc):
        """
        Callback for MQTT connection events
        
        Args:
            client: MQTT client instance
            userdata: User data
            flags: Connection flags
            rc: Connection result code
        """
        if rc == 0:
            self.connected = True
            self.logger.info(f"Connected to MQTT broker with client ID: {self.config.client_id}")
            # Automatically subscribe to the configured topic
            self.subscribe()
        else:
            self.connected = False
            self.logger.error(f"Failed to connect to MQTT broker. Result code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """
        Callback for MQTT disconnection events
        
        Args:
            client: MQTT client instance
            userdata: User data
            rc: Disconnection result code
        """
        self.connected = False
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection from MQTT broker. Result code: {rc}")
            self._attempt_reconnect()
        else:
            self.logger.info("Cleanly disconnected from MQTT broker")
    
    def _on_message(self, client, userdata, msg):
        """
        Callback for received MQTT messages
        
        Args:
            client: MQTT client instance
            userdata: User data
            msg: Received message
        """
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
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
                    'timestamp': time.time()
                }
                
                # Call the message callback if set
                if self.message_callback:
                    self.message_callback(message_data)
                
        except Exception as e:
            self.logger.error(f"Error processing received message: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """
        Callback for published message confirmation
        
        Args:
            client: MQTT client instance
            userdata: User data
            mid: Message ID
        """
        self.logger.debug(f"Message published successfully. Message ID: {mid}")
    
    def _attempt_reconnect(self):
        """
        Attempt to reconnect to MQTT broker with exponential backoff
        """
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error(f"Maximum reconnection attempts ({self.max_reconnect_attempts}) reached")
            return
        
        self.reconnect_attempts += 1
        delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))  # Exponential backoff
        
        self.logger.info(f"Attempting to reconnect in {delay} seconds (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
        time.sleep(delay)
        
        if self.connect():
            self.logger.info("Successfully reconnected to MQTT broker")
        else:
            self.logger.error("Reconnection attempt failed")
            self._attempt_reconnect()  # Try again
    
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
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get current connection status and statistics
        
        Returns:
            Dict containing connection status information
        """
        return {
            'connected': self.connected,
            'broker_host': self.config.broker_host,
            'broker_port': self.config.broker_port,
            'client_id': self.config.client_id,
            'subscribe_topic': self.config.subscribe_topic,
            'reconnect_attempts': self.reconnect_attempts,
            'max_reconnect_attempts': self.max_reconnect_attempts
        }