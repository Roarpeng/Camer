#!/usr/bin/env python3
"""
综合基线测试
比较不同方法的基线建立效果
"""

import cv2
import numpy as np
import time
import logging
import sys
import os
from typing import List, Tuple, Dict
from dataclasses import dataclass

@dataclass
class LightPoint:
    """光点信息"""
    id: int
    center_x: int
    center_y: int
    area: int
    contour: np.ndarray

@dataclass
class TestResult:
    """测试结果"""
    method_name: str
    success: bool
    red_count: int
    total_count: int
    red_light_ids: List[int]
    execution_time: float
    error_message: str = ""

class ComprehensiveBaselineTester:
    """综合基线测试器"""
    
    def __init__(self, mask_file: str = "mask.png"):
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('comprehensive_baseline_test.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.mask_file = mask_file
        self.mask_image = None
        self.light_points_template = []
        
        # 红色检测参数
        self.red_hsv_lower1 = np.array([0, 30, 30])
        self.red_hsv_upper1 = np.array([25, 255, 255])
        self.red_hsv_lower2 = np.array([155, 30, 30])
        self.red_hsv_upper2 = np.array([180, 255, 255])
        
        if not self._load_mask():
            raise ValueError(f"无法加载mask文件: {mask_file}")
    
    def _load_mask(self) -> bool:
        """加载mask图片"""
        if not os.path.exists(self.mask_file):
            self.logger.error(f"Mask文件不存在: {self.mask_file}")
            return False
        
        mask_img = cv2.imread(self.mask_file, cv2.IMREAD_GRAYSCALE)
        if mask_img is None:
            self.logger.error(f"无法读取mask文件: {self.mask_file}")
            return False
        
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
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    center_x = int(M["m10"] / M["m00"])
                    center_y = int(M["m01"] / M["m00"])
                else:
                    x, y, w, h = cv2.boundingRect(contour)
                    center_x = x + w // 2
                    center_y = y + h // 2
                
                light_point = LightPoint(
                    id=i,
                    center_x=center_x,
                    center_y=center_y,
                    area=int(area),
                    contour=contour
                )
                self.light_points_template.append(light_point)
        
        self.logger.info(f"识别到 {len(self.light_points_template)} 个光点区域")
        return len(self.light_points_template) > 0
    
    def _is_red_color(self, bgr_color: Tuple[int, int, int]) -> bool:
        """判断BGR颜色是否为红色"""
        bgr_pixel = np.uint8([[bgr_color]])
        hsv_pixel = cv2.cvtColor(bgr_pixel, cv2.COLOR_BGR2HSV)[0][0]
        
        in_range1 = (self.red_hsv_lower1[0] <= hsv_pixel[0] <= self.red_hsv_upper1[0] and
                     self.red_hsv_lower1[1] <= hsv_pixel[1] <= self.red_hsv_upper1[1] and
                     self.red_hsv_lower1[2] <= hsv_pixel[2] <= self.red_hsv_upper1[2])
        
        in_range2 = (self.red_hsv_lower2[0] <= hsv_pixel[0] <= self.red_hsv_upper2[0] and
                     self.red_hsv_lower2[1] <= hsv_pixel[1] <= self.red_hsv_upper2[1] and
                     self.red_hsv_lower2[2] <= hsv_pixel[2] <= self.red_hsv_upper2[2])
        
        return in_range1 or in_range2
    
    def _check_light_point_red(self, frame: np.ndarray, light_point: LightPoint) -> Tuple[bool, float]:
        """检查光点区域是否为红色"""
        point_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.fillPoly(point_mask, [light_point.contour], 255)
        
        masked_pixels = frame[point_mask > 0]
        if len(masked_pixels) == 0:
            return False, 0.0
        
        red_pixel_count = 0
        total_pixels = len(masked_pixels)
        sample_size = min(100, total_pixels)
        step = max(1, total_pixels // sample_size)
        
        for i in range(0, total_pixels, step):
            bgr_color = tuple(masked_pixels[i].astype(int))
            if self._is_red_color(bgr_color):
                red_pixel_count += 1
        
        red_ratio = red_pixel_count / (total_pixels // step)
        return red_ratio > 0.1, red_ratio
    
    def _setup_camera(self, camera_id: int) -> cv2.VideoCapture:
        """设置摄像头"""
        cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return None
        
        # 配置摄像头
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)  # 确保彩色模式
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, -5)
        cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.8)
        cap.set(cv2.CAP_PROP_CONTRAST, 0.85)
        cap.set(cv2.CAP_PROP_SATURATION, 0.8)
            cap.set(cv2.CAP_PROP_GAIN, 80)
        
        # 预热
        for _ in range(5):
            ret, frame = cap.read()
            if ret and frame is not None:
                break
            time.sleep(0.1)
        
        return cap
    
    def test_method_1_immediate(self, camera_id: int = 0) -> TestResult:
        """方法1: 立即检测（类似test_red_detection.py）"""
        start_time = time.time()
        
        try:
            cap = self._setup_camera(camera_id)
            if cap is None:
                return TestResult("立即检测", False, 0, len(self.light_points_template), [], 
                                time.time() - start_time, "无法打开摄像头")
            
            # 立即捕获和检测
            ret, frame = cap.read()
            if not ret or frame is None:
                cap.release()
                return TestResult("立即检测", False, 0, len(self.light_points_template), [], 
                                time.time() - start_time, "无法捕获帧")
            
            # 检测红色光点
            red_light_ids = []
            for light_point in self.light_points_template:
                is_red, _ = self._check_light_point_red(frame, light_point)
                if is_red:
                    red_light_ids.append(light_point.id)
            
            cap.release()
            execution_time = time.time() - start_time
            
            return TestResult("立即检测", len(red_light_ids) > 0, len(red_light_ids), 
                            len(self.light_points_template), red_light_ids, execution_time)
            
        except Exception as e:
            return TestResult("立即检测", False, 0, len(self.light_points_template), [], 
                            time.time() - start_time, str(e))
    
    def test_method_2_with_delay(self, camera_id: int = 0) -> TestResult:
        """方法2: 模拟MQTT延迟后检测（类似生产环境）"""
        start_time = time.time()
        
        try:
            cap = self._setup_camera(camera_id)
            if cap is None:
                return TestResult("延迟检测", False, 0, len(self.light_points_template), [], 
                                time.time() - start_time, "无法打开摄像头")
            
            # 模拟MQTT触发后的0.1秒延迟
            time.sleep(0.1)
            
            # 捕获和检测
            ret, frame = cap.read()
            if not ret or frame is None:
                cap.release()
                return TestResult("延迟检测", False, 0, len(self.light_points_template), [], 
                                time.time() - start_time, "无法捕获帧")
            
            # 检测红色光点
            red_light_ids = []
            for light_point in self.light_points_template:
                is_red, _ = self._check_light_point_red(frame, light_point)
                if is_red:
                    red_light_ids.append(light_point.id)
            
            cap.release()
            execution_time = time.time() - start_time
            
            return TestResult("延迟检测", len(red_light_ids) > 0, len(red_light_ids), 
                            len(self.light_points_template), red_light_ids, execution_time)
            
        except Exception as e:
            return TestResult("延迟检测", False, 0, len(self.light_points_template), [], 
                            time.time() - start_time, str(e))
    
    def test_method_3_multiple_frames(self, camera_id: int = 0) -> TestResult:
        """方法3: 多帧检测取最佳结果"""
        start_time = time.time()
        
        try:
            cap = self._setup_camera(camera_id)
            if cap is None:
                return TestResult("多帧检测", False, 0, len(self.light_points_template), [], 
                                time.time() - start_time, "无法打开摄像头")
            
            # 捕获多帧并选择最佳结果
            best_red_count = 0
            best_red_ids = []
            
            for frame_num in range(5):
                ret, frame = cap.read()
                if not ret or frame is None:
                    continue
                
                # 检测红色光点
                red_light_ids = []
                for light_point in self.light_points_template:
                    is_red, _ = self._check_light_point_red(frame, light_point)
                    if is_red:
                        red_light_ids.append(light_point.id)
                
                # 保留最佳结果
                if len(red_light_ids) > best_red_count:
                    best_red_count = len(red_light_ids)
                    best_red_ids = red_light_ids
                
                time.sleep(0.05)  # 50ms间隔
            
            cap.release()
            execution_time = time.time() - start_time
            
            return TestResult("多帧检测", best_red_count > 0, best_red_count, 
                            len(self.light_points_template), best_red_ids, execution_time)
            
        except Exception as e:
            return TestResult("多帧检测", False, 0, len(self.light_points_template), [], 
                            time.time() - start_time, str(e))
    
    def test_method_4_enhanced_params(self, camera_id: int = 0) -> TestResult:
        """方法4: 增强检测参数"""
        start_time = time.time()
        
        try:
            cap = self._setup_camera(camera_id)
            if cap is None:
                return TestResult("增强参数", False, 0, len(self.light_points_template), [], 
                                time.time() - start_time, "无法打开摄像头")
            
            # 使用更宽松的红色检测参数
            original_lower1 = self.red_hsv_lower1.copy()
            original_upper1 = self.red_hsv_upper1.copy()
            original_lower2 = self.red_hsv_lower2.copy()
            original_upper2 = self.red_hsv_upper2.copy()
            
            # 更宽松的参数
            self.red_hsv_lower1 = np.array([0, 20, 20])
            self.red_hsv_upper1 = np.array([30, 255, 255])
            self.red_hsv_lower2 = np.array([150, 20, 20])
            self.red_hsv_upper2 = np.array([180, 255, 255])
            
            # 捕获和检测
            ret, frame = cap.read()
            if not ret or frame is None:
                cap.release()
                # 恢复原参数
                self.red_hsv_lower1 = original_lower1
                self.red_hsv_upper1 = original_upper1
                self.red_hsv_lower2 = original_lower2
                self.red_hsv_upper2 = original_upper2
                return TestResult("增强参数", False, 0, len(self.light_points_template), [], 
                                time.time() - start_time, "无法捕获帧")
            
            # 检测红色光点
            red_light_ids = []
            for light_point in self.light_points_template:
                is_red, _ = self._check_light_point_red(frame, light_point)
                if is_red:
                    red_light_ids.append(light_point.id)
            
            # 恢复原参数
            self.red_hsv_lower1 = original_lower1
            self.red_hsv_upper1 = original_upper1
            self.red_hsv_lower2 = original_lower2
            self.red_hsv_upper2 = original_upper2
            
            cap.release()
            execution_time = time.time() - start_time
            
            return TestResult("增强参数", len(red_light_ids) > 0, len(red_light_ids), 
                            len(self.light_points_template), red_light_ids, execution_time)
            
        except Exception as e:
            return TestResult("增强参数", False, 0, len(self.light_points_template), [], 
                            time.time() - start_time, str(e))
    
    def run_comprehensive_test(self, camera_id: int = 0) -> List[TestResult]:
        """运行综合测试"""
        self.logger.info(f"=== 开始综合基线测试 (摄像头 {camera_id}) ===")
        
        results = []
        
        # 测试方法1: 立即检测
        self.logger.info("测试方法1: 立即检测...")
        result1 = self.test_method_1_immediate(camera_id)
        results.append(result1)
        time.sleep(1)
        
        # 测试方法2: 延迟检测
        self.logger.info("测试方法2: 延迟检测...")
        result2 = self.test_method_2_with_delay(camera_id)
        results.append(result2)
        time.sleep(1)
        
        # 测试方法3: 多帧检测
        self.logger.info("测试方法3: 多帧检测...")
        result3 = self.test_method_3_multiple_frames(camera_id)
        results.append(result3)
        time.sleep(1)
        
        # 测试方法4: 增强参数
        self.logger.info("测试方法4: 增强参数...")
        result4 = self.test_method_4_enhanced_params(camera_id)
        results.append(result4)
        
        return results
    
    def print_results(self, results: List[TestResult]) -> None:
        """打印测试结果"""
        self.logger.info("\n=== 综合测试结果 ===")
        
        for result in results:
            status = "成功" if result.success else "失败"
            self.logger.info(f"{result.method_name:8s}: {status:2s} | "
                           f"红色光点: {result.red_count:2d}/{result.total_count:2d} | "
                           f"耗时: {result.execution_time:.3f}s")
            
            if result.success and result.red_light_ids:
                self.logger.info(f"         红色光点ID: {result.red_light_ids}")
            
            if not result.success and result.error_message:
                self.logger.info(f"         错误: {result.error_message}")
        
        # 统计
        success_count = sum(1 for r in results if r.success)
        self.logger.info(f"\n成功方法数: {success_count}/{len(results)}")
        
        if success_count > 0:
            successful_results = [r for r in results if r.success]
            avg_red_count = sum(r.red_count for r in successful_results) / len(successful_results)
            self.logger.info(f"平均红色光点数: {avg_red_count:.1f}")

def main():
    """主函数"""
    print("=== 综合基线测试 ===")
    print("比较不同方法的基线建立效果")
    print()
    
    if not os.path.exists("mask.png"):
        print("[ERROR] 未找到mask.png文件")
        return 1
    
    try:
        tester = ComprehensiveBaselineTester()
        
        camera_id = 0
        results = tester.run_comprehensive_test(camera_id)
        tester.print_results(results)
        
        print(f"\n详细日志已保存到 comprehensive_baseline_test.log")
        return 0
        
    except Exception as e:
        print(f"[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())