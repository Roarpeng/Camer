#!/usr/bin/env python3
"""
USB摄像头连接指南和实时检测工具

帮助用户连接和配置外接USB摄像头
"""

import cv2
import time
import subprocess
import os

def check_usb_devices():
    """检查USB设备连接情况"""
    print("🔍 检查USB设备连接情况...")
    
    try:
        # 使用lsusb命令查看USB设备
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            usb_cameras = []
            
            for line in lines:
                # 查找可能的摄像头设备
                if any(keyword in line.lower() for keyword in ['camera', 'webcam', 'video', 'uvc']):
                    usb_cameras.append(line.strip())
            
            print(f"📱 检测到的USB摄像头设备:")
            if usb_cameras:
                for i, camera in enumerate(usb_cameras):
                    print(f"   {i+1}. {camera}")
            else:
                print("   未检测到USB摄像头设备")
            
            return len(usb_cameras)
        
    except FileNotFoundError:
        print("⚠️  lsusb命令不可用")
    
    return 0

def check_video_devices():
    """检查/dev/video设备"""
    print("\n🎥 检查视频设备文件...")
    
    video_devices = []
    for i in range(10):
        device_path = f"/dev/video{i}"
        if os.path.exists(device_path):
            video_devices.append(device_path)
            print(f"✅ 找到设备: {device_path}")
    
    if not video_devices:
        print("❌ 未找到/dev/video设备")
    
    return video_devices

def real_time_camera_detection():
    """实时检测摄像头连接"""
    print("\n🔄 实时摄像头检测模式")
    print("=" * 40)
    print("请按以下步骤操作:")
    print("1. 逐个连接USB摄像头到计算机")
    print("2. 观察检测结果的变化")
    print("3. 按 Ctrl+C 退出检测")
    print()
    
    last_camera_count = 0
    detection_count = 0
    
    try:
        while True:
            detection_count += 1
            print(f"🔍 第{detection_count}次检测 ({time.strftime('%H:%M:%S')})")
            
            # 检测可用摄像头
            available_cameras = []
            camera_info = []
            
            for i in range(10):
                try:
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            height, width = frame.shape[:2]
                            available_cameras.append(i)
                            
                            # 判断是否为USB摄像头（简单启发式）
                            is_usb = i > 0  # 假设摄像头0是内置的
                            camera_type = "USB" if is_usb else "内置"
                            
                            camera_info.append({
                                'id': i,
                                'type': camera_type,
                                'resolution': f"{width}x{height}"
                            })
                        cap.release()
                except:
                    pass
            
            # 显示检测结果
            current_camera_count = len(available_cameras)
            
            if current_camera_count != last_camera_count:
                print(f"📊 摄像头数量变化: {last_camera_count} -> {current_camera_count}")
                last_camera_count = current_camera_count
            
            print(f"   总摄像头: {current_camera_count} 个")
            
            usb_cameras = [cam for cam in camera_info if cam['type'] == 'USB']
            builtin_cameras = [cam for cam in camera_info if cam['type'] == '内置']
            
            print(f"   内置摄像头: {len(builtin_cameras)} 个")
            for cam in builtin_cameras:
                print(f"     - 摄像头 {cam['id']}: {cam['resolution']}")
            
            print(f"   USB摄像头: {len(usb_cameras)} 个")
            for cam in usb_cameras:
                print(f"     - 摄像头 {cam['id']}: {cam['resolution']}")
            
            if len(usb_cameras) >= 6:
                print("🎉 检测到足够的USB摄像头！")
                break
            elif len(usb_cameras) > 0:
                print(f"⚠️  还需要连接 {6 - len(usb_cameras)} 个USB摄像头")
            else:
                print("❌ 未检测到USB摄像头，请检查连接")
            
            print("-" * 40)
            time.sleep(3)  # 每3秒检测一次
            
    except KeyboardInterrupt:
        print("\n⚠️ 用户停止检测")
        return available_cameras, camera_info

