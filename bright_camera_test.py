#!/usr/bin/env python3
"""
高亮度摄像头测试
专门用于解决摄像头图像过暗的问题
"""

import cv2
import numpy as np
import time

def bright_camera_test():
    """高亮度摄像头测试"""
    
    print("=== 高亮度摄像头测试 ===")
    print("专门用于解决摄像头图像过暗的问题")
    print()
    
    # 测试摄像头0
    camera_id = 0
    
    # 尝试不同后端
    backends = [
        (cv2.CAP_DSHOW, "DirectShow"),
        (cv2.CAP_MSMF, "Media Foundation"),
        (cv2.CAP_ANY, "Any")
    ]
    
    for backend, name in backends:
        print(f"=== 测试 {name} 后端 ===")
        
        try:
            cap = cv2.VideoCapture(camera_id, backend)
            
            if not cap.isOpened():
                print(f"无法打开摄像头 {camera_id} 使用 {name} 后端")
                continue
            
            # 基本配置
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)  # 确保彩色模式
            cap.set(cv2.CAP_PROP_FPS, 30)
            
            # 测试配置组合
            test_configs = [
                # (auto_exposure, exposure, brightness, contrast, gain, description)
                (0.75, 0, 100, 100, 100, "自动曝光+最高亮度"),
                (0.75, 0, 90, 90, 80, "自动曝光+高亮度"),
                (0.25, 10, 100, 100, 100, "手动曝光10+最高亮度"),
                (0.25, 8, 100, 100, 100, "手动曝光8+最高亮度"),
                (0.25, 6, 100, 100, 100, "手动曝光6+最高亮度"),
                (0.25, 5, 100, 100, 100, "手动曝光5+最高亮度"),
                (0.25, 4, 100, 100, 100, "手动曝光4+最高亮度"),
                (0.25, 3, 100, 100, 100, "手动曝光3+最高亮度"),
                (0.25, 2, 100, 100, 100, "手动曝光2+最高亮度"),
                (0.25, 1, 100, 100, 100, "手动曝光1+最高亮度"),
                (0.25, 0, 100, 100, 100, "手动曝光0+最高亮度"),
                (0.25, -1, 100, 100, 100, "手动曝光-1+最高亮度"),
                (0.25, -2, 100, 100, 100, "手动曝光-2+最高亮度"),
            ]
            
            best_config = None
            best_brightness = 0
            
            for auto_exp, exposure, brightness, contrast, gain, desc in test_configs:
                print(f"\n--- 测试配置: {desc} ---")
                
                # 应用配置
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, auto_exp)
                if auto_exp == 0.25:  # 手动曝光
                    cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
                
                cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness / 100.0)
                cap.set(cv2.CAP_PROP_CONTRAST, contrast / 100.0)
                cap.set(cv2.CAP_PROP_SATURATION, 80 / 100.0)
                
                # 尝试设置增益
                try:
                    cap.set(cv2.CAP_PROP_GAIN, gain)
                except:
                    pass
                
                # 等待设置生效
                time.sleep(1.0)
                
                # 预热摄像头
                for _ in range(5):
                    ret, frame = cap.read()
                    time.sleep(0.1)
                
                # 测试多帧取最佳
                max_frame_brightness = 0
                best_frame = None
                
                for i in range(10):
                    ret, frame = cap.read()
                    
                    if ret and frame is not None:
                        avg_brightness = np.mean(frame)
                        
                        if avg_brightness > max_frame_brightness:
                            max_frame_brightness = avg_brightness
                            best_frame = frame
                        
                        print(f"  帧 {i+1}: 亮度 {avg_brightness:.1f}")
                    else:
                        print(f"  帧 {i+1}: 捕获失败")
                    
                    time.sleep(0.1)
                
                if best_frame is not None:
                    # 保存最佳帧
                    filename = f"bright_test_{name.replace(' ', '')}_{desc.replace('+', '_').replace(' ', '_')}.jpg"
                    cv2.imwrite(filename, best_frame)
                    
                    print(f"  最佳亮度: {max_frame_brightness:.1f}")
                    print(f"  保存图像: {filename}")
                    
                    # 分析图像
                    if len(best_frame.shape) == 3:
                        b_avg = np.mean(best_frame[:,:,0])
                        g_avg = np.mean(best_frame[:,:,1])
                        r_avg = np.mean(best_frame[:,:,2])
                        print(f"  BGR平均: B={b_avg:.1f}, G={g_avg:.1f}, R={r_avg:.1f}")
                    
                    # 记录最佳配置
                    if max_frame_brightness > best_brightness:
                        best_brightness = max_frame_brightness
                        best_config = (auto_exp, exposure, brightness, contrast, gain, desc)
                else:
                    print(f"  无法捕获有效帧")
            
            cap.release()
            
            # 输出最佳配置
            if best_config:
                auto_exp, exposure, brightness, contrast, gain, desc = best_config
                print(f"\n=== {name} 后端最佳配置 ===")
                print(f"配置: {desc}")
                print(f"最佳亮度: {best_brightness:.1f}")
                print(f"参数:")
                print(f"  AUTO_EXPOSURE: {auto_exp}")
                if auto_exp == 0.25:
                    print(f"  EXPOSURE: {exposure}")
                print(f"  BRIGHTNESS: {brightness}")
                print(f"  CONTRAST: {contrast}")
                print(f"  GAIN: {gain}")
                
                # 生成配置代码
                print(f"\n代码配置:")
                print(f"cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, {auto_exp})")
                if auto_exp == 0.25:
                    print(f"cap.set(cv2.CAP_PROP_EXPOSURE, {exposure})")
                print(f"cap.set(cv2.CAP_PROP_BRIGHTNESS, {brightness / 100.0})")
                print(f"cap.set(cv2.CAP_PROP_CONTRAST, {contrast / 100.0})")
                print(f"cap.set(cv2.CAP_PROP_GAIN, {gain})")
            else:
                print(f"\n{name} 后端: 所有配置都失败")
            
        except Exception as e:
            print(f"测试 {name} 后端时出错: {e}")
    
    print("\n=== 测试完成 ===")
    print("请检查生成的图像文件，找到最亮的图像对应的配置")
    print("然后将该配置应用到生产系统中")

