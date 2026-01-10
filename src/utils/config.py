import json
import os
import logging

logger = logging.getLogger("CamerApp")

class ConfigManager:
    """配置管理器，负责保存和加载应用配置"""
    
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = {
            "mqtt": {
                "broker": "localhost",
                "client_id": "camer",
                "subscribe_topics": ["changeState", "receiver"],
                "publish_topic": "receiver",
                "auto_connect": True,
                "baseline_delay": 1000
            },
            "cameras": [
                {
                    "active": False,
                    "mask": "",
                    "threshold": 50,
                    "min_area": 500,
                    "scan_interval": 300
                },
                {
                    "active": False,
                    "mask": "",
                    "threshold": 50,
                    "min_area": 500,
                    "scan_interval": 300
                },
                {
                    "active": False,
                    "mask": "",
                    "threshold": 50,
                    "min_area": 500,
                    "scan_interval": 300
                },
                {
                    "active": False,
                    "mask": "",
                    "threshold": 50,
                    "min_area": 500,
                    "scan_interval": 300
                },
                {
                    "active": False,
                    "mask": "",
                    "threshold": 50,
                    "min_area": 500,
                    "scan_interval": 300
                },
                {
                    "active": False,
                    "mask": "",
                    "threshold": 50,
                    "min_area": 500,
                    "scan_interval": 300
                },
                {
                    "active": False,
                    "mask": "",
                    "threshold": 50,
                    "min_area": 500,
                    "scan_interval": 300
                },
                {
                    "active": False,
                    "mask": "",
                    "threshold": 50,
                    "min_area": 500,
                    "scan_interval": 300
                }
            ]
        }
        self.load_config()
    
    def load_config(self):
        """从本地文件加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并配置，确保所有必需字段都存在
                    self._merge_config(loaded_config)
                    logger.info(f"成功加载配置文件: {self.config_file}")
            else:
                logger.info(f"配置文件不存在，使用默认配置: {self.config_file}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
    
    def save_config(self):
        """保存配置到本地文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            logger.info(f"成功保存配置文件: {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def _merge_config(self, loaded_config):
        """合并加载的配置到当前配置"""
        if "mqtt" in loaded_config:
            self.config["mqtt"].update(loaded_config["mqtt"])
        
        if "cameras" in loaded_config:
            for i, cam_config in enumerate(loaded_config["cameras"]):
                if i < len(self.config["cameras"]):
                    self.config["cameras"][i].update(cam_config)
    
    def get_mqtt_broker(self):
        """获取 MQTT broker 地址"""
        return self.config["mqtt"]["broker"]
    
    def set_mqtt_broker(self, broker):
        """设置 MQTT broker 地址"""
        self.config["mqtt"]["broker"] = broker
        self.save_config()
    
    def get_client_id(self):
        """获取 MQTT client ID"""
        return self.config["mqtt"]["client_id"]
    
    def set_client_id(self, client_id):
        """设置 MQTT client ID"""
        self.config["mqtt"]["client_id"] = client_id
        self.save_config()
    
    def get_subscribe_topics(self):
        """获取订阅主题列表"""
        return self.config["mqtt"]["subscribe_topics"]
    
    def set_subscribe_topics(self, topics):
        """设置订阅主题列表"""
        self.config["mqtt"]["subscribe_topics"] = topics
        self.save_config()
    
    def get_publish_topic(self):
        """获取发布主题"""
        return self.config["mqtt"]["publish_topic"]
    
    def set_publish_topic(self, topic):
        """设置发布主题"""
        self.config["mqtt"]["publish_topic"] = topic
        self.save_config()
    
    def get_auto_connect(self):
        """获取是否自动连接broker"""
        return self.config["mqtt"].get("auto_connect", True)
    
    def set_auto_connect(self, auto_connect):
        """设置是否自动连接broker"""
        self.config["mqtt"]["auto_connect"] = auto_connect
        self.save_config()
    
    def get_camera_config(self, camera_id):
        """获取指定摄像头的配置"""
        if 0 <= camera_id < len(self.config["cameras"]):
            return self.config["cameras"][camera_id]
        return None
    
    def update_camera_config(self, camera_id, **kwargs):
        """更新指定摄像头的配置"""
        if 0 <= camera_id < len(self.config["cameras"]):
            self.config["cameras"][camera_id].update(kwargs)
            self.save_config()
    
    def set_camera_active(self, camera_id, active):
        """设置摄像头激活状态"""
        self.update_camera_config(camera_id, active=active)
    
    def set_camera_mask(self, camera_id, mask):
        """设置摄像头掩码"""
        self.update_camera_config(camera_id, mask=mask)
    
    def set_camera_threshold(self, camera_id, threshold):
        """设置摄像头阈值"""
        self.update_camera_config(camera_id, threshold=threshold)
    
    def set_camera_min_area(self, camera_id, min_area):
        """设置摄像头最小面积"""
        self.update_camera_config(camera_id, min_area=min_area)
    
    def set_camera_scan_interval(self, camera_id, scan_interval):
        """设置摄像头扫描间隔（毫秒）"""
        self.update_camera_config(camera_id, scan_interval=scan_interval)
    
    def get_baseline_delay(self):
        """获取基线建立延时（毫秒）"""
        return self.config["mqtt"].get("baseline_delay", 1000)
    
    def set_baseline_delay(self, delay):
        """设置基线建立延时（毫秒）"""
        self.config["mqtt"]["baseline_delay"] = delay
        self.save_config()