def test_specific_cameras(camera_ids):
    """测试指定的摄像头"""
    if not camera_ids:
        print("❌ 没有摄像头可测试")
        return
    
    print(f"\n🧪 测试摄像头: {camera_ids}")
    
    windows = []
    caps = []
    
    try:
        for i, camera_id in enumerate(camera_ids):
            window_name = f"摄像头 {camera_id}"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 320, 240)
            
            # 排列窗口
            col = i % 3
            row = i // 3
            x = col * 330
            y = row * 270
            cv2.moveWindow(window_name, x, y)
            
            windows.append(window_name)
            
            # 打开摄像头
            cap = cv2.VideoCapture(camera_id)
            caps.append((cap, camera_id))
            
            if cap.isOpened():
                print(f"✅ 摄像头 {camera_id}: 已打开")
            else:
                print(f"❌ 摄像头 {camera_id}: 打开失败")
        
        print("🎯 测试说明:")
        print("- 观察每个摄像头的画面")
        print("- 按 'q' 键退出测试")
        
        while True:
            for i, (cap, camera_id) in enumerate(caps):
                window_name = windows[i]
                
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        frame = cv2.resize(frame, (320, 240))
                        cv2.putText(frame, f"Camera {camera_id}", (10, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.imshow(window_name, frame)
                    else:
                        # 显示错误画面
                        error_frame = create_error_frame(camera_id)
                        cv2.imshow(window_name, error_frame)
                else:
                    error_frame = create_error_frame(camera_id)
                    cv2.imshow(window_name, error_frame)
            
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
        
        # 清理
        for cap, _ in caps:
            if cap:
                cap.release()
        cv2.destroyAllWindows()
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def create_error_frame(camera_id):
    """创建错误显示画面"""
    import numpy as np
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[:] = (0, 0, 50)
    
    cv2.putText(frame, f"Camera {camera_id}", (80, 100), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, "ERROR", (120, 140), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    return frame

def show_connection_guide():
    """显示USB摄像头连接指南"""
    print("📋 USB摄像头连接指南")
    print("=" * 50)
    print()
    print("🔌 硬件连接:")
    print("1. 准备6个USB摄像头")
    print("2. 逐个连接到计算机的USB端口")
    print("3. 如果USB端口不够，使用USB集线器")
    print("4. 确保USB集线器有足够的供电能力")
    print()
    print("💻 系统要求:")
    print("1. Linux系统支持UVC (USB Video Class)")
    print("2. 足够的USB带宽（建议使用USB 3.0）")
    print("3. 足够的系统内存和CPU性能")
    print()
    print("🔧 故障排除:")
    print("1. 如果摄像头无法识别，尝试重新插拔")
    print("2. 检查USB端口是否工作正常")
    print("3. 尝试连接到不同的USB端口")
    print("4. 确认摄像头驱动已正确安装")
    print()
    print("📊 预期结果:")
    print("- 笔记本内置摄像头: 摄像头0")
    print("- 外接USB摄像头: 摄像头1, 2, 3, 4, 5, 6")
    print("- 项目将使用: 摄像头1-6 (跳过摄像头0)")
    print()

def main():
    """主函数"""
    print("🎥 USB摄像头连接指南和检测工具")
    print("=" * 60)
    
    # 显示连接指南
    show_connection_guide()
    
    # 检查USB设备
    usb_camera_count = check_usb_devices()
    
    # 检查视频设备文件
    video_devices = check_video_devices()
    
    print(f"\n📋 当前状态:")
    print(f"   - USB摄像头设备: {usb_camera_count} 个")
    print(f"   - 视频设备文件: {len(video_devices)} 个")
    
    # 选择操作
    print(f"\n🎯 请选择操作:")
    print("1. 实时检测摄像头连接")
    print("2. 测试当前可用摄像头")
    print("3. 退出")
    
    try:
        choice = input("请选择 (1-3): ").strip()
        
        if choice == '1':
            available_cameras, camera_info = real_time_camera_detection()
            
            # 询问是否测试
            if available_cameras:
                test_choice = input(f"\n是否测试检测到的{len(available_cameras)}个摄像头？(y/n): ").strip().lower()
                if test_choice == 'y':
                    test_specific_cameras(available_cameras)
        
        elif choice == '2':
            # 快速检测当前摄像头
            available_cameras = []
            for i in range(10):
                try:
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            available_cameras.append(i)
                        cap.release()
                except:
                    pass
            
            if available_cameras:
                print(f"检测到摄像头: {available_cameras}")
                test_specific_cameras(available_cameras)
            else:
                print("未检测到可用摄像头")
        
        elif choice == '3':
            print("退出程序")
        
        else:
            print("无效选择")
    
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")

if __name__ == "__main__":
    main()