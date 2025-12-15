#!/usr/bin/env python3
"""
测试配置文件路径解析
验证PyInstaller打包后配置文件是否能正确读取
"""

import os
import sys
import yaml
from path_utils import get_config_path, ensure_config_in_exe_dir, print_path_info


def test_config_loading():
    """测试配置文件加载"""
    print("=== 配置文件路径测试 ===")
    
    # 打印路径信息
    print_path_info()
    
    # 测试配置文件路径解析
    print("\n=== 配置文件测试 ===")
    config_path = get_config_path("config.yaml")
    print(f"解析的配置文件路径: {config_path}")
    print(f"配置文件存在: {os.path.exists(config_path)}")
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            print("✅ 配置文件读取成功")
            
            # 检查MQTT配置
            if 'mqtt' in config:
                mqtt_config = config['mqtt']
                broker_host = mqtt_config.get('broker_host', 'N/A')
                broker_port = mqtt_config.get('broker_port', 'N/A')
                client_id = mqtt_config.get('client_id', 'N/A')
                
                print(f"✅ MQTT Broker: {broker_host}:{broker_port}")
                print(f"✅ Client ID: {client_id}")
            else:
                print("❌ 配置文件中缺少MQTT配置")
                
        except Exception as e:
            print(f"❌ 配置文件读取失败: {e}")
    else:
        print("❌ 配置文件不存在")
        
        # 尝试确保配置文件存在
        print("\n尝试创建配置文件...")
        try:
            ensured_path = ensure_config_in_exe_dir("config.yaml")
            print(f"确保配置文件路径: {ensured_path}")
            print(f"配置文件现在存在: {os.path.exists(ensured_path)}")
        except Exception as e:
            print(f"创建配置文件失败: {e}")


def test_mqtt_config_access():
    """测试MQTT配置访问"""
    print("\n=== MQTT配置访问测试 ===")
    
    try:
        from mqtt_camera_monitoring.config import ConfigManager
        
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        mqtt_config = config.mqtt
        print(f"✅ MQTT Broker Host: {mqtt_config.broker_host}")
        print(f"✅ MQTT Broker Port: {mqtt_config.broker_port}")
        print(f"✅ MQTT Client ID: {mqtt_config.client_id}")
        
    except Exception as e:
        print(f"❌ MQTT配置访问失败: {e}")


def test_gui_config_manager():
    """测试GUI配置管理器"""
    print("\n=== GUI配置管理器测试 ===")
    
    try:
        from mqtt_camera_monitoring.gui_config_manager import GuiConfigManager
        
        config_manager = GuiConfigManager()
        gui_config = config_manager.load_gui_configuration()
        
        print(f"✅ GUI配置加载成功")
        print(f"✅ 摄像头配置数量: {len(gui_config.cameras)}")
        print(f"✅ 延迟时间: {gui_config.system_parameters.delay_time}")
        
    except Exception as e:
        print(f"❌ GUI配置管理器测试失败: {e}")


def main():
    """主测试函数"""
    print("配置文件路径解析测试")
    print("=" * 50)
    
    test_config_loading()
    test_mqtt_config_access()
    test_gui_config_manager()
    
    print("\n" + "=" * 50)
    print("测试完成")


if __name__ == "__main__":
    main()