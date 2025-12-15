#!/usr/bin/env python3
"""
测试增强的红光检测算法
"""

import cv2
import numpy as np
import time
import logging
import sys
from mqtt_camera_monitoring.config import ConfigManager
from mqtt_camera_monitoring.light_detector import RedLightDetector

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def test_camera_detection(camera_id: int, detector: RedLightDetector, duration: int = 10):
    """测试单个摄像头的检测效果"""
    print(f"\n=== 测试摄像头 {camera_id} ===")
    
    # 初始化摄像头
    cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"❌ 摄像头 {camera_id} 无法打开")
        return False
    
    # 配置摄像头
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, -6)
    
    print(f"✅ 摄像头 {camera_id} 初始化成功")
    
    # 预热
    for _ in range(5):
        ret, frame = cap.read()
        if not ret:
            print(f"❌ 摄像头 {camera_id} 无法读取帧")
            cap.release()
            return False
    
    print(f"开始 {duration} 秒检测测试...")
    
    detection_results = []
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # 执行检测
            detection = detector.detect_red_lights(frame)
            detection_results.append(detection.count)
            
            # 每秒输出一次结果
            elapsed = time.time() - start_time
            if len(detection_results) % 10 == 0:  # 假设约10 FPS
                avg_count = np.mean(detection_results[-10:]) if len(detection_results) >= 10 else np.mean(detection_results)
                print(f"  {elapsed:.1f}s: 检测到 {detection.count} 个红光 (平均: {avg_count:.1f})")
            
            time.sleep(0.1)  # 10 FPS
    
    except KeyboardInterrupt:
        print("用户中断测试")
    
    finally:
        cap.release()
    
    # 统计结果
    if detection_results:
        total_detections = len(detection_results)
        non_zero_detections = len([x for x in detection_results if x > 0])
        avg_count = np.mean(detection_results)
        max_count = max(detection_results)
        
        print(f"\n📊 摄像头 {camera_id} 检测统计:")
        print(f"  总检测次数: {total_detections}")
        print(f"  检测到红光次数: {non_zero_detections} ({non_zero_detections/total_detections*100:.1f}%)")
        print(f"  平均红光数量: {avg_count:.2f}")
        print(f"  最大红光数量: {max_count}")
        
        return non_zero_detections > 0
    
    return False

def main():
    """主函数"""
    print("=== 增强红光检测算法测试 ===")
    print("测试所有可用摄像头的检测效果")
    print("按 Ctrl+C 可以提前结束单个摄像头的测试")
    print()
    
    setup_logging()
    
    try:
        # 加载配置
        config_manager = ConfigManager("config.yaml")
        config = config_manager.load_config()
        
        # 创建检测器
        detector = RedLightDetector(config.red_light_detection)
        
        print("🔧 检测参数:")
        print(f"  HSV范围1: {config.red_light_detection.lower_red_hsv} - {config.red_light_detection.upper_red_hsv}")
        print(f"  HSV范围2: {config.red_light_detection.lower_red_hsv_2} - {config.red_light_detection.upper_red_hsv_2}")
        print(f"  亮度阈值: {config.red_light_detection.brightness_threshold}")
        print(f"  最小面积: {config.red_light_detection.min_contour_area}")
        print(f"  腐蚀迭代: {config.red_light_detection.erosion_iterations}")
        
        # 测试所有摄像头
        successful_cameras = []
        
        for camera_id in range(6):  # 测试6个摄像头
            try:
                success = test_camera_detection(camera_id, detector, duration=5)
                if success:
                    successful_cameras.append(camera_id)
                    print(f"✅ 摄像头 {camera_id} 检测正常")
                else:
                    print(f"⚠️  摄像头 {camera_id} 未检测到红光")
                
            except Exception as e:
                print(f"❌ 摄像头 {camera_id} 测试失败: {e}")
            
            print("-" * 50)
        
        # 总结
        print(f"\n🎯 测试总结:")
        print(f"  成功检测红光的摄像头: {successful_cameras}")
        print(f"  检测成功率: {len(successful_cameras)}/6 ({len(successful_cameras)/6*100:.1f}%)")
        
        if successful_cameras:
            print(f"\n✅ 检测算法优化成功！")
            print(f"建议使用摄像头: {successful_cameras}")
        else:
            print(f"\n❌ 所有摄像头都未检测到红光")
            print(f"建议检查:")
            print(f"  1. 确保有红色光源")
            print(f"  2. 调整摄像头曝光设置")
            print(f"  3. 进一步放宽HSV参数")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())