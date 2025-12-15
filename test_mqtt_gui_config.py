#!/usr/bin/env python3
"""
测试MQTT GUI配置功能
验证GUI中的MQTT配置是否能正确保存和加载
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from mqtt_camera_monitoring.gui_main_window import MainWindow


def test_mqtt_gui_config():
    """测试MQTT GUI配置功能"""
    print("=== MQTT GUI配置测试 ===")
    
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = MainWindow()
    
    # 测试默认MQTT配置
    print("\n1. 测试默认MQTT配置:")
    mqtt_params = window.get_mqtt_parameters()
    for key, value in mqtt_params.items():
        print(f"   {key}: {value}")
    
    # 测试修改MQTT配置
    print("\n2. 测试修改MQTT配置:")
    test_config = {
        'broker_host': '192.168.1.100',
        'broker_port': 1884,
        'client_id': 'test_client',
        'subscribe_topic': 'test/changeState',
        'publish_topic': 'test/triggered'
    }
    
    window.apply_mqtt_parameters(test_config)
    print("   已应用测试配置")
    
    # 验证修改后的配置
    updated_params = window.get_mqtt_parameters()
    print("   修改后的配置:")
    for key, value in updated_params.items():
        print(f"   {key}: {value}")
    
    # 测试配置验证
    print("\n3. 测试配置验证:")
    window._validate_mqtt_parameters_realtime()
    print("   验证完成")
    
    # 测试配置保存
    print("\n4. 测试配置保存:")
    try:
        window.save_configuration_to_file()
        print("   配置保存成功")
    except Exception as e:
        print(f"   配置保存失败: {e}")
    
    # 测试配置加载
    print("\n5. 测试配置加载:")
    try:
        # 先清空配置
        window.apply_mqtt_parameters({
            'broker_host': '',
            'broker_port': 1883,
            'client_id': '',
            'subscribe_topic': '',
            'publish_topic': ''
        })
        
        # 重新加载配置
        window.load_configuration_from_file()
        
        # 检查加载的配置
        loaded_params = window.get_mqtt_parameters()
        print("   加载的配置:")
        for key, value in loaded_params.items():
            print(f"   {key}: {value}")
        
        print("   配置加载成功")
    except Exception as e:
        print(f"   配置加载失败: {e}")
    
    print("\n=== 测试完成 ===")
    
    # 不显示窗口，直接退出
    app.quit()
    return True


def test_system_wrapper_mqtt():
    """测试系统包装器的MQTT配置"""
    print("\n=== 系统包装器MQTT配置测试 ===")
    
    try:
        from mqtt_camera_monitoring.gui_system_wrapper import GuiSystemWrapper
        
        wrapper = GuiSystemWrapper()
        
        # 测试默认MQTT配置
        print("\n1. 默认MQTT配置:")
        default_config = wrapper.get_effective_mqtt_config()
        for key, value in default_config.items():
            print(f"   {key}: {value}")
        
        # 测试更新MQTT配置
        print("\n2. 更新MQTT配置:")
        test_config = {
            'broker_host': '192.168.2.200',
            'broker_port': 1885,
            'client_id': 'wrapper_test'
        }
        
        success = wrapper.update_mqtt_configuration(test_config)
        print(f"   更新结果: {'成功' if success else '失败'}")
        
        # 验证更新后的配置
        updated_config = wrapper.get_effective_mqtt_config()
        print("   更新后的配置:")
        for key, value in updated_config.items():
            print(f"   {key}: {value}")
        
        print("   系统包装器MQTT配置测试完成")
        
    except Exception as e:
        print(f"   系统包装器测试失败: {e}")


def main():
    """主测试函数"""
    print("MQTT GUI配置功能测试")
    print("=" * 50)
    
    test_mqtt_gui_config()
    test_system_wrapper_mqtt()
    
    print("\n" + "=" * 50)
    print("所有测试完成")


if __name__ == "__main__":
    main()