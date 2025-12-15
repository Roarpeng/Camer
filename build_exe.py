#!/usr/bin/env python3
"""
PyInstaller打包脚本
用于将MQTT摄像头监控系统打包为EXE文件
"""

import PyInstaller.__main__
import os
import shutil

def build_exe():
    """构建EXE文件"""
    
    # PyInstaller参数
    args = [
        'gui_main.py',                    # 主程序入口
        '--onefile',                      # 打包为单个EXE文件
        '--windowed',                     # Windows GUI应用（无控制台窗口）
        '--name=MQTT摄像头监控系统',        # EXE文件名
        '--icon=app_icon.ico',            # 应用图标（如果有）
        
        # 添加数据文件
        '--add-data=config.yaml;.',       # 配置文件
        '--add-data=fmask.png;.',         # 掩码文件
        '--add-data=mask.png;.',          # 备用掩码文件
        '--add-data=usb_camera_detector.py;.',  # USB检测工具
        '--add-data=path_utils.py;.',     # 路径工具
        
        # 添加整个模块目录
        '--add-data=mqtt_camera_monitoring;mqtt_camera_monitoring',
        
        # 隐藏导入（如果需要）
        '--hidden-import=PySide6',
        '--hidden-import=cv2',
        '--hidden-import=paho.mqtt.client',
        '--hidden-import=yaml',
        '--hidden-import=numpy',
        
        # 排除不需要的模块
        '--exclude-module=tkinter',
        '--exclude-module=matplotlib',
        
        # 输出目录
        '--distpath=dist',
        '--workpath=build',
        '--specpath=.',
        
        # 清理选项
        '--clean',
        '--noconfirm'
    ]
    
    print("开始打包EXE文件...")
    PyInstaller.__main__.run(args)
    
    # 复制额外文件到dist目录
    dist_dir = 'dist'
    if os.path.exists(dist_dir):
        print("复制额外文件...")
        
        # 复制使用说明
        extra_files = [
            'README_FOR_REMOTE_TESTING.md',
            'USAGE_AND_DEBUGGING_GUIDE.md',
            'camera_configuration_guide.md'
        ]
        
        for file in extra_files:
            if os.path.exists(file):
                shutil.copy2(file, dist_dir)
                print(f"已复制: {file}")
    
    print("打包完成！")
    print(f"EXE文件位置: {os.path.join(dist_dir, 'MQTT摄像头监控系统.exe')}")

if __name__ == "__main__":
    build_exe()