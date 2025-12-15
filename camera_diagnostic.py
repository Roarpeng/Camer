#!/usr/bin/env python3
"""
摄像头诊断工具
检查摄像头是否正常工作，调整曝光和其他参数
"""

import cv2
import numpy as np
import time
import sys

class CameraDiagnostic:
    """摄像头诊断器"""
    
    def __init__(self):
        self.cap = None
        self.current_camera_id = 0
        
        # 曝光参数范围 - 扩展到更高的曝光值
        self.exposure_values = [-11, -10, -9, -8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.current_exposure_idx = 11  # 默认0 (自动曝光)
        
        # 其他参数 - 提高默认亮度
        self.brightness = 80  # 提高到80
        self.contrast = 80    # 提高到80
        self.saturation = 80
        self.gain = 100       # 添加增益控制
    
    def test_camera_availability(self):
        """测试摄像头可用性"""
        print("=== 测试摄像头可用性 ===")
        
        available_cameras = []
        
        for camera_id in range(10):  # 测试0-9号摄像头
            print(f"测试摄像头 {camera_id}...", end=" ")
            
            try:
                cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        print(f"✓ 可用 (分辨率: {frame.shape})")
                        available_cameras.append(camera_id)
                    else:
                        print("✗ 无法读取帧")
                    cap.release()
                else:
                    print("✗ 无法打开")
            except Exception as e:
                print(f"✗ 错误: {e}")
            
            time.sleep(0.2)
        
        print(f"\n可用摄像头: {available_cameras}")
        return available_cameras
    
    def initialize_camera(self, camera_id):
        """初始化指定摄像头"""
        print(f"\n=== 初始化摄像头 {camera_id} ===")
        
        if self.cap is not None:
            self.cap.release()
        
        try:
            # 尝试不同的后端
            backends = [
                (cv2.CAP_DSHOW, "DirectShow"),
                (cv2.CAP_MSMF, "Media Foundation"),
                (cv2.CAP_ANY, "Any")
            ]
            
            for backend, name in backends:
                print(f"尝试 {name} 后端...", end=" ")
                
                cap = cv2.VideoCapture(camera_id, backend)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        print(f"✓ 成功 (分辨率: {frame.shape})")
                        self.cap = cap
                        self.current_camera_id = camera_id
                        return True
                    else:
                        print("✗ 无法读取帧")
                        cap.release()
                else:
                    print("✗ 无法打开")
                    if cap:
                        cap.release()
            
            print("所有后端都失败")
            return False
            
        except Exception as e:
            print(f"初始化错误: {e}")
            return False
    
    def configure_camera(self):
        """配置摄像头参数"""
        if self.cap is None:
            return False
        
        print("\n=== 配置摄像头参数 ===")
        
        try:
            # 设置分辨率
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # 设置缓冲区
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)  # 确保彩色模式
            
            # 设置帧率
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            # 设置曝光模式
            exposure = self.exposure_values[self.current_exposure_idx]
            
            if exposure == 0:
                # 使用自动曝光
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # 启用自动曝光
                print("使用自动曝光模式")
            else:
                # 使用手动曝光
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 禁用自动曝光
                self.cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
                print(f"使用手动曝光: {exposure}")
            
            # 设置其他参数
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness / 100.0)
            self.cap.set(cv2.CAP_PROP_CONTRAST, self.contrast / 100.0)
            self.cap.set(cv2.CAP_PROP_SATURATION, self.saturation / 100.0)
            
            # 尝试设置增益
            try:
                self.cap.set(cv2.CAP_PROP_GAIN, self.gain)
                print(f"增益: {self.gain}")
            except:
                pass
            
            print(f"曝光: {exposure}")
            print(f"亮度: {self.brightness}")
            print(f"对比度: {self.contrast}")
            print(f"饱和度: {self.saturation}")
            
            # 预热摄像头
            print("预热摄像头...")
            for i in range(10):
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    print(f"预热帧 {i+1}: ✓")
                else:
                    print(f"预热帧 {i+1}: ✗")
                time.sleep(0.1)
            
            return True
            
        except Exception as e:
            print(f"配置错误: {e}")
            return False
    
    def test_frame_capture(self):
        """测试帧捕获"""
        if self.cap is None:
            return False
        
        print("\n=== 测试帧捕获 ===")
        
        for i in range(5):
            ret, frame = self.cap.read()
            
            if ret and frame is not None:
                # 分析帧
                avg_brightness = np.mean(frame)
                max_brightness = np.max(frame)
                min_brightness = np.min(frame)
                
                print(f"帧 {i+1}: ✓ 亮度统计 - 平均:{avg_brightness:.1f}, 最大:{max_brightness}, 最小:{min_brightness}")
                
                # 保存测试图像
                filename = f"camera_test_{self.current_camera_id}_exposure_{self.exposure_values[self.current_exposure_idx]}_frame_{i+1}.jpg"
                cv2.imwrite(filename, frame)
                print(f"       保存: {filename}")
                
                if avg_brightness > 10:  # 如果平均亮度大于10，认为图像正常
                    print(f"       图像正常 (平均亮度: {avg_brightness:.1f})")
                    return True
                else:
                    print(f"       图像过暗 (平均亮度: {avg_brightness:.1f})")
            else:
                print(f"帧 {i+1}: ✗ 捕获失败")
            
            time.sleep(0.2)
        
        return False
    
    def adjust_exposure(self, direction):
        """调整曝光"""
        if direction > 0 and self.current_exposure_idx < len(self.exposure_values) - 1:
            self.current_exposure_idx += 1
        elif direction < 0 and self.current_exposure_idx > 0:
            self.current_exposure_idx -= 1
        
        if self.cap is not None:
            exposure = self.exposure_values[self.current_exposure_idx]
            self.cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
            print(f"曝光调整为: {exposure}")
    
    def run_interactive_test(self):
        """运行交互式测试"""
        print("=== 交互式摄像头测试 ===")
        print("控制说明:")
        print("  数字键 0-9: 切换摄像头")
        print("  +/-: 调整曝光")
        print("  SPACE: 捕获测试帧")
        print("  S: 保存当前帧")
        print("  Q: 退出")
        print()
        
        # 首先测试摄像头可用性
        available_cameras = self.test_camera_availability()
        
        if not available_cameras:
            print("[ERROR] 没有找到可用的摄像头")
            return False
        
        # 初始化第一个可用摄像头
        if not self.initialize_camera(available_cameras[0]):
            print("[ERROR] 无法初始化摄像头")
            return False
        
        if not self.configure_camera():
            print("[ERROR] 无法配置摄像头")
            return False
        
        cv2.namedWindow('Camera Diagnostic', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Camera Diagnostic', 960, 540)
        
        frame_count = 0
        
        try:
            while True:
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    frame_count += 1
                    
                    # 分析帧
                    avg_brightness = np.mean(frame)
                    
                    # 创建显示帧
                    display_frame = cv2.resize(frame, (960, 540))
                    
                    # 添加信息
                    cv2.putText(display_frame, f"Camera: {self.current_camera_id}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(display_frame, f"Exposure: {self.exposure_values[self.current_exposure_idx]}", (10, 70),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(display_frame, f"Brightness: {avg_brightness:.1f}", (10, 110),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(display_frame, f"Frame: {frame_count}", (10, 150),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    # 状态指示
                    if avg_brightness < 5:
                        status = "TOO DARK"
                        color = (0, 0, 255)  # 红色
                    elif avg_brightness > 200:
                        status = "TOO BRIGHT"
                        color = (0, 165, 255)  # 橙色
                    else:
                        status = "GOOD"
                        color = (0, 255, 0)  # 绿色
                    
                    cv2.putText(display_frame, status, (10, 200),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 3)
                    
                    cv2.imshow('Camera Diagnostic', display_frame)
                else:
                    # 显示黑屏和错误信息
                    black_frame = np.zeros((540, 960, 3), dtype=np.uint8)
                    cv2.putText(black_frame, "NO SIGNAL", (300, 270),
                               cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
                    cv2.imshow('Camera Diagnostic', black_frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q') or key == 27:
                    break
                elif key == ord(' '):
                    self.test_frame_capture()
                elif key == ord('s') and ret and frame is not None:
                    filename = f"manual_save_{int(time.time())}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"手动保存: {filename}")
                elif key == ord('+') or key == ord('='):
                    self.adjust_exposure(1)
                elif key == ord('-'):
                    self.adjust_exposure(-1)
                elif ord('0') <= key <= ord('9'):
                    camera_id = key - ord('0')
                    if camera_id in available_cameras:
                        if self.initialize_camera(camera_id):
                            self.configure_camera()
                        else:
                            print(f"无法切换到摄像头 {camera_id}")
        
        except KeyboardInterrupt:
            print("\n[INFO] 用户中断")
        
        finally:
            if self.cap is not None:
                self.cap.release()
            cv2.destroyAllWindows()
        
        return True
    
    def run_auto_diagnosis(self):
        """运行自动诊断"""
        print("=== 自动摄像头诊断 ===")
        
        # 测试摄像头可用性
        available_cameras = self.test_camera_availability()
        
        if not available_cameras:
            print("[ERROR] 没有找到可用的摄像头")
            return False
        
        success_count = 0
        
        for camera_id in available_cameras:
            print(f"\n--- 诊断摄像头 {camera_id} ---")
            
            if not self.initialize_camera(camera_id):
                print(f"摄像头 {camera_id}: 初始化失败")
                continue
            
            # 测试不同曝光值
            for exp_idx, exposure in enumerate(self.exposure_values):
                self.current_exposure_idx = exp_idx
                
                if not self.configure_camera():
                    print(f"摄像头 {camera_id} 曝光 {exposure}: 配置失败")
                    continue
                
                print(f"测试曝光 {exposure}...")
                
                # 等待摄像头稳定
                time.sleep(0.5)
                
                # 测试帧捕获
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    avg_brightness = np.mean(frame)
                    
                    filename = f"auto_test_camera{camera_id}_exp{exposure}.jpg"
                    cv2.imwrite(filename, frame)
                    
                    print(f"  曝光 {exposure}: 平均亮度 {avg_brightness:.1f} - 保存 {filename}")
                    
                    if 10 < avg_brightness < 200:  # 合适的亮度范围
                        print(f"  ✓ 摄像头 {camera_id} 在曝光 {exposure} 下工作正常")
                        success_count += 1
                        break
                else:
                    print(f"  曝光 {exposure}: 无法捕获帧")
            
            if self.cap is not None:
                self.cap.release()
                self.cap = None
        
        print(f"\n=== 诊断完成 ===")
        print(f"成功配置的摄像头数: {success_count}")
        
        return success_count > 0

def main():
    """主函数"""
    print("=== 摄像头诊断工具 ===")
    print("检查摄像头是否正常工作，调整曝光和其他参数")
    print()
    
    diagnostic = CameraDiagnostic()
    
    print("选择诊断模式:")
    print("1. 自动诊断 (测试所有摄像头和曝光值)")
    print("2. 交互式测试 (手动调整参数)")
    
    try:
        choice = input("请输入选择 (1 或 2): ").strip()
        
        if choice == "1":
            diagnostic.run_auto_diagnosis()
        elif choice == "2":
            diagnostic.run_interactive_test()
        else:
            print("[ERROR] 无效选择")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())