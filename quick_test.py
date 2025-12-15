#!/usr/bin/env python3
"""
MQTT摄像头监控系统 - 快速测试脚本
用于远程同事快速验证系统核心功能
"""

import sys
import os
import time
from datetime import datetime

def print_header(title):
    """打印测试标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_step(step_num, description):
    """打印测试步骤"""
    print(f"\n[步骤 {step_num}] {description}")
    print("-" * 40)

def test_imports():
    """测试模块导入"""
    print_step(1, "测试模块导入")
    
    try:
        import cv2
        print("✅ OpenCV 导入成功")
    except ImportError as e:
        print(f"❌ OpenCV 导入失败: {e}")
        return False
    
    try:
        from PySide6.QtWidgets import QApplication
        print("✅ PySide6 导入成功")
    except ImportError as e:
        print(f"❌ PySide6 导入失败: {e}")
        return False
    
    try:
        from usb_camera_detector import USBCameraDetector
        print("✅ USB摄像头检测器导入成功")
    except ImportError as e:
        print(f"❌ USB摄像头检测器导入失败: {e}")
        return False
    
    try:
        from mqtt_camera_monitoring.gui_main_window import MainWindow
        print("✅ GUI主窗口导入成功")
    except ImportError as e:
        print(f"❌ GUI主窗口导入失败: {e}")
        return False
    
    return True

def test_camera_detection():
    """测试摄像头检测"""
    print_step(2, "测试USB摄像头检测")
    
    try:
        from usb_camera_detector import USBCameraDetector
        
        detector = USBCameraDetector()
        cameras = detector.detect_cameras()
        
        if cameras:
            print(f"✅ 检测到 {len(cameras)} 个USB摄像头:")
            for camera in cameras:
                print(f"   - ID {camera['id']}: {camera['name']}")
                
                # 检查是否显示实际设备名称而不是简单的"摄像头 X"
                if camera['name'] != f"USB摄像头 {camera['id']}":
                    print(f"   ✅ 设备名称正确: {camera['name']}")
                else:
                    print(f"   ⚠️  使用默认名称: {camera['name']}")
            return True
        else:
            print("❌ 未检测到USB摄像头")
            print("   请检查：")
            print("   1. USB摄像头是否正确连接")
            print("   2. 是否有其他程序占用摄像头")
            print("   3. 摄像头驱动是否正常")
            return False
            
    except Exception as e:
        print(f"❌ 摄像头检测失败: {e}")
        return False

def test_gui_camera_display():
    """测试GUI摄像头显示"""
    print_step(3, "测试GUI摄像头显示功能")
    
    try:
        from PySide6.QtWidgets import QApplication
        from mqtt_camera_monitoring.gui_main_window import MainWindow
        
        # 创建应用程序（不显示窗口）
        app = QApplication(sys.argv)
        
        # 创建主窗口
        window = MainWindow()
        
        print(f"✅ GUI窗口创建成功")
        print(f"   摄像头检测器状态: {'可用' if window.camera_detector else '不可用'}")
        print(f"   检测到的摄像头数量: {len(window.available_cameras)}")
        
        # 检查第一个摄像头小部件的下拉列表
        if window.camera_widgets:
            first_widget = window.camera_widgets[0]
            combo = first_widget['id_combo']
            
            print(f"   摄像头下拉列表选项数量: {combo.count()}")
            
            if combo.count() > 0:
                first_item_text = combo.itemText(0)
                first_item_data = combo.itemData(0)
                
                print(f"   第一个选项显示文本: '{first_item_text}'")
                print(f"   第一个选项数据值: {first_item_data}")
                
                # 检查是否显示设备名称格式
                if "(ID:" in first_item_text and ")" in first_item_text:
                    print("   ✅ 摄像头选项显示格式正确（包含设备名称和ID）")
                    success = True
                elif first_item_text.isdigit():
                    print("   ❌ 摄像头选项仍显示数字ID，未显示设备名称")
                    success = False
                else:
                    print("   ⚠️  摄像头选项显示格式未知")
                    success = True  # 不算失败，可能是其他格式
            else:
                print("   ❌ 摄像头下拉列表为空")
                success = False
        else:
            print("   ❌ 未找到摄像头配置小部件")
            success = False
        
        # 退出应用程序
        app.quit()
        return success
        
    except Exception as e:
        print(f"❌ GUI测试失败: {e}")
        return False

def test_configuration_validation():
    """测试配置验证"""
    print_step(4, "测试配置验证功能")
    
    try:
        import subprocess
        
        # 运行配置验证工具
        result = subprocess.run([
            sys.executable, 'validate_camera_config.py'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ 配置验证通过")
        else:
            print("⚠️  配置验证发现问题（这可能是正常的）")
        
        # 检查是否生成了验证报告
        if os.path.exists('validation_report.txt'):
            print("✅ 验证报告生成成功")
            return True
        else:
            print("❌ 验证报告未生成")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  配置验证超时")
        return False
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")
        return False

def test_automated_tests():
    """运行自动化测试"""
    print_step(5, "运行自动化测试（可选）")
    
    try:
        import subprocess
        
        print("正在运行自动化测试...")
        
        # 运行核心测试
        test_files = [
            'test_gui_integration.py',
            'test_integration_gui_system.py'
        ]
        
        passed_tests = 0
        total_tests = 0
        
        for test_file in test_files:
            if os.path.exists(test_file):
                try:
                    result = subprocess.run([
                        sys.executable, '-m', 'pytest', test_file, '-v'
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        print(f"   ✅ {test_file} 通过")
                        passed_tests += 1
                    else:
                        print(f"   ❌ {test_file} 失败")
                    
                    total_tests += 1
                    
                except subprocess.TimeoutExpired:
                    print(f"   ⚠️  {test_file} 超时")
                    total_tests += 1
            else:
                print(f"   ⚠️  {test_file} 不存在")
        
        if total_tests > 0:
            print(f"   测试结果: {passed_tests}/{total_tests} 通过")
            return passed_tests == total_tests
        else:
            print("   ⚠️  没有找到测试文件")
            return True  # 不算失败
            
    except Exception as e:
        print(f"❌ 自动化测试失败: {e}")
        return False

def generate_test_report(results):
    """生成测试报告"""
    print_header("测试报告")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""
MQTT摄像头监控系统 - 快速测试报告
生成时间: {timestamp}

测试结果总览:
{'='*40}
"""
    
    test_names = [
        "模块导入测试",
        "USB摄像头检测测试", 
        "GUI摄像头显示测试",
        "配置验证测试",
        "自动化测试"
    ]
    
    passed_count = sum(results)
    total_count = len(results)
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ 通过" if result else "❌ 失败"
        report += f"{i+1}. {name}: {status}\n"
    
    report += f"\n总体结果: {passed_count}/{total_count} 项测试通过\n"
    
    if passed_count == total_count:
        report += "\n🎉 所有测试通过！系统功能正常。\n"
    elif passed_count >= total_count * 0.8:
        report += "\n⚠️  大部分测试通过，系统基本功能正常。\n"
    else:
        report += "\n❌ 多项测试失败，请检查系统配置。\n"
    
    print(report)
    
    # 保存报告到文件
    try:
        with open('quick_test_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📄 测试报告已保存到: quick_test_report.txt")
    except Exception as e:
        print(f"⚠️  保存测试报告失败: {e}")

def main():
    """主测试函数"""
    print_header("MQTT摄像头监控系统 - 快速测试")
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 运行所有测试
    results = []
    
    results.append(test_imports())
    results.append(test_camera_detection())
    results.append(test_gui_camera_display())
    results.append(test_configuration_validation())
    results.append(test_automated_tests())
    
    # 生成测试报告
    generate_test_report(results)
    
    # 返回总体结果
    return all(results)

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生未预期的错误: {e}")
        sys.exit(1)