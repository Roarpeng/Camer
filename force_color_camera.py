#!/usr/bin/env python3
"""
强制彩色摄像头工具
尝试各种方法强制摄像头输出真正的彩色图像
"""

import cv2
import numpy as np
import time

def test_all_camera_backends():
    """测试所有可能的摄像头后端和格式"""
    
    print("=== 强制彩色摄像头工具 ===")
    print("尝试各种方法强制摄像头输出真正的彩色图像")
    print()
    
    # 测试所有可能的后端
    backends = [
        (cv2.CAP_DSHOW, "DirectShow"),
        (cv2.CAP_MSMF, "Media Foundation"), 
        (cv2.CAP_V4L2, "Video4Linux2"),
        (cv2.CAP_GSTREAMER, "GStreamer"),
        (cv2.CAP_FFMPEG, "FFmpeg"),
        (cv2.CAP_ANY, "Any")
    ]
    
    # 测试不同的FOURCC格式
    fourcc_formats = [
        ('MJPG', cv2.VideoWriter_fourcc('M','J','P','G')),
        ('YUYV', cv2.VideoWriter_fourcc('Y','U','Y','V')),
        ('RGB3', cv2.VideoWriter_fourcc('R','G','B','3')),
        ('BGR3', cv2.VideoWriter_fourcc('B','G','R','3')),
        ('YUY2', cv2.VideoWriter_fourcc('Y','U','Y','2')),
        ('UYVY', cv2.VideoWriter_fourcc('U','Y','V','Y')),
    ]
    
    best_result = None
    best_variance = 0
    
    for backend, backend_name in backends:
        print(f"=== 测试 {backend_name} 后端 ===")
        
        try:
            cap = cv2.VideoCapture(0, backend)
            
            if not cap.isOpened():
                print(f"无法打开摄像头使用 {backend_name}")
                continue
            
            for fourcc_name, fourcc_code in fourcc_formats:
                print(f"\n--- 测试 {fourcc_name} 格式 ---")
                
                # 设置FOURCC格式
                cap.set(cv2.CAP_PROP_FOURCC, fourcc_code)
                
                # 尝试不同分辨率
                resolutions = [
                    (640, 480),
                    (320, 240),
                    (800, 600),
                    (1280, 720),
                    (1920, 1080)
                ]
                
                for width, height in resolutions:
                    print(f"  分辨率 {width}x{height}...", end=" ")
                    
                    # 设置分辨率
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    
                    # 强制彩色设置
                    cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)
                    cap.set(cv2.CAP_PROP_MODE, 0)  # 尝试设置模式
                    
                    # 曝光和亮度设置
                    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                    cap.set(cv2.CAP_PROP_EXPOSURE, -5)
                    cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.8)
                    cap.set(cv2.CAP_PROP_CONTRAST, 0.85)
                    cap.set(cv2.CAP_PROP_SATURATION, 1.0)  # 最大饱和度
                    cap.set(cv2.CAP_PROP_HUE, 0.5)
                    cap.set(cv2.CAP_PROP_GAIN, 100)
                    
                    # 等待设置生效
                    time.sleep(0.3)
                    
                    # 预热摄像头
                    for _ in range(5):
                        ret, frame = cap.read()
                        time.sleep(0.05)
                    
                    # 捕获测试帧
                    ret, frame = cap.read()
                    
                    if ret and frame is not None:
                        actual_shape = frame.shape
                        
                        if len(actual_shape) == 3:
                            b_avg = np.mean(frame[:,:,0])
                            g_avg = np.mean(frame[:,:,1])
                            r_avg = np.mean(frame[:,:,2])
                            
                            color_variance = np.var([b_avg, g_avg, r_avg])
                            
                            print(f"BGR=({b_avg:.1f},{g_avg:.1f},{r_avg:.1f}) 方差={color_variance:.2f}", end=" ")
                            
                            if color_variance > best_variance:
                                best_variance = color_variance
                                best_result = {
                                    'backend': backend_name,
                                    'fourcc': fourcc_name,
                                    'resolution': (width, height),
                                    'actual_shape': actual_shape,
                                    'bgr': (b_avg, g_avg, r_avg),
                                    'variance': color_variance,
                                    'frame': frame.copy()
                                }
                            
                            if color_variance > 10:
                                print("✓ 彩色")
                                
                                # 保存成功的配置
                                filename = f"color_success_{backend_name}_{fourcc_name}_{width}x{height}.jpg"
                                cv2.imwrite(filename, frame)
                                print(f" -> 保存: {filename}")
                            else:
                                print("✗ 灰度")
                        else:
                            print("✗ 非彩色格式")
                    else:
                        print("✗ 捕获失败")
            
            cap.release()
            
        except Exception as e:
            print(f"测试 {backend_name} 时出错: {e}")
    
    # 输出最佳结果
    print(f"\n=== 测试结果 ===")
    if best_result:
        print(f"最佳配置:")
        print(f"  后端: {best_result['backend']}")
        print(f"  格式: {best_result['fourcc']}")
        print(f"  分辨率: {best_result['resolution']}")
        print(f"  实际尺寸: {best_result['actual_shape']}")
        print(f"  BGR值: {best_result['bgr']}")
        print(f"  颜色方差: {best_result['variance']:.2f}")
        
        # 保存最佳结果
        cv2.imwrite("best_color_result.jpg", best_result['frame'])
        print(f"  最佳图像已保存: best_color_result.jpg")
        
        if best_result['variance'] > 10:
            print("✓ 找到真正的彩色配置")
        else:
            print("✗ 所有配置都是灰度模式")
    else:
        print("✗ 没有找到任何可用配置")
    
    return best_result

