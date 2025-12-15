#!/usr/bin/env python3
"""
实时红色检测调参工具
可以动态调整HSV参数来找到最佳的红色检测范围
"""

import cv2
import numpy as np
import os

class RealtimeRedTuner:
    """实时红色检测调参器"""
    
    def __init__(self, mask_file: str = "mask.png"):
        self.mask_file = mask_file
        self.mask_image = None
        self.light_points_template = []
        
        # 初始HSV参数
        self.h_min1 = 0
        self.h_max1 = 25
        self.s_min1 = 30
        self.s_max1 = 255
        self.v_min1 = 30
        self.v_max1 = 255
        
        self.h_min2 = 155
        self.h_max2 = 180
        self.s_min2 = 30
        self.s_max2 = 255
        self.v_min2 = 30
        self.v_max2 = 255
        
        self._load_mask()
    
    def _load_mask(self):
        """加载mask图片"""
        if os.path.exists(self.mask_file):
            mask_img = cv2.imread(self.mask_file, cv2.IMREAD_GRAYSCALE)
            if mask_img is not None:
                # 缩放到1080p
                target_width, target_height = 1920, 1080
                if mask_img.shape != (target_height, target_width):
                    mask_img = cv2.resize(mask_img, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
                
                self.mask_image = mask_img
                
                # 识别光点
                binary_mask = (mask_img > 200).astype(np.uint8) * 255
                contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                self.light_points_template = []
                for i, contour in enumerate(contours):
                    area = cv2.contourArea(contour)
                    if area >= 10:
                        self.light_points_template.append((i, contour))
                
                print(f"[INFO] 加载mask成功，识别到 {len(self.light_points_template)} 个光点")
            else:
                print(f"[WARNING] 无法读取mask文件: {self.mask_file}")
        else:
            print(f"[WARNING] Mask文件不存在: {self.mask_file}")
    
    def create_trackbars(self):
        """创建调参滑动条"""
        cv2.namedWindow('Red Tuner Controls', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Red Tuner Controls', 400, 600)
        
        # 范围1的滑动条
        cv2.createTrackbar('H1_Min', 'Red Tuner Controls', self.h_min1, 179, lambda x: setattr(self, 'h_min1', x))
        cv2.createTrackbar('H1_Max', 'Red Tuner Controls', self.h_max1, 179, lambda x: setattr(self, 'h_max1', x))
        cv2.createTrackbar('S1_Min', 'Red Tuner Controls', self.s_min1, 255, lambda x: setattr(self, 's_min1', x))
        cv2.createTrackbar('S1_Max', 'Red Tuner Controls', self.s_max1, 255, lambda x: setattr(self, 's_max1', x))
        cv2.createTrackbar('V1_Min', 'Red Tuner Controls', self.v_min1, 255, lambda x: setattr(self, 'v_min1', x))
        cv2.createTrackbar('V1_Max', 'Red Tuner Controls', self.v_max1, 255, lambda x: setattr(self, 'v_max1', x))
        
        # 范围2的滑动条
        cv2.createTrackbar('H2_Min', 'Red Tuner Controls', self.h_min2, 179, lambda x: setattr(self, 'h_min2', x))
        cv2.createTrackbar('H2_Max', 'Red Tuner Controls', self.h_max2, 179, lambda x: setattr(self, 'h_max2', x))
        cv2.createTrackbar('S2_Min', 'Red Tuner Controls', self.s_min2, 255, lambda x: setattr(self, 's_min2', x))
        cv2.createTrackbar('S2_Max', 'Red Tuner Controls', self.s_max2, 255, lambda x: setattr(self, 's_max2', x))
        cv2.createTrackbar('V2_Min', 'Red Tuner Controls', self.v_min2, 255, lambda x: setattr(self, 'v_min2', x))
        cv2.createTrackbar('V2_Max', 'Red Tuner Controls', self.v_max2, 255, lambda x: setattr(self, 'v_max2', x))
    
    def detect_red_in_light_points(self, frame):
        """在光点区域检测红色"""
        if not self.light_points_template:
            return 0, []
        
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 创建红色mask
        lower1 = np.array([self.h_min1, self.s_min1, self.v_min1])
        upper1 = np.array([self.h_max1, self.s_max1, self.v_max1])
        lower2 = np.array([self.h_min2, self.s_min2, self.v_min2])
        upper2 = np.array([self.h_max2, self.s_max2, self.v_max2])
        
        mask1 = cv2.inRange(hsv, lower1, upper1)
        mask2 = cv2.inRange(hsv, lower2, upper2)
        red_mask = mask1 + mask2
        
        red_light_count = 0
        red_light_ids = []
        
        for light_id, contour in self.light_points_template:
            # 创建光点区域mask
            point_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            cv2.fillPoly(point_mask, [contour], 255)
            
            # 计算光点区域内的红色像素
            combined_mask = cv2.bitwise_and(red_mask, point_mask)
            red_pixels = np.sum(combined_mask > 0)
            total_pixels = np.sum(point_mask > 0)
            
            if total_pixels > 0:
                red_ratio = red_pixels / total_pixels
                if red_ratio > 0.1:  # 10%阈值
                    red_light_count += 1
                    red_light_ids.append(light_id)
        
        return red_light_count, red_light_ids
    
    def run_tuner(self):
        """运行调参器"""
        print("=== 实时红色检测调参工具 ===")
        print("使用滑动条调整HSV参数")
        print("控制说明:")
        print("  S - 保存当前参数到config.yaml")
        print("  R - 重置参数到默认值")
        print("  Q - 退出")
        print()
        
        # 初始化摄像头
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("[ERROR] 无法打开摄像头")
            return False
        
        # 配置摄像头
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, -5)
        
        # 创建窗口和滑动条
        cv2.namedWindow('Camera Feed', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Camera Feed', 960, 540)
        
        cv2.namedWindow('Red Detection', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Red Detection', 960, 540)
        
        self.create_trackbars()
        
        print("[INFO] 摄像头和界面初始化完成")
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # 检测红色光点
                red_count, red_ids = self.detect_red_in_light_points(frame)
                
                # 创建显示图像
                display_frame = frame.copy()
                
                # 如果有mask，应用mask
                if self.mask_image is not None:
                    # 将非mask区域变暗
                    black_mask = self.mask_image <= 200
                    display_frame[black_mask] = display_frame[black_mask] // 3
                    
                    # 绘制光点轮廓
                    for light_id, contour in self.light_points_template:
                        color = (0, 0, 255) if light_id in red_ids else (128, 128, 128)
                        cv2.drawContours(display_frame, [contour], -1, color, 2)
                        
                        # 添加光点ID
                        M = cv2.moments(contour)
                        if M["m00"] != 0:
                            center_x = int(M["m10"] / M["m00"])
                            center_y = int(M["m01"] / M["m00"])
                            cv2.putText(display_frame, str(light_id), (center_x-10, center_y+5),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # 添加信息文本
                cv2.putText(display_frame, f"Red Light Points: {red_count}/{len(self.light_points_template)}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                if red_ids:
                    cv2.putText(display_frame, f"Red IDs: {red_ids}", 
                               (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # 显示当前参数
                param_text = f"Range1: H({self.h_min1}-{self.h_max1}) S({self.s_min1}-{self.s_max1}) V({self.v_min1}-{self.v_max1})"
                cv2.putText(display_frame, param_text, (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                param_text2 = f"Range2: H({self.h_min2}-{self.h_max2}) S({self.s_min2}-{self.s_max2}) V({self.v_min2}-{self.v_max2})"
                cv2.putText(display_frame, param_text2, (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # 显示图像
                display_resized = cv2.resize(display_frame, (960, 540))
                cv2.imshow('Camera Feed', display_resized)
                
                # 创建红色检测结果图像
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                lower1 = np.array([self.h_min1, self.s_min1, self.v_min1])
                upper1 = np.array([self.h_max1, self.s_max1, self.v_max1])
                lower2 = np.array([self.h_min2, self.s_min2, self.v_min2])
                upper2 = np.array([self.h_max2, self.s_max2, self.v_max2])
                
                mask1 = cv2.inRange(hsv, lower1, upper1)
                mask2 = cv2.inRange(hsv, lower2, upper2)
                red_mask = mask1 + mask2
                
                red_result = cv2.bitwise_and(frame, frame, mask=red_mask)
                red_result_resized = cv2.resize(red_result, (960, 540))
                cv2.imshow('Red Detection', red_result_resized)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    break
                elif key == ord('s'):
                    self.save_parameters()
                elif key == ord('r'):
                    self.reset_parameters()
        
        except KeyboardInterrupt:
            print("\n[INFO] 用户中断")
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        return True
    
    def save_parameters(self):
        """保存参数到配置文件"""
        print("\n=== 保存参数 ===")
        print(f"范围1: H({self.h_min1}-{self.h_max1}) S({self.s_min1}-{self.s_max1}) V({self.v_min1}-{self.v_max1})")
        print(f"范围2: H({self.h_min2}-{self.h_max2}) S({self.s_min2}-{self.s_max2}) V({self.v_min2}-{self.v_max2})")
        
        # 保存到文本文件
        with open("red_detection_params.txt", "w", encoding="utf-8") as f:
            f.write("# 红色检测参数\n")
            f.write(f"# 范围1\n")
            f.write(f"red_hsv_lower1 = np.array([{self.h_min1}, {self.s_min1}, {self.v_min1}])\n")
            f.write(f"red_hsv_upper1 = np.array([{self.h_max1}, {self.s_max1}, {self.v_max1}])\n")
            f.write(f"# 范围2\n")
            f.write(f"red_hsv_lower2 = np.array([{self.h_min2}, {self.s_min2}, {self.v_min2}])\n")
            f.write(f"red_hsv_upper2 = np.array([{self.h_max2}, {self.s_max2}, {self.v_max2}])\n")
        
        print("参数已保存到 red_detection_params.txt")
    
    def reset_parameters(self):
        """重置参数到默认值"""
        self.h_min1 = 0
        self.h_max1 = 25
        self.s_min1 = 30
        self.s_max1 = 255
        self.v_min1 = 30
        self.v_max1 = 255
        
        self.h_min2 = 155
        self.h_max2 = 180
        self.s_min2 = 30
        self.s_max2 = 255
        self.v_min2 = 30
        self.v_max2 = 255
        
        # 更新滑动条
        cv2.setTrackbarPos('H1_Min', 'Red Tuner Controls', self.h_min1)
        cv2.setTrackbarPos('H1_Max', 'Red Tuner Controls', self.h_max1)
        cv2.setTrackbarPos('S1_Min', 'Red Tuner Controls', self.s_min1)
        cv2.setTrackbarPos('S1_Max', 'Red Tuner Controls', self.s_max1)
        cv2.setTrackbarPos('V1_Min', 'Red Tuner Controls', self.v_min1)
        cv2.setTrackbarPos('V1_Max', 'Red Tuner Controls', self.v_max1)
        
        cv2.setTrackbarPos('H2_Min', 'Red Tuner Controls', self.h_min2)
        cv2.setTrackbarPos('H2_Max', 'Red Tuner Controls', self.h_max2)
        cv2.setTrackbarPos('S2_Min', 'Red Tuner Controls', self.s_min2)
        cv2.setTrackbarPos('S2_Max', 'Red Tuner Controls', self.s_max2)
        cv2.setTrackbarPos('V2_Min', 'Red Tuner Controls', self.v_min2)
        cv2.setTrackbarPos('V2_Max', 'Red Tuner Controls', self.v_max2)
        
        print("[INFO] 参数已重置到默认值")

def main():
    """主函数"""
    try:
        tuner = RealtimeRedTuner()
        tuner.run_tuner()
        return 0
        
    except Exception as e:
        print(f"[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())