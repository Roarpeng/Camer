"""
Trigger Publisher Component

Handles publishing trigger messages to MQTT broker when red light
count decreases are detected.
"""

import logging
import time
from typing import Optional
import paho.mqtt.client as mqtt
from .config import MQTTConfig


class TriggerPublisher:
    """
    MQTT trigger message publisher for sending empty messages when red light changes are detected.
    
    Publishes empty messages to the "receiver/triggered" topic with delivery confirmation
    and retry logic for reliability.
    """
    
    def __init__(self, config: MQTTConfig):
        """
        Initialize trigger publisher with MQTT configuration
        
        Args:
            config: MQTT configuration settings
        """
        self.config = config
        self.client = mqtt.Client(client_id=f"{config.client_id}_publisher")
        self.logger = logging.getLogger(__name__)
        self.connected = False
        
        # Message delivery tracking
        self.pending_messages = {}  # mid -> timestamp
        self.max_retry_attempts = 3
        self.retry_delay = 1.0  # seconds
        self.delivery_timeout = 10.0  # seconds
        
        # Set up MQTT client callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
    
    def connect(self) -> bool:
        """
        Connect to MQTT broker for publishing
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting trigger publisher to MQTT broker at {self.config.broker_host}:{self.config.broker_port}")
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
                self.logger.info("Trigger publisher successfully connected to MQTT broker")
                return True
            else:
                self.logger.error("Trigger publisher failed to connect to MQTT broker within timeout")
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting trigger publisher to MQTT broker: {e}")
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
                self.logger.info("Trigger publisher disconnected from MQTT broker")
        except Exception as e:
            self.logger.error(f"Error disconnecting trigger publisher from MQTT broker: {e}")
    
    def publish_trigger(self, topic: Optional[str] = None) -> bool:
        """
        Publish empty trigger message to MQTT topic with delivery confirmation and retry logic
        
        Args:
            topic: Topic to publish to (uses config default if None)
            
        Returns:
            bool: True if message was successfully delivered, False otherwise
        """
        if not self.connected:
            self.logger.error("Cannot publish trigger: not connected to broker")
            return False
        
        topic = topic or self.config.publish_topic
        
        # Attempt to publish with retry logic
        for attempt in range(self.max_retry_attempts):
            try:
                self.logger.info(f"Publishing trigger message to topic: {topic} (attempt {attempt + 1}/{self.max_retry_attempts})")
                
                # Publish empty message
                result = self.client.publish(topic, payload="")
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    # Track message for delivery confirmation
                    self.pending_messages[result.mid] = time.time()
                    
                    # Wait for delivery confirmation
                    if self._wait_for_delivery_confirmation(result.mid):
                        self.logger.info(f"Trigger message successfully delivered to topic: {topic}")
                        return True
                    else:
                        self.logger.warning(f"Trigger message delivery confirmation timeout for topic: {topic}")
                        # Continue to retry
                else:
                    self.logger.error(f"Failed to publish trigger message to topic {topic}: {mqtt.error_string(result.rc)}")
                
            except Exception as e:
                self.logger.error(f"Error publishing trigger message (attempt {attempt + 1}): {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retry_attempts - 1:
                self.logger.info(f"Retrying trigger message publication in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
        
        self.logger.error(f"Failed to deliver trigger message after {self.max_retry_attempts} attempts")
        return False
    
    def _wait_for_delivery_confirmation(self, message_id: int) -> bool:
        """
        Wait for delivery confirmation of a published message
        
        Args:
            message_id: Message ID to wait for confirmation
            
        Returns:
            bool: True if delivery confirmed within timeout, False otherwise
        """
        start_time = time.time()
        
        while (time.time() - start_time) < self.delivery_timeout:
            # Check if message has been confirmed (removed from pending)
            if message_id not in self.pending_messages:
                return True
            
            time.sleep(0.1)  # Small delay to avoid busy waiting
        
        # Timeout reached, remove from pending messages
        if message_id in self.pending_messages:
            del self.pending_messages[message_id]
        
        return False
    
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
            self.logger.info(f"Trigger publisher connected to MQTT broker with client ID: {client._client_id}")
        else:
            self.connected = False
            self.logger.error(f"Trigger publisher failed to connect to MQTT broker. Result code: {rc}")
    
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
            self.logger.warning(f"Trigger publisher unexpected disconnection from MQTT broker. Result code: {rc}")
        else:
            self.logger.info("Trigger publisher cleanly disconnected from MQTT broker")
    
    def _on_publish(self, client, userdata, mid):
        """
        Callback for published message confirmation
        
        Args:
            client: MQTT client instance
            userdata: User data
            mid: Message ID
        """
        # Remove message from pending list to indicate successful delivery
        if mid in self.pending_messages:
            delivery_time = time.time() - self.pending_messages[mid]
            del self.pending_messages[mid]
            self.logger.debug(f"Trigger message delivery confirmed. Message ID: {mid}, Delivery time: {delivery_time:.3f}s")
    
    def get_status(self) -> dict:
        """
        Get current status of the trigger publisher
        
        Returns:
            dict: Status information including connection state and pending messages
        """
        return {
            'connected': self.connected,
            'broker_host': self.config.broker_host,
            'broker_port': self.config.broker_port,
            'client_id': f"{self.config.client_id}_publisher",
            'publish_topic': self.config.publish_topic,
            'pending_messages': len(self.pending_messages),
            'max_retry_attempts': self.max_retry_attempts,
            'retry_delay': self.retry_delay,
            'delivery_timeout': self.delivery_timeout
        }