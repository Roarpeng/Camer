#!/usr/bin/env python3
"""
USB摄像头检测工具

专门检测外接USB摄像头，跳过笔记本自带摄像头
- 检测所有可用摄像头
- 识别哪些是外接USB摄像头
- 配置系统使用外接摄像头
"""

import cv2
import numpy as np
import time
import subprocess
import re

def get_camera_info_linux():
    """在Linux系统上获取摄像头详细信息"""
    camera_info = {}
    
    try:
        # 使用v4l2-ctl获取摄像头信息
        result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            current_device = None
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('/dev/video'):
                    # 设备名称行
                    current_device = line
                elif line.startswith('/dev/video'):
                    # 设备路径行
                    video_num = re.search(r'/dev/video(\d+)', line)
                    if video_num:
                        camera_id = int(video_num.group(1))
                        camera_info[camera_id] = {
                            'device_name': current_device,
                            'device_path': line,
                            'is_usb': 'usb' in current_device.lower() or 'usb' in line.lower()
                        }
        
    except FileNotFoundError:
        print("⚠️  v4l2-ctl未安装，无法获取详细摄像头信息")
        print("   安装命令: sudo apt-get install v4l-utils")
    
    return camera_info

def detect_all_cameras():
    """检测所有可用摄像头"""
    print("🔍 检测所有可用摄像头...")
    
    available_cameras = []
    camera_details = []
    
    # 获取Linux系统摄像头信息
    camera_info = get_camera_info_linux()
    
    # 检测前10个摄像头索引
    for i in range(10):
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # 尝试读取一帧
                ret, frame = cap.read()
                if ret and frame is not None:
                    height, width = frame.shape[:2]
                    available_cameras.append(i)
                    
                    # 获取摄像头详细信息
                    device_info = camera_info.get(i, {})
                    device_name = device_info.get('device_name', f'Camera {i}')
                    is_usb = device_info.get('is_usb', False)
                    
                    # 判断是否为USB摄像头
                    if not is_usb:
                        # 如果v4l2信息不可用，使用启发式判断
                        is_usb = i > 0  # 通常摄像头0是内置摄像头
                    
                    camera_detail = {
                        'id': i,
                        'resolution': f"{width}x{height}",
                        'device_name': device_name,
                        'is_usb': is_usb,
                        'status': '可用'
                    }
                    camera_details.append(camera_detail)
                    
                    camera_type = "USB摄像头" if is_usb else "内置摄像头"
                    print(f"{'✅' if is_usb else '📱'} 摄像头 {i}: {camera_type} ({width}x{height}) - {device_name}")
                else:
                    print(f"⚠️  摄像头 {i}: 已连接但无法读取画面")
                cap.release()
            else:
                if i < 8:  # 只对前8个显示未找到信息
                    print(f"❌ 摄像头 {i}: 未找到")
        except Exception as e:
            print(f"❌ 摄像头 {i}: 检测异常 - {e}")
    
    return available_cameras, camera_details

def filter_usb_cameras(camera_details):
    """筛选出USB摄像头"""
    usb_cameras = [cam for cam in camera_details if cam['is_usb']]
    builtin_cameras = [cam for cam in camera_details if not cam['is_usb']]
    
    print(f"\n📊 摄像头分类结果:")
    print(f"   内置摄像头: {len(builtin_cameras)} 个")
    for cam in builtin_cameras:
        print(f"     - 摄像头 {cam['id']}: {cam['device_name']}")
    
    print(f"   USB摄像头: {len(usb_cameras)} 个")
    for cam in usb_cameras:
        print(f"     - 摄像头 {cam['id']}: {cam['device_name']}")
    
    return usb_cameras, builtin_cameras

