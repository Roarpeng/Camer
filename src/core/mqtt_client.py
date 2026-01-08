
import paho.mqtt.client as mqtt
from PySide6.QtCore import QObject, Signal
import logging

logger = logging.getLogger("CamerApp")

class MqttWorker(QObject):
    reset_signal = Signal()
    status_changed = Signal(bool, str)
    
    def __init__(self, broker="localhost", port=1883, topics=["changeState", "receiver"], publish_topic="receiver"):
        super().__init__()
        self.broker = broker
        self.port = port
        self.topics = topics
        self.publish_topic = publish_topic
        self.client = mqtt.Client(client_id="camer")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self._connected = False
        
    def start(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            logger.info(f"MQTT Client connected to {self.broker}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            logger.info("Connected to MQTT Broker.")
            for topic in self.topics:
                client.subscribe(topic)
                logger.info(f"Subscribed to topic: {topic}")
            self.status_changed.emit(True, "已连接")
        else:
            self._connected = False
            logger.error(f"MQTT Connection failed with code {rc}")
            self.status_changed.emit(False, f"连接失败({rc})")

    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode()
            logger.info(f"Received MQTT message on {msg.topic}: {payload}")
            
            # Check if it's the changeState topic
            if msg.topic == "changeState":
                # Parse JSON format: {"state":[1,1,1,2,0,...,1,1,1]} (144 elements)
                import json
                try:
                    data = json.loads(payload)
                    if "state" in data and isinstance(data["state"], list):
                        # Check if the state array contains 2
                        if 2 in data["state"]:
                            logger.info("检测到 state 数组中包含 2，触发基线建立。")
                            self.reset_signal.emit()
                        else:
                            logger.debug(f"State 数组中未检测到 2: {data['state'][:10]}...")
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON 解析失败: {e}")
                    # Fallback: check if payload contains '2' as string
                    if "2" in payload:
                        logger.info("触发基线建立（字符串匹配）。")
                        self.reset_signal.emit()
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT Broker with code: {rc}")
        self._connected = False
        self.status_changed.emit(False, "已断开")

    def on_publish(self, client, userdata, mid):
        """发布成功的回调"""
        logger.info(f"消息发布成功，Message ID: {mid}")

    def reconnect(self, broker, port=1883, subscribe_topics=None, publish_topic=None):
        self.stop()
        self.broker = broker
        self.port = port
        if subscribe_topics is not None:
            self.topics = subscribe_topics
        if publish_topic is not None:
            self.publish_topic = publish_topic
        self.start()

    def publish(self, topic, payload=""):
        try:
            if not self._connected:
                logger.warning(f"MQTT 未连接，无法发布到 {topic}")
                return
            
            info = self.client.publish(topic, payload)
            if info.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"已发布到 {topic} (Message ID: {info.mid}): {payload}")
            elif info.rc == mqtt.MQTT_ERR_NO_CONN:
                logger.warning(f"发布到 {topic} 失败：没有连接")
            elif info.rc == mqtt.MQTT_ERR_QUEUE_SIZE:
                logger.warning(f"发布到 {topic} 失败：消息队列已满")
            else:
                logger.warning(f"发布到 {topic} 失败，返回码: {info.rc}")
        except Exception as e:
            logger.error(f"发布到 MQTT 失败: {e}")

    def stop(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except:
            pass
