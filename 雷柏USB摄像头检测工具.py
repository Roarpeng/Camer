#!/usr/bin/env python3
"""
雷柏USB摄像头检测和配置工具

专门针对雷柏(Rapoo)品牌USB摄像头的检测和配置
- 检测雷柏USB摄像头连接状态
- 处理Linux环境下的兼容性问题
- 配置摄像头参数和驱动
"""

import cv2
import numpy as np
import time
import subprocess
import re
import os

def check_rapoo_usb_devices():
    """检查雷柏USB设备连接情况"""
    print("🔍 检查雷柏USB摄像头连接情况...")
    
    rapoo_devices = []
    
    try:
        # 使用lsusb命令查看USB设备
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            
            for line in lines:
                # 查找雷柏设备
                if any(keyword in line.lower() for keyword in ['rapoo', '雷柏']):
                    rapoo_devices.append(line.strip())
                    print(f"✅ 发现雷柏设备: {line.strip()}")
                # 查找可能的摄像头设备（通用）
                elif any(keyword in line.lower() for keyword in ['camera', 'webcam', 'video', 'uvc']):
                    rapoo_devices.append(line.strip())
                    print(f"📷 发现摄像头设备: {line.strip()}")
            
            if not rapoo_devices:
                print("❌ 未检测到雷柏USB摄像头设备")
                print("请确认:")
                print("1. 雷柏USB摄像头已连接到计算机")
                print("2. USB端口工作正常")
                print("3. 摄像头电源指示灯是否亮起")
        
    except FileNotFoundError:
        print("⚠️  lsusb命令不可用，尝试其他方法检测")
    
    return rapoo_devices