def test_usb_cameras(usb_cameras):
    """测试USB摄像头显示"""
    if not usb_cameras:
        print("\n❌ 未检测到USB摄像头，无法进行测试")
        return False
    
    print(f"\n🎥 测试{len(usb_cameras)}个USB摄像头显示...")
    
    # 限制最多显示6个USB摄像头
    test_cameras = usb_cameras[:6]
    
    windows = []
    caps = []
    
    try:
        # 创建窗口
        for i, cam_info in enumerate(test_cameras):
            camera_id = cam_info['id']
            window_name = f"USB摄像头 {camera_id}"
            
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 400, 300)
            
            # 排列窗口
            col = i % 3
            row = i // 3
            x = col * 410
            y = row * 350
            cv2.moveWindow(window_name, x, y)
            
            windows.append(window_name)
            
            # 打开对应的USB摄像头
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                caps.append((cap, camera_id, cam_info))
                print(f"✅ USB摄像头 {camera_id}: 已打开")
            else:
                caps.append((None, camera_id, cam_info))
                print(f"❌ USB摄像头 {camera_id}: 打开失败")
        
        print(f"\n✅ {len(test_cameras)}个USB摄像头窗口创建完成")
        print("🎯 测试说明:")
        print("- 每个窗口显示对应USB摄像头的实时画面")
        print("- 窗口标题显示摄像头ID和设备名称")
        print("- 按 'q' 键退出测试")
        print()
        
        frame_count = 0
        while True:
            for i, (cap, camera_id, cam_info) in enumerate(caps):
                window_name = windows[i]
                
                if cap and cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        # 调整画面大小
                        frame = cv2.resize(frame, (400, 300))
                        
                        # 添加信息
                        cv2.putText(frame, f"USB Camera {camera_id}", (10, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        cv2.putText(frame, cam_info['device_name'][:30], (10, 60), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(frame, f"Frame {frame_count}", (10, 90), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                        
                        cv2.imshow(window_name, frame)
                    else:
                        # 创建错误画面
                        error_frame = create_error_frame(camera_id, "无法读取画面")
                        cv2.imshow(window_name, error_frame)
                else:
                    # 创建错误画面
                    error_frame = create_error_frame(camera_id, "摄像头打开失败")
                    cv2.imshow(window_name, error_frame)
            
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            
            frame_count += 1
        
        # 清理资源
        for cap, _, _ in caps:
            if cap:
                cap.release()
        cv2.destroyAllWindows()
        
        print("✅ USB摄像头测试完成")
        return True
        
    except Exception as e:
        print(f"❌ USB摄像头测试失败: {e}")
        return False

def create_error_frame(camera_id: int, error_msg: str) -> np.ndarray:
    """创建错误显示画面"""
    frame = np.zeros((300, 400, 3), dtype=np.uint8)
    frame[:] = (0, 0, 50)  # 深红色背景
    
    # 添加摄像头ID
    cv2.putText(frame, f"USB Camera {camera_id}", (100, 120), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    # 添加错误信息
    cv2.putText(frame, "ERROR", (150, 150), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(frame, error_msg, (50, 180), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    return frame

def generate_usb_camera_config(usb_cameras):
    """生成USB摄像头配置"""
    print(f"\n📋 生成USB摄像头配置...")
    
    if len(usb_cameras) == 0:
        print("❌ 未检测到USB摄像头，无法生成配置")
        return None
    
    # 选择前6个USB摄像头
    selected_cameras = usb_cameras[:6]
    
    config = {
        'usb_cameras': [cam['id'] for cam in selected_cameras],
        'camera_mapping': {},
        'total_cameras': len(selected_cameras)
    }
    
    # 创建摄像头映射 (项目中的摄像头0-5 对应 实际的USB摄像头ID)
    for i, cam_info in enumerate(selected_cameras):
        config['camera_mapping'][i] = cam_info['id']
    
    print(f"✅ USB摄像头配置生成完成:")
    print(f"   - 选择的USB摄像头: {config['usb_cameras']}")
    print(f"   - 摄像头映射:")
    for project_id, real_id in config['camera_mapping'].items():
        device_name = next(cam['device_name'] for cam in selected_cameras if cam['id'] == real_id)
        print(f"     项目摄像头{project_id} -> 实际摄像头{real_id} ({device_name})")
    
    return config

def create_usb_camera_startup_script(usb_config):
    """创建USB摄像头启动脚本"""
    if not usb_config:
        return
    
    script_content = f'''#!/usr/bin/env python3
"""
USB摄像头专用启动脚本

使用外接USB摄像头，跳过笔记本内置摄像头
配置: {usb_config['camera_mapping']}
"""

import sys
import time
import numpy as np
import cv2
from mqtt_camera_monitoring.config import VisualMonitorConfig
from mqtt_camera_monitoring.visual_monitor import EnhancedVisualMonitor
from mqtt_camera_monitoring.camera_manager import CameraFrame
from mqtt_camera_monitoring.light_detector import RedLightDetection

# USB摄像头配置
USB_CAMERA_MAPPING = {usb_config['camera_mapping']}
TOTAL_CAMERAS = {usb_config['total_cameras']}

def get_real_camera_id(project_camera_id):
    """获取实际摄像头ID"""
    return USB_CAMERA_MAPPING.get(project_camera_id, project_camera_id)

def create_usb_camera_frame(project_camera_id: int, width: int = 640, height: int = 480) -> np.ndarray:
    """从USB摄像头获取画面"""
    real_camera_id = get_real_camera_id(project_camera_id)
    
    try:
        cap = cv2.VideoCapture(real_camera_id)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                # 调整画面大小
                frame = cv2.resize(frame, (width, height))
                
                # 添加摄像头信息
                cv2.putText(frame, f"USB Cam {{project_camera_id}} (Real {{real_camera_id}})", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # 添加时间戳
                timestamp = time.strftime("%H:%M:%S")
                cv2.putText(frame, timestamp, (10, height - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                return frame
    except Exception as e:
        print(f"获取USB摄像头{{project_camera_id}}(实际{{real_camera_id}})画面失败: {{e}}")
    
    # 创建错误画面
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (0, 0, 50)
    
    cv2.putText(frame, f"USB Camera {{project_camera_id}}", (50, height//2 - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, f"Real ID: {{real_camera_id}}", (50, height//2 + 10), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    cv2.putText(frame, "ERROR", (50, height//2 + 40), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    return frame

def create_test_detection(camera_id: int) -> RedLightDetection:
    """创建测试检测结果"""
    if camera_id % 2 == 0:
        return RedLightDetection(
            count=2,
            total_area=1500.0 + camera_id * 100,
            bounding_boxes=[(100, 200, 50, 50), (275, 195, 50, 50)],
            contours=[],
            timestamp=time.time()
        )
    else:
        return RedLightDetection(
            count=0, total_area=0.0, bounding_boxes=[], contours=[], timestamp=time.time()
        )

def main():
    """主启动函数"""
    print("🎥 USB摄像头专用监控系统")
    print("=" * 50)
    print("USB摄像头映射:")
    for project_id, real_id in USB_CAMERA_MAPPING.items():
        print(f"  项目摄像头{{project_id}} -> 实际USB摄像头{{real_id}}")
    print()
    
    try:
        # 创建配置
        visual_config = VisualMonitorConfig(
            window_width=400, window_height=300,
            show_detection_boxes=True, box_color=[0, 255, 0], box_thickness=2
        )
        
        # 创建监控器
        monitor = EnhancedVisualMonitor(visual_config, camera_count=TOTAL_CAMERAS)
        
        # 创建窗口
        if not monitor.create_windows():
            print("❌ 窗口创建失败！")
            return
        
        print("✅ USB摄像头监控系统启动成功！")
        print("- 按 'q' 键退出系统")
        
        # 等待GUI启动
        time.sleep(2)
        
        # 添加日志
        monitor.add_log_entry("INFO", "USB摄像头监控系统启动")
        monitor.add_log_entry("INFO", f"使用{{TOTAL_CAMERAS}}个USB摄像头")
        
        # 主循环
        frame_count = 0
        baseline_set = False
        
        while True:
            try:
                frames = []
                detection_results = []
                
                for camera_id in range(TOTAL_CAMERAS):
                    # 从USB摄像头获取画面
                    frame_data = create_usb_camera_frame(camera_id)
                    
                    camera_frame = CameraFrame(
                        camera_id=camera_id, frame=frame_data,
                        timestamp=time.time(), is_valid=True
                    )
                    frames.append(camera_frame)
                    
                    # 创建检测结果
                    detection = create_test_detection(camera_id)
                    detection_results.append(detection)
                    
                    # 更新检测数据
                    if not baseline_set and frame_count > 30:
                        monitor.update_camera_detection_data(
                            camera_id, detection.count, detection.total_area,
                            detection.count, detection.total_area
                        )
                        if camera_id == TOTAL_CAMERAS - 1:
                            baseline_set = True
                            monitor.add_log_entry("INFO", "USB摄像头基线已建立")
                
                # 更新显示
                monitor.update_display(frames, detection_results)
                
                # 检查退出
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q'):
                    break
                
                frame_count += 1
                
                if frame_count % 60 == 0:
                    monitor.add_log_entry("DEBUG", f"USB摄像头系统运行正常，帧数: {{frame_count}}")
                
                time.sleep(0.033)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"运行错误: {{e}}")
                monitor.add_log_entry("ERROR", f"系统错误: {{e}}")
                break
    
    except Exception as e:
        print(f"启动失败: {{e}}")
    finally:
        if 'monitor' in locals():
            monitor.close_windows()
        cv2.destroyAllWindows()
        print("✅ USB摄像头监控系统已关闭")

if __name__ == "__main__":
    main()
'''
    
    with open("USB摄像头启动.py", "w", encoding="utf-8") as f:
        f.write(script_content)
    
    print(f"\n✅ USB摄像头启动脚本已生成: USB摄像头启动.py")

def main():
    """主函数"""
    print("🎥 USB摄像头检测和配置工具")
    print("=" * 60)
    print("功能: 检测外接USB摄像头，跳过笔记本内置摄像头")
    print()
    
    try:
        # 检测所有摄像头
        available_cameras, camera_details = detect_all_cameras()
        
        if not available_cameras:
            print("❌ 未检测到任何摄像头")
            return
        
        # 筛选USB摄像头
        usb_cameras, builtin_cameras = filter_usb_cameras(camera_details)
        
        if not usb_cameras:
            print("❌ 未检测到USB摄像头")
            print("请确认:")
            print("1. USB摄像头已正确连接")
            print("2. USB摄像头驱动已安装")
            print("3. USB端口工作正常")
            return
        
        # 生成配置
        usb_config = generate_usb_camera_config(usb_cameras)
        
        # 询问是否测试
        print(f"\n🧪 是否测试USB摄像头显示？")
        choice = input("输入 'y' 进行测试，其他键跳过: ").strip().lower()
        
        if choice == 'y':
            test_usb_cameras(usb_cameras)
        
        # 询问是否生成启动脚本
        print(f"\n🚀 是否生成USB摄像头专用启动脚本？")
        choice = input("输入 'y' 生成脚本，其他键跳过: ").strip().lower()
        
        if choice == 'y':
            create_usb_camera_startup_script(usb_config)
        
        print(f"\n📊 检测总结:")
        print(f"   - 总摄像头数量: {len(available_cameras)}")
        print(f"   - 内置摄像头: {len(builtin_cameras)} 个")
        print(f"   - USB摄像头: {len(usb_cameras)} 个")
        print(f"   - 项目将使用: 前{min(6, len(usb_cameras))}个USB摄像头")
        
        if len(usb_cameras) < 6:
            print(f"\n⚠️  建议:")
            print(f"   - 当前只有{len(usb_cameras)}个USB摄像头")
            print(f"   - 建议连接{6-len(usb_cameras)}个额外的USB摄像头")
            print(f"   - 系统会为缺失的摄像头显示模拟画面")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断检测")
    except Exception as e:
        print(f"\n❌ 检测异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()