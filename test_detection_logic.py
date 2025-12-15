#!/usr/bin/env python3
"""
检测逻辑测试 - 验证红光检测和面积比较逻辑
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
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def test_single_camera_detection(camera_id=1):
    """测试单个摄像头的检测逻辑"""
    logger = logging.getLogger(__name__)
    
    try:
        # 加载配置
        config_manager = ConfigManager('config.yaml')
        config = config_manager.load_config()
        
        # 创建检测器
        detector = RedLightDetector(config.red_light_detection)
        
        # 打开摄像头
        logger.info(f"打开摄像头 {camera_id}...")
        cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        
        if not cap.isOpened():
            logger.error(f"无法打开摄像头 {camera_id}")
            return False
        
        # 配置摄像头
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # 设置曝光参数
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, config.cameras.exposure)
        cap.set(cv2.CAP_PROP_BRIGHTNESS, config.cameras.brightness / 100.0)
        cap.set(cv2.CAP_PROP_CONTRAST, config.cameras.contrast / 100.0)
        
        # 预热
        for _ in range(5):
            cap.read()
            time.sleep(0.1)
        
        logger.info("摄像头就绪，开始检测测试...")
        logger.info("按 Enter 键设置基线，按 'q' 退出")
        
        baseline_area = None
        detection_count = 0
        
        while True:
            # 捕获帧
            ret, frame = cap.read()
            if not ret or frame is None:
                logger.warning("无法捕获帧")
                continue
            
            # 检测红光
            detection = detector.detect_red_lights(frame)
            detection_count += 1
            
            # 显示检测结果
            if detection_count % 10 == 0:  # 每2秒显示一次
                logger.info(f"检测结果: 数量={detection.count}, 面积={detection.total_area:.2f}")
            
            # 如果有基线，比较数量变化
            if baseline_area is not None:
                baseline_count = int(baseline_area)  # 重用变量名存储基线数量
                
                if detection.count != baseline_count:
                    logger.warning(f"⚠️  红光数量变化! "
                                 f"基线={baseline_count}, "
                                 f"当前={detection.count}, "
                                 f"变化={detection.count - baseline_count:+d}")
            
            # 检查键盘输入
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == 13:  # Enter键
                baseline_area = detection.count  # 重用变量名存储基线数量
                logger.info(f"✅ 基线已设置: 数量={detection.count}")
            
            time.sleep(0.2)  # 0.2秒间隔
        
        cap.release()
        logger.info("测试完成")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        return False

def test_all_cameras_detection():
    """测试所有摄像头的检测"""
    logger = logging.getLogger(__name__)
    
    try:
        # 加载配置
        config_manager = ConfigManager('config.yaml')
        config = config_manager.load_config()
        
        # 创建检测器
        detector = RedLightDetector(config.red_light_detection)
        
        logger.info("测试所有摄像头的红光检测...")
        
        # 测试每个摄像头
        for camera_id in range(config.cameras.count):
            logger.info(f"\n--- 测试摄像头 {camera_id} ---")
            
            try:
                # 打开摄像头
                cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
                
                if not cap.isOpened():
                    logger.warning(f"摄像头 {camera_id} 无法打开")
                    continue
                
                # 配置和预热
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # 设置曝光参数
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                cap.set(cv2.CAP_PROP_EXPOSURE, config.cameras.exposure)
                cap.set(cv2.CAP_PROP_BRIGHTNESS, config.cameras.brightness / 100.0)
                
                for _ in range(3):
                    cap.read()
                    time.sleep(0.1)
                
                # 检测红光
                ret, frame = cap.read()
                if ret and frame is not None:
                    detection = detector.detect_red_lights(frame)
                    logger.info(f"摄像头 {camera_id}: 数量={detection.count}")
                else:
                    logger.warning(f"摄像头 {camera_id}: 无法读取帧")
                
                cap.release()
                time.sleep(0.3)  # 延迟避免冲突
                
            except Exception as e:
                logger.error(f"摄像头 {camera_id} 测试失败: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        return False

def main():
    """主函数"""
    print("=== 检测逻辑测试 ===")
    print("1. 测试单个摄像头检测逻辑")
    print("2. 测试所有摄像头检测")
    print()
    
    setup_logging()
    
    try:
        choice = input("请选择测试模式 (1/2): ").strip()
        
        if choice == "1":
            camera_id = input("请输入摄像头ID (默认1): ").strip()
            camera_id = int(camera_id) if camera_id else 1
            
            print(f"\n开始测试摄像头 {camera_id}...")
            print("系统将显示检测结果")
            print("按 Enter 键设置基线，按 'q' 退出")
            
            test_single_camera_detection(camera_id)
            
        elif choice == "2":
            print("\n开始测试所有摄像头...")
            test_all_cameras_detection()
            
        else:
            print("无效选择")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\n用户中断")
        return 0
    except Exception as e:
        print(f"错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())