def interactive_brightness_tuner():
    """交互式亮度调节器"""
    print("=== 交互式亮度调节器 ===")
    print("实时调节摄像头参数")
    print()
    
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return
    
    # 初始配置
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)  # 确保彩色模式
    
    # 参数范围
    auto_exposure = True
    exposure = 0
    brightness = 80
    contrast = 80
    gain = 80
    
    cv2.namedWindow('Brightness Tuner', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Brightness Tuner', 960, 540)
    
    print("控制说明:")
    print("  A - 切换自动/手动曝光")
    print("  +/- - 调整曝光 (手动模式)")
    print("  W/S - 调整亮度")
    print("  E/D - 调整对比度")
    print("  R/F - 调整增益")
    print("  SPACE - 保存当前帧")
    print("  Q - 退出")
    print()
    
    try:
        while True:
            # 应用当前配置
            if auto_exposure:
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
            else:
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
            
            cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness / 100.0)
            cap.set(cv2.CAP_PROP_CONTRAST, contrast / 100.0)
            cap.set(cv2.CAP_PROP_GAIN, gain)
            
            ret, frame = cap.read()
            
            if ret and frame is not None:
                avg_brightness = np.mean(frame)
                
                # 创建显示帧
                display_frame = cv2.resize(frame, (960, 540))
                
                # 添加信息
                mode_text = "自动曝光" if auto_exposure else f"手动曝光: {exposure}"
                cv2.putText(display_frame, mode_text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_frame, f"亮度: {brightness}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_frame, f"对比度: {contrast}", (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_frame, f"增益: {gain}", (10, 120),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_frame, f"图像亮度: {avg_brightness:.1f}", (10, 150),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                # 状态指示
                if avg_brightness < 10:
                    status = "太暗"
                    color = (0, 0, 255)
                elif avg_brightness > 200:
                    status = "太亮"
                    color = (0, 165, 255)
                else:
                    status = "正常"
                    color = (0, 255, 0)
                
                cv2.putText(display_frame, status, (10, 200),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                
                cv2.imshow('Brightness Tuner', display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:
                break
            elif key == ord('a'):
                auto_exposure = not auto_exposure
                print(f"切换到 {'自动' if auto_exposure else '手动'} 曝光")
            elif key == ord('+') or key == ord('='):
                if not auto_exposure:
                    exposure = min(10, exposure + 1)
                    print(f"曝光: {exposure}")
            elif key == ord('-'):
                if not auto_exposure:
                    exposure = max(-11, exposure - 1)
                    print(f"曝光: {exposure}")
            elif key == ord('w'):
                brightness = min(100, brightness + 5)
                print(f"亮度: {brightness}")
            elif key == ord('s'):
                brightness = max(0, brightness - 5)
                print(f"亮度: {brightness}")
            elif key == ord('e'):
                contrast = min(100, contrast + 5)
                print(f"对比度: {contrast}")
            elif key == ord('d'):
                contrast = max(0, contrast - 5)
                print(f"对比度: {contrast}")
            elif key == ord('r'):
                gain = min(100, gain + 5)
                print(f"增益: {gain}")
            elif key == ord('f'):
                gain = max(0, gain - 5)
                print(f"增益: {gain}")
            elif key == ord(' '):
                if ret and frame is not None:
                    filename = f"tuned_frame_{int(time.time())}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"保存帧: {filename}")
                    print(f"当前配置: 自动曝光={auto_exposure}, 曝光={exposure}, 亮度={brightness}, 对比度={contrast}, 增益={gain}")
    
    except KeyboardInterrupt:
        print("\n用户中断")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()

def main():
    """主函数"""
    print("选择测试模式:")
    print("1. 自动高亮度测试")
    print("2. 交互式亮度调节")
    
    try:
        choice = input("请输入选择 (1 或 2): ").strip()
        
        if choice == "1":
            bright_camera_test()
        elif choice == "2":
            interactive_brightness_tuner()
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