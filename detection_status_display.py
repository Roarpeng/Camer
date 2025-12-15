#!/usr/bin/env python3
"""
检测状态显示 - 实时显示红光检测结果，不显示摄像头画面
"""

import cv2
import numpy as np
import time
import threading
import logging
import sys
from typing import Dict, List, Optional
from dataclasses import dataclass
from mqtt_camera_monitoring.config import ConfigManager
from mqtt_camera_monitoring.light_detector import RedLightDetector

@dataclass
class CameraStatus:
    """摄像头状态"""
    camera_id: int
    active: bool = False
    red_count: int = 0
    last_update: float = 0.0
    total_detections: int = 0

class DetectionStatusDisplay:
    """检测状态显示系统"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        config_manager = ConfigManager('config.yaml')
        self.config = config_manager.load_config()
        
        # 摄像头和检测器
        self.cameras: List[Optional[cv2.VideoCapture]] = []
        self.camera_status: Dict[int, CameraStatus] = {}
        self.detector = RedLightDetector(self.config.red_light_detection)
        
        # 控制变量
        self.running = False
        self.detection_threads: List[threading.Thread] = []
        
        self.logger.info("检测状态显示系统初始化完成")
    
    def initialize_cameras(self) -> bool:
        """初始化摄像头"""
        self.logger.info(f"初始化 {self.config.cameras.count} 个摄像头...")
        
        self.cameras = [None] * self.config.cameras.count
        
        for camera_id in range(self.config.cameras.count):
            try:
                # 延迟初始化
                if camera_id > 0:
                    time.sleep(0.3)
                
                self.logger.info(f"初始化摄像头 {camera_id}...")
                
                cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
                
                if not cap.isOpened():
                    self.logger.warning(f"摄像头 {camera_id} 无法打开")
                    self.camera_status[camera_id] = CameraStatus(camera_id, False)
                    continue
                
                # 配置摄像头
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # 测试帧捕获
                ret, frame = cap.read()
                if ret and frame is not None:
                    self.cameras[camera_id] = cap
                    self.camera_status[camera_id] = CameraStatus(camera_id, True)
                    self.logger.info(f"摄像头 {camera_id} 初始化成功")
                else:
                    self.logger.warning(f"摄像头 {camera_id} 无法读取帧")
                    cap.release()
                    self.camera_status[camera_id] = CameraStatus(camera_id, False)
                    
            except Exception as e:
                self.logger.error(f"摄像头 {camera_id} 初始化失败: {e}")
                self.camera_status[camera_id] = CameraStatus(camera_id, False)
        
        active_count = len([s for s in self.camera_status.values() if s.active])
        self.logger.info(f"成功初始化 {active_count} 个摄像头")
        
        return active_count > 0
    
    def detect_camera_loop(self, camera_id: int) -> None:
        """单个摄像头检测循环"""
        cap = self.cameras[camera_id]
        status = self.camera_status[camera_id]
        
        if not cap or not status.active:
            return
        
        self.logger.info(f"摄像头 {camera_id} 检测线程启动")
        
        while self.running:
            try:
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    # 检测红光
                    detection = self.detector.detect_red_lights(frame)
                    
                    # 更新状态
                    status.red_count = detection.count
                    status.last_update = time.time()
                    status.total_detections += 1
                
                time.sleep(0.2)  # 5 FPS检测频率
                
            except Exception as e:
                self.logger.error(f"摄像头 {camera_id} 检测错误: {e}")
                time.sleep(1)
        
        self.logger.info(f"摄像头 {camera_id} 检测线程结束")
    
    def display_status_loop(self) -> None:
        """状态显示循环"""
        self.logger.info("状态显示循环启动")
        
        while self.running:
            try:
                # 清屏
                if sys.platform == "win32":
                    import os
                    os.system('cls')
                else:
                    print('\033[2J\033[H')
                
                # 显示标题
                print("=" * 80)
                print("红光检测状态实时显示".center(80))
                print("=" * 80)
                print(f"更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                print()
                
                # 显示摄像头状态
                print(f"{'摄像头':<8} {'状态':<8} {'红光数量':<10} {'检测次数':<10} {'最后更新':<12}")
                print("-" * 70)
                
                total_red_count = 0
                active_cameras = 0
                
                for camera_id in sorted(self.camera_status.keys()):
                    status = self.camera_status[camera_id]
                    
                    if status.active:
                        active_cameras += 1
                        total_red_count += status.red_count
                        
                        last_update_str = f"{time.time() - status.last_update:.1f}s前" if status.last_update > 0 else "无"
                        
                        print(f"Cam {camera_id:<4} {'活跃':<8} {status.red_count:<10} "
                              f"{status.total_detections:<10} {last_update_str:<12}")
                    else:
                        print(f"Cam {camera_id:<4} {'离线':<8} {'-':<10} {'-':<10} {'-':<12}")
                
                print("-" * 70)
                print(f"总计: 活跃摄像头={active_cameras}, 总红光数量={total_red_count}")
                print()
                print("按 Ctrl+C 退出")
                
                time.sleep(1)  # 每秒更新一次显示
                
            except Exception as e:
                self.logger.error(f"状态显示错误: {e}")
                time.sleep(1)
        
        self.logger.info("状态显示循环结束")
    
    def start(self) -> bool:
        """启动系统"""
        try:
            # 初始化摄像头
            if not self.initialize_cameras():
                self.logger.error("摄像头初始化失败")
                return False
            
            # 启动检测线程
            self.running = True
            
            for camera_id, status in self.camera_status.items():
                if status.active:
                    thread = threading.Thread(
                        target=self.detect_camera_loop, 
                        args=(camera_id,), 
                        daemon=True
                    )
                    thread.start()
                    self.detection_threads.append(thread)
            
            # 启动状态显示
            display_thread = threading.Thread(target=self.display_status_loop, daemon=True)
            display_thread.start()
            
            self.logger.info("检测状态显示系统启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"系统启动失败: {e}")
            return False
    
    def stop(self) -> None:
        """停止系统"""
        try:
            self.logger.info("停止检测状态显示系统")
            
            self.running = False
            
            # 等待检测线程结束
            for thread in self.detection_threads:
                if thread.is_alive():
                    thread.join(timeout=1.0)
            
            # 释放摄像头
            for cap in self.cameras:
                if cap is not None:
                    cap.release()
            
            self.logger.info("检测状态显示系统已停止")
            
        except Exception as e:
            self.logger.error(f"系统停止错误: {e}")

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('detection_status.log')
        ]
    )

def main():
    """主函数"""
    print("=== 检测状态显示系统 ===")
    print("实时显示红光检测结果，不显示摄像头画面")
    print("按 Ctrl+C 退出")
    print()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    system = None
    
    try:
        # 创建系统
        system = DetectionStatusDisplay()
        
        # 启动系统
        if not system.start():
            logger.error("系统启动失败")
            return 1
        
        # 主循环
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        logger.error(f"系统错误: {e}")
        return 1
    finally:
        if system:
            system.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())