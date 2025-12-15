#!/usr/bin/env python3
"""
测试摄像头系统 - 验证哪些摄像头可以正常工作
"""

import cv2
import time
import logging
import sys

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def test_single_camera(camera_id: int, test_duration: int = 3) -> bool:
    """测试单个摄像头"""
    print(f"测试摄像头 {camera_id}...", end=" ")
    
    cap = None
    try:
        # 尝试使用DirectShow后端
        cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        
        if not cap.isOpened():
            print("❌ 无法打开")
            return False
        
        # 配置基本参数
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # 测试读取帧
        success_count = 0
        total_attempts = 0
        
        start_time = time.time()
        while time.time() - start_time < test_duration:
            ret, frame = cap.read()
            total_attempts += 1
            
            if ret and frame is not None:
                success_count += 1
            
            time.sleep(0.1)
        
        success_rate = success_count / total_attempts if total_attempts > 0 else 0
        
        if success_rate > 0.8:
            print(f"✅ 成功 (成功率: {success_rate:.1%})")
            return True
        else:
            print(f"❌ 无法读取帧 (成功率: {success_rate:.1%})")
            return False
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False
    
    finally:
        if cap:
            cap.release()

def main():
    """主函数"""
    print("=== 摄像头系统测试 ===")
    print("检测所有可用的摄像头")
    print()
    
    setup_logging()
    
    working_cameras = []
    
    # 测试摄像头 0-9
    for camera_id in range(10):
        if test_single_camera(camera_id):
            working_cameras.append(camera_id)
    
    print()
    print("📊 测试结果:")
    print(f"  可用摄像头: {working_cameras}")
    print(f"  总数: {len(working_cameras)}")
    
    if len(working_cameras) >= 3:
        print("✅ 摄像头数量足够，可以运行检测系统")
    else:
        print("⚠️  摄像头数量不足，建议检查硬件连接")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())