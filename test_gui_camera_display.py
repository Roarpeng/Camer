#!/usr/bin/env python3
"""
测试GUI摄像头显示功能
验证摄像头下拉列表是否显示设备名称而不是简单数字
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from mqtt_camera_monitoring.gui_main_window import MainWindow
from usb_camera_detector import USBCameraDetector


def test_camera_display():
    """测试摄像头显示功能"""
    print("测试GUI摄像头显示功能...")
    
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = MainWindow()
    
    # 检查摄像头检测器
    print(f"摄像头检测器状态: {'可用' if window.camera_detector else '不可用'}")
    print(f"检测到的摄像头数量: {len(window.available_cameras)}")
    
    # 检查每个摄像头小部件的下拉列表内容
    for i, widget in enumerate(window.camera_widgets):
        combo = widget['id_combo']
        print(f"\n摄像头 {i} 下拉列表内容:")
        
        for j in range(combo.count()):
            item_text = combo.itemText(j)
            item_data = combo.itemData(j)
            print(f"  索引 {j}: 显示文本='{item_text}', 数据值={item_data}")
    
    # 检查可用摄像头信息
    print(f"\n检测到的摄像头详情:")
    for camera in window.available_cameras:
        print(f"  ID: {camera['id']}, 名称: {camera['name']}, 描述: {camera['description']}")
    
    print("\n测试完成")
    
    # 不显示窗口，直接退出
    app.quit()
    return True


if __name__ == "__main__":
    test_camera_display()