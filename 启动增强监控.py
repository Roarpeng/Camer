#!/usr/bin/env python3
"""
增强MQTT摄像头监控系统启动脚本

解决原系统只显示一个黑色视窗的问题，提供：
- 6个独立摄像头视窗
- 每个摄像头的独立参数配置
- 实时日志显示
"""

import sys
import os
import logging
import signal
import time
from mqtt_camera_monitoring.config import ConfigManager
from mqtt_camera_monitoring.main_controller import MainController


def setup_enhanced_logging(config):
    """设置增强日志配置"""
    # 创建日志格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 设置根日志级别
    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.logging.file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 设置特定模块的日志级别
    logging.getLogger('mqtt_camera_monitoring.visual_monitor').setLevel(logging.INFO)
    logging.getLogger('mqtt_camera_monitoring.camera_manager').setLevel(logging.INFO)


def signal_handler(signum, frame):
    """处理关闭信号"""
    logging.info(f"接收到信号 {signum}，正在关闭系统...")
    sys.exit(0)


def check_dependencies():
    """检查系统依赖"""
    try:
        import cv2
        import numpy as np
        import paho.mqtt.client as mqtt
        import tkinter as tk
        print("✓ 所有依赖库检查通过")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖库: {e}")
        print("请运行: pip install -r requirements.txt")
        return False


def create_default_config():
    """创建默认配置文件"""
    default_config = """# MQTT摄像头监控系统 - 增强配置

mqtt:
  broker_host: "192.168.10.80"
  broker_port: 1883
  client_id: "receiver"
  subscribe_topic: "changeState"
  publish_topic: "receiver/triggered"
  keepalive: 60
  reconnect_delay: 5
  max_reconnect_attempts: 10

cameras:
  count: 6
  resolution_width: 640
  resolution_height: 480
  fps: 30
  buffer_size: 1
  
  # 默认设置
  default_settings:
    brightness: 60
    exposure: 120
    contrast: 50
    saturation: 50
    auto_exposure: false
  
  # 每个摄像头的独立配置
  individual_settings:
    camera_0:
      brightness: 65
      exposure: 130
    camera_1:
      brightness: 55
      exposure: 110
    camera_2:
      brightness: 70
      exposure: 140
      auto_exposure: true

red_light_detection:
  lower_red_hsv: [0, 50, 50]
  upper_red_hsv: [10, 255, 255]
  lower_red_hsv_2: [170, 50, 50]
  upper_red_hsv_2: [180, 255, 255]
  min_contour_area: 100
  sensitivity: 0.8
  area_change_threshold: 0.1
  baseline_duration: 0.3

visual_monitor:
  window_width: 400
  window_height: 300
  show_detection_boxes: true
  box_color: [0, 255, 0]
  box_thickness: 2

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "mqtt_camera_monitoring.log"
"""
    
    with open("config.yaml", "w", encoding="utf-8") as f:
        f.write(default_config)
    
    print("✓ 已创建默认配置文件 config.yaml")


def main():
    """主启动函数"""
    print("=" * 60)
    print("🎥 MQTT摄像头监控系统 - 增强版")
    print("=" * 60)
    print()
    
    # 检查依赖
    if not check_dependencies():
        return 1
    
    # 检查配置文件
    if not os.path.exists("config.yaml"):
        print("⚠️  未找到配置文件，正在创建默认配置...")
        create_default_config()
    
    try:
        # 加载配置
        print("📋 正在加载配置...")
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # 设置日志
        setup_enhanced_logging(config)
        logger = logging.getLogger(__name__)
        
        # 设置信号处理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 显示配置信息
        print(f"🌐 MQTT服务器: {config.mqtt.broker_host}:{config.mqtt.broker_port}")
        print(f"📹 摄像头数量: {config.cameras.count}")
        print(f"⚙️  基线建立时间: {config.red_light_detection.baseline_duration}秒")
        print()
        
        logger.info("启动增强MQTT摄像头监控系统")
        logger.info(f"MQTT服务器: {config.mqtt.broker_host}:{config.mqtt.broker_port}")
        logger.info(f"摄像头数量: {config.cameras.count}")
        
        # 显示启动信息
        print("🚀 正在启动系统组件...")
        print("   - MQTT客户端连接")
        print("   - 6个USB摄像头初始化")
        print("   - 6个独立视窗创建")
        print("   - 控制面板启动")
        print("   - 实时日志系统")
        print()
        
        # 初始化并运行主控制器
        controller = MainController(config)
        
        print("✅ 系统启动完成！")
        print()
        print("💡 使用说明:")
        print("   - 6个摄像头视窗将显示实时画面")
        print("   - 控制面板可调整每个摄像头参数")
        print("   - 日志面板显示系统运行状态")
        print("   - 按 Ctrl+C 安全退出系统")
        print()
        
        # 运行系统
        controller.run()
        
    except FileNotFoundError as e:
        print(f"❌ 配置文件错误: {e}")
        return 1
    except Exception as e:
        print(f"❌ 系统启动失败: {e}")
        logging.error(f"系统启动失败: {e}")
        return 1
    
    finally:
        print("\n🔄 正在关闭系统...")
        print("✅ 系统已安全关闭")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)