def check_video_devices_detailed():
    """详细检查视频设备"""
    print("\n🎥 详细检查视频设备...")
    
    video_devices = []
    device_info = {}
    
    # 检查/dev/video设备
    for i in range(10):
        device_path = f"/dev/video{i}"
        if os.path.exists(device_path):
            video_devices.append(device_path)
            print(f"✅ 找到视频设备: {device_path}")
            
            # 尝试获取设备信息
            try:
                result = subprocess.run(['v4l2-ctl', '--device', device_path, '--info'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    device_info[i] = result.stdout
                    # 查找设备名称
                    for line in result.stdout.split('\n'):
                        if 'Card type' in line or 'Device name' in line:
                            print(f"   设备信息: {line.strip()}")
            except:
                print(f"   无法获取{device_path}的详细信息")
    
    return video_devices, device_info

def test_rapoo_camera_compatibility(camera_id):
    """测试雷柏摄像头兼容性"""
    print(f"\n🧪 测试摄像头 {camera_id} 兼容性...")
    
    try:
        # 尝试不同的后端
        backends = [
            (cv2.CAP_V4L2, "V4L2"),
            (cv2.CAP_GSTREAMER, "GStreamer"),
            (cv2.CAP_FFMPEG, "FFmpeg"),
            (cv2.CAP_ANY, "Auto")
        ]
        
        for backend, name in backends:
            try:
                print(f"   尝试 {name} 后端...")
                cap = cv2.VideoCapture(camera_id, backend)
                
                if cap.isOpened():
                    # 尝试读取画面
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        height, width = frame.shape[:2]
                        print(f"   ✅ {name} 后端成功: {width}x{height}")
                        
                        # 测试参数设置
                        test_camera_parameters(cap, camera_id, name)
                        
                        cap.release()
                        return True, name, (width, height)
                    else:
                        print(f"   ❌ {name} 后端无法读取画面")
                else:
                    print(f"   ❌ {name} 后端无法打开摄像头")
                
                cap.release()
                
            except Exception as e:
                print(f"   ❌ {name} 后端异常: {e}")
        
        return False, None, None
        
    except Exception as e:
        print(f"   ❌ 兼容性测试失败: {e}")
        return False, None, None

def test_camera_parameters(cap, camera_id, backend_name):
    """测试摄像头参数设置"""
    print(f"     测试参数设置...")
    
    # 测试常用参数
    params = [
        (cv2.CAP_PROP_BRIGHTNESS, "亮度"),
        (cv2.CAP_PROP_CONTRAST, "对比度"),
        (cv2.CAP_PROP_SATURATION, "饱和度"),
        (cv2.CAP_PROP_EXPOSURE, "曝光"),
        (cv2.CAP_PROP_AUTO_EXPOSURE, "自动曝光")
    ]
    
    supported_params = []
    
    for prop, name in params:
        try:
            # 获取当前值
            current_value = cap.get(prop)
            if current_value != -1:
                print(f"     ✅ {name}: {current_value}")
                supported_params.append((prop, name, current_value))
            else:
                print(f"     ❌ {name}: 不支持")
        except:
            print(f"     ❌ {name}: 读取失败")
    
    return supported_params

def create_rapoo_camera_test(camera_ids):
    """创建雷柏摄像头测试窗口"""
    if not camera_ids:
        print("❌ 没有摄像头可测试")
        return
    
    print(f"\n🎥 测试雷柏摄像头显示: {camera_ids}")
    
    windows = []
    caps = []
    
    try:
        for i, camera_id in enumerate(camera_ids):
            window_name = f"雷柏摄像头 {camera_id}"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 400, 300)
            
            # 排列窗口
            col = i % 3
            row = i // 3
            x = col * 410
            y = row * 350
            cv2.moveWindow(window_name, x, y)
            
            windows.append(window_name)
            
            # 尝试打开雷柏摄像头
            cap = cv2.VideoCapture(camera_id)
            
            # 如果默认方式失败，尝试V4L2后端
            if not cap.isOpened():
                cap = cv2.VideoCapture(camera_id, cv2.CAP_V4L2)
            
            caps.append((cap, camera_id))
            
            if cap.isOpened():
                print(f"✅ 雷柏摄像头 {camera_id}: 已打开")
                
                # 设置一些基本参数
                try:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    cap.set(cv2.CAP_PROP_FPS, 30)
                    print(f"   参数设置完成")
                except:
                    print(f"   参数设置失败，使用默认值")
            else:
                print(f"❌ 雷柏摄像头 {camera_id}: 打开失败")
        
        print("\n🎯 雷柏摄像头测试说明:")
        print("- 观察每个摄像头的画面质量")
        print("- 检查是否有延迟或卡顿")
        print("- 按 'q' 键退出测试")
        print("- 按 's' 键截图保存")
        
        frame_count = 0
        while True:
            all_frames_valid = True
            
            for i, (cap, camera_id) in enumerate(caps):
                window_name = windows[i]
                
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        # 调整画面大小
                        frame = cv2.resize(frame, (400, 300))
                        
                        # 添加信息
                        cv2.putText(frame, f"Rapoo Camera {camera_id}", (10, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(frame, f"Frame: {frame_count}", (10, 60), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(frame, time.strftime("%H:%M:%S"), (10, 280), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        
                        cv2.imshow(window_name, frame)
                    else:
                        all_frames_valid = False
                        # 显示错误画面
                        error_frame = create_rapoo_error_frame(camera_id, "无法读取画面")
                        cv2.imshow(window_name, error_frame)
                else:
                    all_frames_valid = False
                    error_frame = create_rapoo_error_frame(camera_id, "摄像头未打开")
                    cv2.imshow(window_name, error_frame)
            
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                print(f"截图保存 - 帧数: {frame_count}")
            
            frame_count += 1
            
            # 每30帧检查一次状态
            if frame_count % 30 == 0:
                status = "正常" if all_frames_valid else "异常"
                print(f"雷柏摄像头状态: {status} (帧数: {frame_count})")
        
        # 清理资源
        for cap, _ in caps:
            if cap:
                cap.release()
        cv2.destroyAllWindows()
        
        print("✅ 雷柏摄像头测试完成")
        
    except Exception as e:
        print(f"❌ 雷柏摄像头测试失败: {e}")

def create_rapoo_error_frame(camera_id, error_msg):
    """创建雷柏摄像头错误显示画面"""
    frame = np.zeros((300, 400, 3), dtype=np.uint8)
    frame[:] = (20, 20, 60)  # 深蓝色背景
    
    # 添加雷柏标识
    cv2.putText(frame, "RAPOO", (150, 80), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    
    cv2.putText(frame, f"Camera {camera_id}", (130, 120), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    cv2.putText(frame, "ERROR", (150, 160), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    cv2.putText(frame, error_msg, (50, 200), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    # 添加故障排除提示
    cv2.putText(frame, "Try:", (50, 230), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    cv2.putText(frame, "1. Reconnect USB", (50, 250), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    cv2.putText(frame, "2. Check power", (50, 270), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    
    return frame

def install_rapoo_camera_support():
    """安装雷柏摄像头支持"""
    print("\n🔧 安装雷柏摄像头支持...")
    
    commands = [
        "sudo apt-get update",
        "sudo apt-get install -y v4l-utils",
        "sudo apt-get install -y uvcdynctrl",
        "sudo apt-get install -y guvcview"
    ]
    
    for cmd in commands:
        print(f"执行: {cmd}")
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                print(f"✅ 成功")
            else:
                print(f"⚠️  警告: {result.stderr}")
        except subprocess.TimeoutExpired:
            print(f"⚠️  超时")
        except Exception as e:
            print(f"❌ 失败: {e}")

def generate_rapoo_camera_config(detected_cameras):
    """生成雷柏摄像头配置"""
    print(f"\n📋 生成雷柏摄像头配置...")
    
    if not detected_cameras:
        print("❌ 未检测到摄像头，无法生成配置")
        return None
    
    # 过滤掉摄像头0（内置摄像头）
    rapoo_cameras = [cam_id for cam_id in detected_cameras if cam_id > 0]
    
    if not rapoo_cameras:
        print("❌ 未检测到雷柏USB摄像头（摄像头1及以上）")
        return None
    
    # 限制最多6个摄像头
    selected_cameras = rapoo_cameras[:6]
    
    config = {
        'rapoo_cameras': selected_cameras,
        'camera_mapping': {},
        'total_cameras': len(selected_cameras),
        'skip_builtin': True  # 跳过内置摄像头
    }
    
    # 创建摄像头映射
    for i, real_id in enumerate(selected_cameras):
        config['camera_mapping'][i] = real_id
    
    print(f"✅ 雷柏摄像头配置生成完成:")
    print(f"   - 跳过内置摄像头: 摄像头0")
    print(f"   - 雷柏USB摄像头: {config['rapoo_cameras']}")
    print(f"   - 摄像头映射:")
    for project_id, real_id in config['camera_mapping'].items():
        print(f"     项目摄像头{project_id} -> 雷柏摄像头{real_id}")
    
    return config

def main():
    """主函数"""
    print("🎥 雷柏USB摄像头检测和配置工具")
    print("=" * 60)
    print("专门针对雷柏(Rapoo)品牌USB摄像头")
    print()
    
    try:
        # 检查雷柏USB设备
        rapoo_devices = check_rapoo_usb_devices()
        
        # 详细检查视频设备
        video_devices, device_info = check_video_devices_detailed()
        
        # 检测可用摄像头
        print(f"\n🔍 检测可用摄像头...")
        available_cameras = []
        
        for i in range(10):
            try:
                # 测试兼容性
                success, backend, resolution = test_rapoo_camera_compatibility(i)
                if success:
                    available_cameras.append(i)
                    camera_type = "内置摄像头" if i == 0 else "雷柏USB摄像头"
                    print(f"✅ 摄像头 {i}: {camera_type} ({backend}, {resolution[0]}x{resolution[1]})")
                else:
                    if i < 7:  # 只显示前7个的未找到信息
                        print(f"❌ 摄像头 {i}: 未找到或不兼容")
            except Exception as e:
                if i < 7:
                    print(f"❌ 摄像头 {i}: 检测异常 - {e}")
        
        if not available_cameras:
            print("\n❌ 未检测到任何可用摄像头")
            print("\n🔧 建议操作:")
            print("1. 检查雷柏USB摄像头连接")
            print("2. 安装必要的驱动和工具")
            
            install_choice = input("是否安装摄像头支持工具？(y/n): ").strip().lower()
            if install_choice == 'y':
                install_rapoo_camera_support()
            
            return
        
        # 生成配置
        config = generate_rapoo_camera_config(available_cameras)
        
        if not config:
            print("无法生成有效配置")
            return
        
        # 询问是否测试
        print(f"\n🧪 是否测试雷柏摄像头显示？")
        test_choice = input("输入 'y' 进行测试，其他键跳过: ").strip().lower()
        
        if test_choice == 'y':
            create_rapoo_camera_test(config['rapoo_cameras'])
        
        print(f"\n📊 检测总结:")
        print(f"   - 总摄像头数量: {len(available_cameras)}")
        print(f"   - 内置摄像头: {'1个 (跳过)' if 0 in available_cameras else '0个'}")
        print(f"   - 雷柏USB摄像头: {len(config['rapoo_cameras'])} 个")
        print(f"   - 项目将使用: {config['total_cameras']} 个雷柏摄像头")
        
        if len(config['rapoo_cameras']) < 6:
            print(f"\n⚠️  建议:")
            print(f"   - 当前只有{len(config['rapoo_cameras'])}个雷柏USB摄像头")
            print(f"   - 建议连接{6-len(config['rapoo_cameras'])}个额外的雷柏USB摄像头")
            print(f"   - 系统会为缺失的摄像头显示模拟画面")
        
        print(f"\n🚀 下一步:")
        print("1. 使用 '模拟USB摄像头启动.py' 测试系统功能")
        print("2. 连接更多雷柏USB摄像头")
        print("3. 运行完整的监控系统")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断检测")
    except Exception as e:
        print(f"\n❌ 检测异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()