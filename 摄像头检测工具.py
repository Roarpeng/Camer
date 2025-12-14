#!/usr/bin/env python3
"""
摄像头检测和配置工具

帮助检测可用的摄像头数量，并配置系统显示6个视窗
"""

import cv2
import numpy as np
import time

def detect_available_cameras():
    """检测可用的摄像头"""
    print("🔍 检测可用摄像头...")
    
    available_cameras = []
    camera_info = []
    
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
                    camera_info.append({
                        'id': i,
                        'resolution': f"{width}x{height}",
                        'status': '可用'
                    })
                    print(f"✅ 摄像头 {i}: 可用 ({width}x{height})")
                else:
                    print(f"⚠️  摄像头 {i}: 已连接但无法读取画面")
                cap.release()
            else:
                if i < 6:  # 只对前6个显示未找到信息
                    print(f"❌ 摄像头 {i}: 未找到")
        except Exception as e:
            print(f"❌ 摄像头 {i}: 检测异常 - {e}")
    
    print(f"\n📊 检测结果:")
    print(f"   总计找到 {len(available_cameras)} 个可用摄像头")
    print(f"   摄像头索引: {available_cameras}")
    
    return available_cameras, camera_info

def test_6_windows_with_available_cameras(available_cameras):
    """使用可用摄像头测试6个窗口显示"""
    print(f"\n🎥 测试6个窗口显示（使用{len(available_cameras)}个真实摄像头）...")
    
    windows = []
    caps = []
    
    try:
        # 创建6个窗口
        for i in range(6):
            window_name = f"摄像头 {i}"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 400, 300)
            
            # 排列窗口
            col = i % 3
            row = i // 3
            x = col * 410
            y = row * 350
            cv2.moveWindow(window_name, x, y)
            
            windows.append(window_name)
            
            # 尝试打开对应的摄像头
            if i < len(available_cameras):
                camera_index = available_cameras[i]
                cap = cv2.VideoCapture(camera_index)
                if cap.isOpened():
                    caps.append(cap)
                    print(f"✅ 窗口 {i}: 使用真实摄像头 {camera_index}")
                else:
                    caps.append(None)
                    print(f"⚠️  窗口 {i}: 摄像头 {camera_index} 打开失败，使用模拟画面")
            else:
                caps.append(None)
                print(f"📺 窗口 {i}: 使用模拟画面（无对应摄像头）")
        
        print(f"\n✅ 6个窗口创建完成")
        print("🎯 测试说明:")
        print("- 前几个窗口显示真实摄像头画面")
        print("- 其余窗口显示彩色模拟画面")
        print("- 按 'q' 键退出测试")
        print()
        
        frame_count = 0
        while True:
            for i in range(6):
                # 获取画面
                if i < len(caps) and caps[i] and caps[i].isOpened():
                    ret, frame = caps[i].read()
                    if not ret:
                        frame = create_test_frame(i, 400, 300)
                else:
                    frame = create_test_frame(i, 400, 300)
                
                # 调整画面大小
                frame = cv2.resize(frame, (400, 300))
                
                # 添加信息
                cv2.putText(frame, f"Camera {i}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                if i < len(available_cameras):
                    cv2.putText(frame, f"Real Cam {available_cameras[i]}", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
                else:
                    cv2.putText(frame, "Simulated", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
                
                cv2.putText(frame, f"Frame {frame_count}", (10, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                
                cv2.imshow(windows[i], frame)
            
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            
            frame_count += 1
        
        # 清理资源
        for cap in caps:
            if cap:
                cap.release()
        cv2.destroyAllWindows()
        
        print("✅ 测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def create_test_frame(camera_id: int, width: int, height: int) -> np.ndarray:
    """创建测试画面"""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # 不同摄像头使用不同颜色
    colors = [
        (100, 50, 50),   # 蓝红色调
        (50, 100, 50),   # 绿红色调
        (50, 50, 100),   # 红蓝色调
        (100, 100, 50),  # 青色调
        (100, 50, 100),  # 紫色调
        (50, 100, 100)   # 黄色调
    ]
    
    color = colors[camera_id % len(colors)]
    frame[:] = color
    
    # 添加渐变效果
    for y in range(height):
        intensity = int(50 + (y / height) * 100)
        frame[y, :] = [c * intensity // 100 for c in color]
    
    # 添加摄像头标识
    cv2.putText(frame, f"Test Camera {camera_id}", (50, height//2), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    
    # 添加时间戳
    timestamp = time.strftime("%H:%M:%S")
    cv2.putText(frame, timestamp, (10, height - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    return frame

def create_config_recommendation(available_cameras):
    """根据检测结果创建配置建议"""
    print(f"\n📋 配置建议:")
    
    if len(available_cameras) >= 6:
        print("✅ 检测到6个或更多摄像头，可以完全使用真实摄像头")
        config_mode = "full_real"
    elif len(available_cameras) >= 3:
        print(f"⚠️  检测到{len(available_cameras)}个摄像头，建议混合模式（真实+模拟）")
        config_mode = "mixed"
    elif len(available_cameras) >= 1:
        print(f"⚠️  只检测到{len(available_cameras)}个摄像头，建议主要使用模拟模式")
        config_mode = "mostly_simulated"
    else:
        print("❌ 未检测到摄像头，建议使用完全模拟模式")
        config_mode = "full_simulated"
    
    print(f"\n🔧 建议的启动方式:")
    
    if config_mode == "full_real":
        print("   python 启动增强监控.py  # 使用真实摄像头")
    elif config_mode in ["mixed", "mostly_simulated"]:
        print("   python test_enhanced_monitor.py  # 混合模式测试")
        print("   python 启动增强监控.py  # 尝试真实摄像头")
    else:
        print("   python test_enhanced_monitor.py  # 完全模拟模式")
    
    return config_mode

def main():
    """主函数"""
    print("🎥 MQTT摄像头监控系统 - 摄像头检测工具")
    print("=" * 60)
    
    try:
        # 检测可用摄像头
        available_cameras, camera_info = detect_available_cameras()
        
        # 创建配置建议
        config_mode = create_config_recommendation(available_cameras)
        
        # 询问是否进行测试
        print(f"\n🧪 是否进行6窗口显示测试？")
        choice = input("输入 'y' 进行测试，其他键跳过: ").strip().lower()
        
        if choice == 'y':
            test_6_windows_with_available_cameras(available_cameras)
        
        print(f"\n📊 检测总结:")
        print(f"   - 可用摄像头数量: {len(available_cameras)}")
        print(f"   - 摄像头索引: {available_cameras}")
        print(f"   - 建议模式: {config_mode}")
        
        print(f"\n💡 使用建议:")
        if len(available_cameras) < 6:
            print("   1. 连接更多USB摄像头以获得最佳体验")
            print("   2. 使用测试模式验证界面功能")
            print("   3. 系统会自动处理缺失的摄像头（显示模拟画面）")
        else:
            print("   1. 摄像头数量充足，可以正常使用所有功能")
            print("   2. 建议使用增强版启动脚本")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断检测")
    except Exception as e:
        print(f"\n❌ 检测异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()