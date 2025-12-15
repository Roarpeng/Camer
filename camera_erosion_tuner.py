#!/usr/bin/env python3
"""
摄像头腐蚀参数调试工具 - 逐个摄像头调试腐蚀值
"""

import cv2
import numpy as np
import time
import sys
import yaml
from mqtt_camera_monitoring.config import ConfigManager
from mqtt_camera_monitoring.light_detector import RedLightDetector

class ErosionTuner:
    def __init__(self):
        self.config_manager = ConfigManager('config.yaml')
        self.config = self.config_manager.load_config()
        self.detector = RedLightDetector(self.config.red_light_detection)
        
        # 腐蚀参数
        self.erosion_kernel = 2
        self.erosion_iterations = 1
        
        # HSV参数
        self.lower_red_hsv = [0, 150, 150]
        self.upper_red_hsv = [6, 255, 255]
        self.lower_red_hsv_2 = [174, 150, 150]
        self.upper_red_hsv_2 = [180, 255, 255]
        
        # 摄像头配置
        self.camera_configs = {}
        
    def test_single_camera(self, camera_id):
        """测试单个摄像头并调试腐蚀参数"""
        print(f"\n=== 调试摄像头 {camera_id} ===")
        
        cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print(f"无法打开摄像头 {camera_id}")
            return False
        
        # 配置摄像头 - 使用分辨率匹配mask (1280x720)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, self.config.cameras.exposure)
        cap.set(cv2.CAP_PROP_BRIGHTNESS, self.config.cameras.brightness / 100.0)
        
        # 预热
        for _ in range(5):
            cap.read()
            time.sleep(0.1)
        
        print("控制说明:")
        print("  1/2 - 调整腐蚀核大小")
        print("  3/4 - 调整腐蚀迭代次数")
        print("  a/z - 调整HSV下限H值")
        print("  w/x - 调整HSV下限S值")
        print("  e/c - 调整HSV下限V值")
        print("  r/v - 调整HSV上限H值")
        print("  s - 保存当前设置")
        print("  n - 下一个摄像头")
        print("  q - 退出")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # 使用当前腐蚀参数检测
            detection = self._detect_with_erosion(frame)
            
            # 显示结果
            display_frame = frame.copy()
            cv2.putText(display_frame, f"Camera {camera_id}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(display_frame, f"Count: {detection.count}", (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(display_frame, f"Erosion K: {self.erosion_kernel}", (10, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(display_frame, f"Erosion I: {self.erosion_iterations}", (10, 140), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(display_frame, f"HSV L: {self.lower_red_hsv}", (10, 170), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(display_frame, f"HSV U: {self.upper_red_hsv}", (10, 190), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            # 绘制检测框
            for x, y, w, h in detection.bounding_boxes:
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            cv2.imshow(f"Camera {camera_id} Erosion Tuning", display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return False
            elif key == ord('n'):
                # 保存当前设置
                self.camera_configs[camera_id] = {
                    'erosion_kernel': self.erosion_kernel,
                    'erosion_iterations': self.erosion_iterations,
                    'lower_red_hsv': self.lower_red_hsv.copy(),
                    'upper_red_hsv': self.upper_red_hsv.copy(),
                    'lower_red_hsv_2': self.lower_red_hsv_2.copy(),
                    'upper_red_hsv_2': self.upper_red_hsv_2.copy()
                }
                print(f"摄像头 {camera_id} 设置已保存")
                break
            elif key == ord('s'):
                self.camera_configs[camera_id] = {
                    'erosion_kernel': self.erosion_kernel,
                    'erosion_iterations': self.erosion_iterations,
                    'lower_red_hsv': self.lower_red_hsv.copy(),
                    'upper_red_hsv': self.upper_red_hsv.copy(),
                    'lower_red_hsv_2': self.lower_red_hsv_2.copy(),
                    'upper_red_hsv_2': self.upper_red_hsv_2.copy()
                }
                print(f"摄像头 {camera_id} 设置已保存")
            elif key == ord('1'):
                if self.erosion_kernel > 1:
                    self.erosion_kernel -= 1
                    print(f"腐蚀核大小: {self.erosion_kernel}")
            elif key == ord('2'):
                if self.erosion_kernel < 10:
                    self.erosion_kernel += 1
                    print(f"腐蚀核大小: {self.erosion_kernel}")
            elif key == ord('3'):
                if self.erosion_iterations > 1:
                    self.erosion_iterations -= 1
                    print(f"腐蚀迭代次数: {self.erosion_iterations}")
            elif key == ord('4'):
                if self.erosion_iterations < 5:
                    self.erosion_iterations += 1
                    print(f"腐蚀迭代次数: {self.erosion_iterations}")
            # HSV调整
            elif key == ord('a'):
                if self.lower_red_hsv[0] > 0:
                    self.lower_red_hsv[0] -= 1
                    print(f"HSV下限H: {self.lower_red_hsv[0]}")
            elif key == ord('z'):
                if self.lower_red_hsv[0] < 10:
                    self.lower_red_hsv[0] += 1
                    print(f"HSV下限H: {self.lower_red_hsv[0]}")
            elif key == ord('w'):
                if self.lower_red_hsv[1] > 50:
                    self.lower_red_hsv[1] -= 10
                    print(f"HSV下限S: {self.lower_red_hsv[1]}")
            elif key == ord('x'):
                if self.lower_red_hsv[1] < 255:
                    self.lower_red_hsv[1] += 10
                    print(f"HSV下限S: {self.lower_red_hsv[1]}")
            elif key == ord('e'):
                if self.lower_red_hsv[2] > 50:
                    self.lower_red_hsv[2] -= 10
                    print(f"HSV下限V: {self.lower_red_hsv[2]}")
            elif key == ord('c'):
                if self.lower_red_hsv[2] < 255:
                    self.lower_red_hsv[2] += 10
                    print(f"HSV下限V: {self.lower_red_hsv[2]}")
            elif key == ord('r'):
                if self.upper_red_hsv[0] > 0:
                    self.upper_red_hsv[0] -= 1
                    print(f"HSV上限H: {self.upper_red_hsv[0]}")
            elif key == ord('v'):
                if self.upper_red_hsv[0] < 15:
                    self.upper_red_hsv[0] += 1
                    print(f"HSV上限H: {self.upper_red_hsv[0]}")
        
        cap.release()
        cv2.destroyAllWindows()
        return True
    
    def _detect_with_erosion(self, frame):
        """使用当前腐蚀参数进行检测"""
        # 预处理
        blur_kernel = getattr(self.config.red_light_detection, 'gaussian_blur_kernel', 5)
        blurred = cv2.GaussianBlur(frame, (blur_kernel, blur_kernel), 0)
        
        # HSV转换
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        
        # 亮度过滤
        brightness_threshold = getattr(self.config.red_light_detection, 'brightness_threshold', 200)
        brightness_mask = hsv[:, :, 2] > brightness_threshold
        
        # 红色掩码 - 使用当前HSV参数
        lower_red_1 = np.array(self.lower_red_hsv, dtype=np.uint8)
        upper_red_1 = np.array(self.upper_red_hsv, dtype=np.uint8)
        lower_red_2 = np.array(self.lower_red_hsv_2, dtype=np.uint8)
        upper_red_2 = np.array(self.upper_red_hsv_2, dtype=np.uint8)
        
        mask1 = cv2.inRange(hsv, lower_red_1, upper_red_1)
        mask2 = cv2.inRange(hsv, lower_red_2, upper_red_2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        red_mask = cv2.bitwise_and(red_mask, brightness_mask.astype(np.uint8) * 255)
        
        # 形态学操作
        morph_kernel_size = getattr(self.config.red_light_detection, 'morphology_kernel', 3)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph_kernel_size, morph_kernel_size))
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel, iterations=2)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # 应用当前腐蚀参数
        erosion_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.erosion_kernel, self.erosion_kernel))
        red_mask = cv2.erode(red_mask, erosion_kernel, iterations=self.erosion_iterations)
        
        # 查找轮廓
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 过滤轮廓
        valid_contours = []
        bounding_boxes = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self.config.red_light_detection.min_contour_area:
                valid_contours.append(contour)
                x, y, w, h = cv2.boundingRect(contour)
                bounding_boxes.append((x, y, w, h))
        
        # 创建检测结果
        from mqtt_camera_monitoring.light_detector import RedLightDetection
        return RedLightDetection(
            count=len(valid_contours),
            total_area=sum(cv2.contourArea(c) for c in valid_contours),
            bounding_boxes=bounding_boxes,
            contours=valid_contours,
            timestamp=time.time()
        )
    
    def save_config(self):
        """保存配置到文件"""
        if not self.camera_configs:
            print("没有配置需要保存")
            return
        
        # 读取当前配置
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # 计算平均参数
        avg_kernel = sum(cfg['erosion_kernel'] for cfg in self.camera_configs.values()) / len(self.camera_configs)
        avg_iterations = sum(cfg['erosion_iterations'] for cfg in self.camera_configs.values()) / len(self.camera_configs)
        
        # 计算平均HSV参数
        avg_lower_hsv = [
            int(sum(cfg['lower_red_hsv'][i] for cfg in self.camera_configs.values()) / len(self.camera_configs))
            for i in range(3)
        ]
        avg_upper_hsv = [
            int(sum(cfg['upper_red_hsv'][i] for cfg in self.camera_configs.values()) / len(self.camera_configs))
            for i in range(3)
        ]
        avg_lower_hsv_2 = [
            int(sum(cfg['lower_red_hsv_2'][i] for cfg in self.camera_configs.values()) / len(self.camera_configs))
            for i in range(3)
        ]
        avg_upper_hsv_2 = [
            int(sum(cfg['upper_red_hsv_2'][i] for cfg in self.camera_configs.values()) / len(self.camera_configs))
            for i in range(3)
        ]
        
        # 更新配置
        config_data['red_light_detection']['erosion_kernel'] = int(round(avg_kernel))
        config_data['red_light_detection']['erosion_iterations'] = int(round(avg_iterations))
        config_data['red_light_detection']['lower_red_hsv'] = avg_lower_hsv
        config_data['red_light_detection']['upper_red_hsv'] = avg_upper_hsv
        config_data['red_light_detection']['lower_red_hsv_2'] = avg_lower_hsv_2
        config_data['red_light_detection']['upper_red_hsv_2'] = avg_upper_hsv_2
        
        # 保存配置
        with open('config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        
        print(f"\n配置已保存:")
        print(f"  平均腐蚀核大小: {int(round(avg_kernel))}")
        print(f"  平均腐蚀迭代次数: {int(round(avg_iterations))}")
        print(f"  平均HSV下限: {avg_lower_hsv}")
        print(f"  平均HSV上限: {avg_upper_hsv}")
        print(f"  平均HSV下限2: {avg_lower_hsv_2}")
        print(f"  平均HSV上限2: {avg_upper_hsv_2}")
        
        # 保存详细配置
        with open('camera_detection_configs.txt', 'w') as f:
            f.write("摄像头检测参数配置:\n")
            for camera_id, cfg in self.camera_configs.items():
                f.write(f"摄像头 {camera_id}:\n")
                f.write(f"  腐蚀核大小: {cfg['erosion_kernel']}\n")
                f.write(f"  腐蚀迭代次数: {cfg['erosion_iterations']}\n")
                f.write(f"  HSV下限: {cfg['lower_red_hsv']}\n")
                f.write(f"  HSV上限: {cfg['upper_red_hsv']}\n")
                f.write(f"  HSV下限2: {cfg['lower_red_hsv_2']}\n")
                f.write(f"  HSV上限2: {cfg['upper_red_hsv_2']}\n\n")
        
        print("详细配置已保存到 camera_erosion_configs.txt")
    
    def run(self):
        """运行调试工具"""
        print("=== 摄像头腐蚀参数调试工具 ===")
        print("将逐个调试6个摄像头的腐蚀参数")
        print()
        
        for camera_id in range(6):
            if not self.test_single_camera(camera_id):
                break
            time.sleep(0.5)
        
        self.save_config()

def main():
    tuner = ErosionTuner()
    tuner.run()

if __name__ == "__main__":
    main()