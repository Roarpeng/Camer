#!/usr/bin/env python3
"""
彩色摄像头测试工具
专门诊断摄像头彩色模式问题
"""

import cv2
import numpy as np
import time

def test_camera_color_modes():
    """测试摄像头彩色模式"""
    
    print("=== 彩色摄像头测试工具 ===")
    print("专门诊断摄像头彩色模式问题")
    print()
    
    # 测试不同后端
    backends = [
        (cv2.CAP_DSHOW, "DirectShow"),
        (cv2.CAP_MSMF, "Media Foundation"),
        (cv2.CAP_ANY, "Any")
    ]
    
    for backend, name in backends:
        print(f"=== 测试 {name} 后端 ===")
        
        try:
            cap = cv2.VideoCapture(0, backend)
            
            if not cap.isOpened():
                print(f"无法打开摄像头使用 {name} 后端")
                continue
            
            # 基本配置
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # 测试不同的彩色模式设置
            color_configs = [
                ("默认设置", {}),
                ("强制RGB", {cv2.CAP_PROP_CONVERT_RGB: 1}),
                ("FOURCC MJPG", {cv2.CAP_PROP_FOURCC: cv2.VideoWriter_fourcc('M','J','P','G')}),
                ("FOURCC YUYV", {cv2.CAP_PROP_FOURCC: cv2.VideoWriter_fourcc('Y','U','Y','V')}),
                ("高饱和度", {cv2.CAP_PROP_SATURATION: 100}),
            ]
            
            for config_name, config_props in color_configs:
                print(f"\n--- 测试配置: {config_name} ---")
                
                # 应用配置
                for prop, value in config_props.items():
                    try:
                        cap.set(prop, value)
                    except:
                        pass
                
                # 应用最佳曝光和亮度设置
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                cap.set(cv2.CAP_PROP_EXPOSURE, -5)
                cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.8)
                cap.set(cv2.CAP_PROP_CONTRAST, 0.85)
                cap.set(cv2.CAP_PROP_SATURATION, 0.8)
                cap.set(cv2.CAP_PROP_GAIN, 80)
                
                # 等待设置生效
                time.sleep(0.5)
                
                # 预热摄像头
                for _ in range(5):
                    ret, frame = cap.read()
                    time.sleep(0.1)
                
                # 捕获测试帧
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    print(f"  帧尺寸: {frame.shape}")
                    
                    # 分析图像
                    if len(frame.shape) == 3:
                        # 彩色图像
                        b_avg = np.mean(frame[:,:,0])
                        g_avg = np.mean(frame[:,:,1])
                        r_avg = np.mean(frame[:,:,2])
                        
                        print(f"  BGR平均值: B={b_avg:.1f}, G={g_avg:.1f}, R={r_avg:.1f}")
                        
                        # 检查是否真的是彩色
                        color_variance = np.var([b_avg, g_avg, r_avg])
                        if color_variance > 10:
                            print(f"  ✓ 彩色图像 (方差: {color_variance:.1f})")
                        else:
                            print(f"  ✗ 灰度图像 (方差: {color_variance:.1f})")
                        
                        # 检查颜色通道分布
                        b_std = np.std(frame[:,:,0])
                        g_std = np.std(frame[:,:,1])
                        r_std = np.std(frame[:,:,2])
                        print(f"  BGR标准差: B={b_std:.1f}, G={g_std:.1f}, R={r_std:.1f}")
                        
                    elif len(frame.shape) == 2:
                        # 灰度图像
                        avg_brightness = np.mean(frame)
                        print(f"  ✗ 灰度图像，平均亮度: {avg_brightness:.1f}")
                    
                    # 保存测试图像
                    filename = f"color_test_{name.replace(' ', '')}_{config_name.replace(' ', '_')}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"  保存图像: {filename}")
                    
                else:
                    print(f"  ✗ 无法捕获帧")
            
            cap.release()
            
        except Exception as e:
            print(f"测试 {name} 后端时出错: {e}")
    
    print("\n=== 测试完成 ===")
    print("请检查生成的图像文件:")
    print("- 如果图像是彩色的，说明摄像头支持彩色模式")
    print("- 如果图像是灰度的，可能需要调整驱动或设置")

def interactive_color_test():
    """交互式彩色测试"""
    
    print("\n=== 交互式彩色测试 ===")
    
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return
    
    # 配置摄像头
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)  # 强制RGB模式
    
    # 应用最佳设置
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, -5)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.8)
    cap.set(cv2.CAP_PROP_CONTRAST, 0.85)
    cap.set(cv2.CAP_PROP_SATURATION, 0.8)
    cap.set(cv2.CAP_PROP_GAIN, 80)
    
    cv2.namedWindow('Color Test', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Color Test', 640, 480)
    
    print("控制说明:")
    print("  SPACE - 保存当前帧")
    print("  C - 分析当前帧颜色")
    print("  Q - 退出")
    print()
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            
            if ret and frame is not None:
                frame_count += 1
                
                # 分析颜色信息
                if len(frame.shape) == 3:
                    b_avg = np.mean(frame[:,:,0])
                    g_avg = np.mean(frame[:,:,1])
                    r_avg = np.mean(frame[:,:,2])
                    color_variance = np.var([b_avg, g_avg, r_avg])
                    
                    # 在图像上显示信息
                    display_frame = frame.copy()
                    cv2.putText(display_frame, f"BGR: ({b_avg:.0f},{g_avg:.0f},{r_avg:.0f})", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    if color_variance > 10:
                        cv2.putText(display_frame, "COLOR MODE", (10, 60),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    else:
                        cv2.putText(display_frame, "GRAYSCALE MODE", (10, 60),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    cv2.putText(display_frame, f"Frame: {frame_count}", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    cv2.imshow('Color Test', display_frame)
                else:
                    # 灰度图像
                    cv2.putText(frame, "GRAYSCALE IMAGE", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.imshow('Color Test', frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:
                break
            elif key == ord(' '):
                if ret and frame is not None:
                    filename = f"interactive_color_test_{int(time.time())}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"保存帧: {filename}")
            elif key == ord('c'):
                if ret and frame is not None and len(frame.shape) == 3:
                    b_avg = np.mean(frame[:,:,0])
                    g_avg = np.mean(frame[:,:,1])
                    r_avg = np.mean(frame[:,:,2])
                    color_variance = np.var([b_avg, g_avg, r_avg])
                    
                    print(f"\n当前帧颜色分析:")
                    print(f"  BGR平均值: B={b_avg:.1f}, G={g_avg:.1f}, R={r_avg:.1f}")
                    print(f"  颜色方差: {color_variance:.1f}")
                    print(f"  模式: {'彩色' if color_variance > 10 else '灰度'}")
    
    except KeyboardInterrupt:
        print("\n用户中断")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()

def main():
    """主函数"""
    print("选择测试模式:")
    print("1. 自动彩色模式测试")
    print("2. 交互式彩色测试")
    
    try:
        choice = input("请输入选择 (1 或 2): ").strip()
        
        if choice == "1":
            test_camera_color_modes()
        elif choice == "2":
            interactive_color_test()
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