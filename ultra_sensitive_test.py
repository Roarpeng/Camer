#!/usr/bin/env python3
"""
超敏感红光检测测试 - 实时显示检测效果
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

def balanced_detection(frame):
    """平衡的红光检测算法 - 适中敏感度"""
    if frame is None or frame.size == 0:
        return 0, [], np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8)
    
    # 最小模糊减少噪声
    blurred = cv2.GaussianBlur(frame, (1, 1), 0) if frame.shape[0] > 100 else frame
    
    # 转换颜色空间
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    
    # 1. 适中的HSV红色检测
    lower_red_1 = np.array([0, 25, 25], dtype=np.uint8)
    upper_red_1 = np.array([18, 255, 255], dtype=np.uint8)
    lower_red_2 = np.array([160, 25, 25], dtype=np.uint8)
    upper_red_2 = np.array([180, 255, 255], dtype=np.uint8)
    
    mask1 = cv2.inRange(hsv, lower_red_1, upper_red_1)
    mask2 = cv2.inRange(hsv, lower_red_2, upper_red_2)
    hsv_mask = cv2.bitwise_or(mask1, mask2)
    
    # 2. 适中的亮度过滤
    brightness_mask = hsv[:, :, 2] > 30
    hsv_mask = cv2.bitwise_and(hsv_mask, brightness_mask.astype(np.uint8) * 255)
    
    # 3. 红色通道优势检测（适中条件）
    b, g, r = cv2.split(blurred)
    red_dominant = (r > g + 15) & (r > b + 15) & (r > 40)
    red_channel_mask = red_dominant.astype(np.uint8) * 255
    
    # 4. 组合检测结果（使用OR保持检测能力）
    final_mask = cv2.bitwise_or(hsv_mask, red_channel_mask)
    
    # 最小形态学处理
    if np.any(final_mask):
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (1, 1))
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # 查找轮廓
    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 适度的轮廓过滤
    valid_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 3 or area > 80000:  # 放宽面积限制
            continue
        
        # 基本形状检查
        x, y, w, h = cv2.boundingRect(contour)
        if w > 0 and h > 0:
            aspect_ratio = float(w) / h
            if aspect_ratio < 0.2 or aspect_ratio > 5.0:  # 放宽长宽比
                continue
        
        valid_contours.append(contour)
    
    return len(valid_contours), valid_contours, final_mask

def test_camera_balanced(camera_id: int, duration: int = 10):
    """测试单个摄像头的平衡检测"""
    print(f"\n=== 平衡检测测试摄像头 {camera_id} ===")
    
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
    cap.set(cv2.CAP_PROP_EXPOSURE, -4)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.6)
    cap.set(cv2.CAP_PROP_CONTRAST, 0.6)
    cap.set(cv2.CAP_PROP_SATURATION, 0.8)
    
    print(f"✅ 摄像头 {camera_id} 初始化成功")
    
    # 预热
    for _ in range(5):
        ret, frame = cap.read()
        if not ret:
            print(f"❌ 摄像头 {camera_id} 无法读取帧")
            cap.release()
            return False
    
    print(f"开始 {duration} 秒平衡检测测试...")
    print("按 'q' 键提前退出，按 's' 键保存当前帧")
    
    detection_results = []
    start_time = time.time()
    frame_count = 0
    
    try:
        while time.time() - start_time < duration:
            ret, frame = cap.read()
            if not ret:
                continue
            
            frame_count += 1
            
            # 执行平衡检测
            count, contours, mask = balanced_detection(frame)
            detection_results.append(count)
            
            # 在原图上绘制检测结果
            result_frame = frame.copy()
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(result_frame, (x, y), (x+w, y+h), (0, 255, 0), 1)
            
            # 显示信息
            elapsed = time.time() - start_time
            cv2.putText(result_frame, f"Camera {camera_id}: {count} red lights", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(result_frame, f"Time: {elapsed:.1f}s", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 显示原图和掩码
            display_frame = np.hstack([result_frame, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)])
            cv2.imshow(f'Camera {camera_id} - Balanced Detection', display_frame)
            
            # 每秒输出一次结果
            if frame_count % 10 == 0:
                avg_count = np.mean(detection_results[-10:]) if len(detection_results) >= 10 else np.mean(detection_results)
                print(f"  {elapsed:.1f}s: 检测到 {count} 个红光 (平均: {avg_count:.1f})")
            
            # 检查按键
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("用户退出测试")
                break
            elif key == ord('s'):
                filename = f"camera_{camera_id}_frame_{frame_count}.jpg"
                cv2.imwrite(filename, frame)
                print(f"保存帧到 {filename}")
    
    except KeyboardInterrupt:
        print("用户中断测试")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    # 统计结果
    if detection_results:
        total_detections = len(detection_results)
        non_zero_detections = len([x for x in detection_results if x > 0])
        avg_count = np.mean(detection_results)
        max_count = max(detection_results)
        
        print(f"\n📊 摄像头 {camera_id} 平衡检测统计:")
        print(f"  总检测次数: {total_detections}")
        print(f"  检测到红光次数: {non_zero_detections} ({non_zero_detections/total_detections*100:.1f}%)")
        print(f"  平均红光数量: {avg_count:.2f}")
        print(f"  最大红光数量: {max_count}")
        
        return non_zero_detections > 0
    
    return False

def main():
    """主函数"""
    print("=== 平衡红光检测算法测试 ===")
    print("实时显示检测效果，绿色框标记检测到的红光")
    print("减少误检，提高检测精度")
    print("按 'q' 退出，按 's' 保存当前帧")
    print()
    
    setup_logging()
    
    try:
        # 测试所有摄像头
        successful_cameras = []
        
        for camera_id in range(6):
            try:
                success = test_camera_balanced(camera_id, duration=15)
                if success:
                    successful_cameras.append(camera_id)
                    print(f"✅ 摄像头 {camera_id} 检测到红光")
                else:
                    print(f"⚠️  摄像头 {camera_id} 未检测到红光")
                
            except Exception as e:
                print(f"❌ 摄像头 {camera_id} 测试失败: {e}")
            
            print("-" * 50)
        
        # 总结
        print(f"\n🎯 平衡检测测试总结:")
        print(f"  成功检测红光的摄像头: {successful_cameras}")
        print(f"  检测成功率: {len(successful_cameras)}/6 ({len(successful_cameras)/6*100:.1f}%)")
        
        if successful_cameras:
            print(f"\n✅ 平衡检测算法成功！")
            print(f"建议使用摄像头: {successful_cameras}")
        else:
            print(f"\n❌ 所有摄像头都未检测到红光")
            print(f"建议检查红色光源是否存在")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())