def test_external_lighting():
    """测试外部光照对彩色的影响"""
    
    print("\n=== 测试外部光照影响 ===")
    print("请在摄像头前放置不同颜色的物体进行测试")
    
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return
    
    # 使用最基本的设置
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # 使用自动曝光
    cap.set(cv2.CAP_PROP_SATURATION, 1.0)      # 最大饱和度
    
    cv2.namedWindow('Lighting Test', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Lighting Test', 640, 480)
    
    print("控制说明:")
    print("  SPACE - 分析当前帧颜色")
    print("  S - 保存当前帧")
    print("  Q - 退出")
    print()
    print("测试建议:")
    print("1. 在摄像头前放置红色物体")
    print("2. 在摄像头前放置绿色物体")
    print("3. 在摄像头前放置蓝色物体")
    print("4. 改变光照条件")
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            
            if ret and frame is not None:
                frame_count += 1
                
                # 分析整体颜色
                if len(frame.shape) == 3:
                    b_avg = np.mean(frame[:,:,0])
                    g_avg = np.mean(frame[:,:,1])
                    r_avg = np.mean(frame[:,:,2])
                    color_variance = np.var([b_avg, g_avg, r_avg])
                    
                    # 分析中心区域颜色
                    h, w = frame.shape[:2]
                    center_region = frame[h//4:3*h//4, w//4:3*w//4]
                    b_center = np.mean(center_region[:,:,0])
                    g_center = np.mean(center_region[:,:,1])
                    r_center = np.mean(center_region[:,:,2])
                    center_variance = np.var([b_center, g_center, r_center])
                    
                    # 在图像上显示信息
                    display_frame = frame.copy()
                    cv2.putText(display_frame, f"Overall BGR: ({b_avg:.0f},{g_avg:.0f},{r_avg:.0f})", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    cv2.putText(display_frame, f"Overall Variance: {color_variance:.2f}", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    cv2.putText(display_frame, f"Center BGR: ({b_center:.0f},{g_center:.0f},{r_center:.0f})", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    cv2.putText(display_frame, f"Center Variance: {center_variance:.2f}", (10, 120),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    # 绘制中心区域框
                    cv2.rectangle(display_frame, (w//4, h//4), (3*w//4, 3*h//4), (0, 255, 255), 2)
                    
                    # 状态指示
                    if center_variance > 10:
                        cv2.putText(display_frame, "COLOR DETECTED", (10, 160),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    else:
                        cv2.putText(display_frame, "GRAYSCALE MODE", (10, 160),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    
                    cv2.imshow('Lighting Test', display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:
                break
            elif key == ord(' '):
                if ret and frame is not None and len(frame.shape) == 3:
                    print(f"\n帧 {frame_count} 颜色分析:")
                    print(f"  整体BGR: ({b_avg:.1f}, {g_avg:.1f}, {r_avg:.1f})")
                    print(f"  整体方差: {color_variance:.2f}")
                    print(f"  中心BGR: ({b_center:.1f}, {g_center:.1f}, {r_center:.1f})")
                    print(f"  中心方差: {center_variance:.2f}")
                    print(f"  状态: {'彩色' if center_variance > 10 else '灰度'}")
            elif key == ord('s'):
                if ret and frame is not None:
                    filename = f"lighting_test_{int(time.time())}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"保存帧: {filename}")
    
    except KeyboardInterrupt:
        print("\n用户中断")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()

def main():
    """主函数"""
    
    print("选择测试模式:")
    print("1. 测试所有摄像头后端和格式")
    print("2. 测试外部光照影响")
    print("3. 执行完整测试")
    
    try:
        choice = input("请输入选择 (1-3): ").strip()
        
        if choice == "1":
            test_all_camera_backends()
        elif choice == "2":
            test_external_lighting()
        elif choice == "3":
            result = test_all_camera_backends()
            if result and result['variance'] <= 10:
                print("\n所有后端都是灰度模式，测试外部光照...")
                test_external_lighting()
        else:
            print("[ERROR] 无效选择")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())