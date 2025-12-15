#!/usr/bin/env python3
"""
最终生产系统
在成功的红色检测基础上加入MQTT逻辑
"""

import cv2
import numpy as np
import time
import threading
import logging
import sys
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from mqtt_camera_monitoring.config import ConfigManager
from mqtt_camera_monitoring.mqtt_client import MQTTClient

@dataclass
class CameraState:
    """摄像头状态"""
    camera_id: int
    baseline_red_count: int = -1  # 初始化为-1表示未建立基线
    current_red_count: int = -1
    last_reported_count: int = -1  # 上一次上报的数量
    baseline_established: bool = False
    baseline_time: float = 0.0  # 基线建立时间
    stable_period: float = 2.0  # 基线稳定期2秒
    stable_period_logged: bool = False  # 是否已记录稳定期结束

class FinalProductionSystem:
    """最终生产系统"""
    
    def __init__(self, config_file: str = "config.yaml", mask_file: str = "mask.png", enable_view: bool = False):
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('final_production.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        config_manager = ConfigManager(config_file)
        self.config = config_manager.load_config()
        
        # 加载mask
        self.mask_file = mask_file
        self.mask_image = None
        self.light_points = []
        
        if not self._load_mask():
            raise ValueError(f"无法加载mask文件: {mask_file}")
        
        # 系统状态
        self.running = False
        self.mqtt_triggered = False
        self.baseline_capture_time = 0.0
        self.enable_view = enable_view  # 是否启用视觉显示
        
        # 摄像头和状态
        self.cameras: List[Optional[cv2.VideoCapture]] = []
        self.camera_states: Dict[int, CameraState] = {}
        
        # MQTT客户端
        self.mqtt_client: Optional[MQTTClient] = None
        
        # 检测锁
        self.detection_lock = threading.Lock()
        
        # 视觉显示相关
        self.view_thread = None
        self.latest_frames = {}  # 存储最新帧用于显示
        
        self.logger.info(f"最终生产系统初始化完成，光点数: {len(self.light_points)}, 视觉显示: {enable_view}")
    
    def _load_mask(self) -> bool:
        """加载mask图片"""
        if not os.path.exists(self.mask_file):
            self.logger.error(f"Mask文件不存在: {self.mask_file}")
            return False
        
        mask_img = cv2.imread(self.mask_file, cv2.IMREAD_GRAYSCALE)
        if mask_img is None:
            self.logger.error(f"无法读取mask文件: {self.mask_file}")
            return False
        
        self.mask_image = mask_img
        self.logger.info(f"Mask加载成功: {mask_img.shape}")
        return True
    
    def _detect_red_lights(self, frame: np.ndarray) -> int:
        """检测红色光点数量 - 使用成功的检测逻辑"""
        
        # 调整mask尺寸匹配摄像头
        frame_height, frame_width = frame.shape[:2]
        mask_img = self.mask_image
        
        if mask_img.shape != (frame_height, frame_width):
            mask_img = cv2.resize(mask_img, (frame_width, frame_height), interpolation=cv2.INTER_NEAREST)
        
        # 识别光点区域（如果还没有识别过）
        if not self.light_points:
            binary_mask = (mask_img > 200).astype(np.uint8) * 255
            contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area >= 10:
                    self.light_points.append((i, contour))
            
            self.logger.info(f"识别到 {len(self.light_points)} 个光点区域")
        
        # 检测红色光点
        red_count = 0
        
        for light_id, contour in self.light_points:
            # 创建光点mask
            point_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            cv2.fillPoly(point_mask, [contour], 255)
            
            # 提取光点区域像素
            masked_pixels = frame[point_mask > 0]
            
            if len(masked_pixels) == 0:
                continue
            
            # 分析BGR颜色
            avg_bgr = np.mean(masked_pixels, axis=0)
            b, g, r = avg_bgr
            
            # 转换为HSV
            bgr_sample = np.uint8([[avg_bgr]])
            hsv_sample = cv2.cvtColor(bgr_sample, cv2.COLOR_BGR2HSV)[0][0]
            h, s, v = hsv_sample
            
            # 红色检测逻辑 - 使用成功的方法
            is_red_bgr = r > g and r > b and r > 100
            is_red_hsv = (0 <= h <= 25 or 155 <= h <= 180) and s > 50 and v > 50
            is_red = is_red_bgr or is_red_hsv
            
            if is_red:
                red_count += 1
        
        return red_count
    
    def _detect_red_lights_with_visual(self, frame: np.ndarray, camera_id: int) -> tuple[int, np.ndarray]:
        """检测红色光点数量并生成可视化图像"""
        
        # 调整mask尺寸匹配摄像头
        frame_height, frame_width = frame.shape[:2]
        mask_img = self.mask_image
        
        if mask_img.shape != (frame_height, frame_width):
            mask_img = cv2.resize(mask_img, (frame_width, frame_height), interpolation=cv2.INTER_NEAREST)
        
        # 识别光点区域（如果还没有识别过）
        if not self.light_points:
            binary_mask = (mask_img > 200).astype(np.uint8) * 255
            contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area >= 10:
                    self.light_points.append((i, contour))
        
        # 创建可视化图像
        visual_frame = frame.copy()
        
        # 应用mask - 非白色区域变暗
        black_mask = mask_img <= 200
        visual_frame[black_mask] = visual_frame[black_mask] // 3
        
        # 检测红色光点并标注
        red_count = 0
        red_light_positions = []
        
        for light_id, contour in self.light_points:
            # 创建光点mask
            point_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            cv2.fillPoly(point_mask, [contour], 255)
            
            # 提取光点区域像素
            masked_pixels = frame[point_mask > 0]
            
            if len(masked_pixels) == 0:
                continue
            
            # 分析BGR颜色
            avg_bgr = np.mean(masked_pixels, axis=0)
            b, g, r = avg_bgr
            
            # 转换为HSV
            bgr_sample = np.uint8([[avg_bgr]])
            hsv_sample = cv2.cvtColor(bgr_sample, cv2.COLOR_BGR2HSV)[0][0]
            h, s, v = hsv_sample
            
            # 红色检测逻辑
            is_red_bgr = r > g and r > b and r > 100
            is_red_hsv = (0 <= h <= 25 or 155 <= h <= 180) and s > 50 and v > 50
            is_red = is_red_bgr or is_red_hsv
            
            # 绘制光点轮廓和标注
            if is_red:
                red_count += 1
                # 红色光点用绿色框标注
                cv2.drawContours(visual_frame, [contour], -1, (0, 255, 0), 2)
                
                # 计算中心点
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    center_x = int(M["m10"] / M["m00"])
                    center_y = int(M["m01"] / M["m00"])
                    red_light_positions.append((center_x, center_y))
                    
                    # 标注光点ID和"RED"
                    cv2.putText(visual_frame, f"R{light_id}", (center_x-15, center_y-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            else:
                # 非红色光点用蓝色框标注
                cv2.drawContours(visual_frame, [contour], -1, (255, 0, 0), 1)
                
                # 计算中心点并标注ID
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    center_x = int(M["m10"] / M["m00"])
                    center_y = int(M["m01"] / M["m00"])
                    cv2.putText(visual_frame, str(light_id), (center_x-10, center_y+5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        
        # 添加状态信息
        state = self.camera_states.get(camera_id)
        if state:
            status_text = f"Camera {camera_id}: Red={red_count}/{len(self.light_points)}"
            if state.baseline_established:
                status_text += f" | Baseline={state.baseline_red_count}"
                current_time = time.time()
                time_since_baseline = current_time - state.baseline_time
                if time_since_baseline < state.stable_period:
                    status_text += f" | Stable({state.stable_period - time_since_baseline:.1f}s)"
                else:
                    diff = abs(red_count - state.baseline_red_count)
                    status_text += f" | Diff={diff}"
            
            # 绘制状态文本背景
            text_size = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            cv2.rectangle(visual_frame, (5, 5), (text_size[0] + 10, text_size[1] + 15), (0, 0, 0), -1)
            cv2.putText(visual_frame, status_text, (10, 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return red_count, visual_frame
    
    def initialize_cameras(self) -> bool:
        """初始化摄像头"""
        camera_count = min(self.config.cameras.count, 6)
        self.logger.info(f"初始化 {camera_count} 个摄像头...")
        
        self.cameras = [None] * camera_count
        
        for camera_id in range(camera_count):
            try:
                if camera_id > 0:
                    time.sleep(0.3)
                
                self.logger.info(f"初始化摄像头 {camera_id}...")
                
                # 使用成功的摄像头打开方式 - 完全不设置参数
                cap = cv2.VideoCapture(camera_id)
                
                if not cap.isOpened():
                    self.logger.warning(f"摄像头 {camera_id} 无法打开")
                    continue
                
                # 预热摄像头
                for _ in range(5):
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        break
                    time.sleep(0.1)
                
                if ret and frame is not None:
                    self.cameras[camera_id] = cap
                    self.camera_states[camera_id] = CameraState(camera_id)
                    self.logger.info(f"摄像头 {camera_id} 初始化成功: {frame.shape}")
                else:
                    self.logger.warning(f"摄像头 {camera_id} 无法读取帧")
                    cap.release()
                    
            except Exception as e:
                self.logger.error(f"摄像头 {camera_id} 初始化失败: {e}")
        
        active_cameras = len([c for c in self.cameras if c is not None])
        self.logger.info(f"成功初始化 {active_cameras} 个摄像头")
        return active_cameras > 0
    
    def initialize_mqtt(self) -> bool:
        """初始化MQTT连接"""
        try:
            from copy import deepcopy
            mqtt_config = deepcopy(self.config.mqtt)
            mqtt_config.client_id = "receiver"
            self.mqtt_client = MQTTClient(mqtt_config)
            
            if self.mqtt_client.connect():
                self.mqtt_client.set_message_callback(self._handle_mqtt_message)
                self.logger.info("MQTT连接成功")
                return True
            else:
                self.logger.error("MQTT连接失败")
                return False
                
        except Exception as e:
            self.logger.error(f"MQTT初始化失败: {e}")
            return False
    
    def _handle_mqtt_message(self, message_data: Dict) -> None:
        """处理MQTT消息"""
        try:
            payload_data = message_data.get('payload', {})
            ones_count = payload_data.get('count_of_ones', 0)
            is_update = message_data.get('is_update', False)
            
            self.logger.info(f"收到MQTT消息: {ones_count} ones, 更新: {is_update}")
            
            # 检查是否为144个ones - 如果是，则使之前的基线无效
            if ones_count == 144:
                self.logger.info("检测到144个ones，使之前基线无效，跳过基线建立")
                # 重置所有摄像头状态，使之前的基线无效
                with self.detection_lock:
                    for state in self.camera_states.values():
                        if state.baseline_established:
                            self.logger.info(f"摄像头 {state.camera_id} 基线已失效")
                        state.baseline_established = False
                        state.baseline_red_count = -1  # 重置为未建立状态
                        state.current_red_count = -1
                        state.last_reported_count = -1  # 重置上一次上报数量
                        state.baseline_time = 0.0
                        state.stable_period_logged = False
                return
            
            if ones_count == 0:
                self.logger.info("ones数量为0，跳过基线建立")
                return
            
            if not is_update:
                self.logger.info("changeState内容无更新，跳过基线建立")
                return
            
            # 满足条件，建立基线
            self.logger.info("基线建立条件满足，开始建立基线")
            self.mqtt_triggered = True
            self.baseline_capture_time = time.time() + 0.3  # 延时0.2秒
            
            # 重置所有摄像头状态
            with self.detection_lock:
                for state in self.camera_states.values():
                    state.baseline_established = False
                    state.baseline_red_count = -1  # 重置为未建立状态
                    state.current_red_count = -1
                    state.last_reported_count = -1  # 重置上一次上报数量
                    state.baseline_time = 0.0
                    state.stable_period_logged = False
            
        except Exception as e:
            self.logger.error(f"处理MQTT消息错误: {e}")
    
    def capture_baseline(self) -> None:
        """捕获基线数据"""
        self.logger.info("开始捕获红色光点基线数据...")
        
        with self.detection_lock:
            for camera_id, cap in enumerate(self.cameras):
                if cap is None or camera_id not in self.camera_states:
                    continue
                
                try:
                    # 捕获帧
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        self.logger.warning(f"摄像头 {camera_id} 无法捕获基线帧")
                        continue
                    
                    # 检测红色光点
                    red_count = self._detect_red_lights(frame)
                    
                    # 设置基线
                    state = self.camera_states[camera_id]
                    state.baseline_red_count = red_count
                    state.current_red_count = red_count
                    state.baseline_established = True
                    state.baseline_time = time.time()  # 记录基线建立时间
                    
                    self.logger.info(f"摄像头 {camera_id} 基线: {red_count}/{len(self.light_points)} 个红色光点")
                    
                except Exception as e:
                    self.logger.error(f"摄像头 {camera_id} 基线捕获失败: {e}")
        
        self.logger.info("基线捕获完成，开始2秒稳定期")
    
    def detect_and_compare(self) -> None:
        """检测并比较光点变化"""
        current_time = time.time()
        
        with self.detection_lock:
            for camera_id, cap in enumerate(self.cameras):
                if cap is None or camera_id not in self.camera_states:
                    continue
                
                state = self.camera_states[camera_id]
                
                # 只有基线已建立且基线值有效才进行检测
                if not state.baseline_established or state.baseline_red_count < 0:
                    continue
                
                # 检查是否还在稳定期内
                time_since_baseline = current_time - state.baseline_time
                if time_since_baseline < state.stable_period:
                    # 仍在稳定期内，只更新当前值但不触发检测
                    try:
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            current_count = self._detect_red_lights(frame)
                            state.current_red_count = current_count
                    except Exception as e:
                        self.logger.error(f"摄像头 {camera_id} 稳定期检测失败: {e}")
                    continue
                else:
                    # 稳定期结束，记录一次
                    if not state.stable_period_logged:
                        self.logger.info(f"摄像头 {camera_id} 稳定期结束，开始正式检测")
                        state.stable_period_logged = True
                
                try:
                    # 捕获帧
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        continue
                    
                    # 检测当前红色光点
                    current_count = self._detect_red_lights(frame)
                    state.current_red_count = current_count
                    
                    # 检查是否与上一次上报的数量不同
                    if state.last_reported_count == -1:
                        # 第一次检测，设置初始上报数量为当前数量
                        state.last_reported_count = current_count
                        self.logger.info(f"摄像头 {camera_id} 初始上报数量: {current_count}")
                    elif current_count != state.last_reported_count:
                        # 当前数量与上一次上报的数量不同，触发上报
                        count_diff = abs(current_count - state.last_reported_count)
                        self.logger.info(f"摄像头 {camera_id} 检测到光点数量变化: "
                                       f"基线={state.baseline_red_count}, "
                                       f"上次上报={state.last_reported_count}, "
                                       f"当前={current_count}, "
                                       f"变化={count_diff}")
                        
                        # 触发MQTT消息
                        self._trigger_mqtt_message(camera_id, current_count, state.last_reported_count)
                        
                        # 更新上一次上报的数量
                        state.last_reported_count = current_count
                    
                except Exception as e:
                    self.logger.error(f"摄像头 {camera_id} 检测失败: {e}")
    
    def _trigger_mqtt_message(self, camera_id: int, current_count: int, last_reported_count: int) -> None:
        """触发MQTT消息"""
        try:
            if self.mqtt_client and self.mqtt_client.client:
                result = self.mqtt_client.client.publish(
                    self.config.mqtt.publish_topic, 
                    payload=""
                )
                
                if result.rc == 0:
                    self.logger.info(f"摄像头 {camera_id} 触发MQTT消息成功 (光点数量: {last_reported_count} -> {current_count})")
                else:
                    self.logger.error(f"摄像头 {camera_id} 触发MQTT消息失败: {result.rc}")
            else:
                self.logger.error("MQTT客户端未连接，无法发送触发消息")
            
        except Exception as e:
            self.logger.error(f"触发MQTT消息错误: {e}")
    
    def detection_loop(self) -> None:
        """检测循环"""
        self.logger.info("开始光点检测循环")
        
        while self.running:
            try:
                current_time = time.time()
                
                # 检查是否需要捕获基线
                if self.mqtt_triggered and current_time >= self.baseline_capture_time:
                    self.capture_baseline()
                    self.mqtt_triggered = False
                
                # 执行检测和比较
                self.detect_and_compare()
                
                # 短暂休眠
                time.sleep(0.3)  # 每0.3秒检测一次
                
            except Exception as e:
                self.logger.error(f"检测循环错误: {e}")
                time.sleep(1)
        
        self.logger.info("检测循环结束")
    
    def visual_display_loop(self) -> None:
        """视觉显示循环"""
        self.logger.info("开始视觉显示循环")
        
        while self.running:
            try:
                # 为每个活跃摄像头显示画面
                for camera_id, cap in enumerate(self.cameras):
                    if cap is None:
                        continue
                    
                    # 捕获帧
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        continue
                    
                    # 生成可视化图像
                    red_count, visual_frame = self._detect_red_lights_with_visual(frame, camera_id)
                    
                    # 存储最新帧
                    self.latest_frames[camera_id] = visual_frame
                    
                    # 显示图像
                    window_name = f"Camera {camera_id} - Red Light Detection"
                    cv2.imshow(window_name, visual_frame)
                
                # 检查退出键
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q') or key == 27:  # 'q' 或 ESC 键退出
                    self.logger.info("用户请求退出视觉显示")
                    self.running = False
                    break
                
            except Exception as e:
                self.logger.error(f"视觉显示循环错误: {e}")
                time.sleep(0.1)
        
        # 关闭所有窗口
        cv2.destroyAllWindows()
        self.logger.info("视觉显示循环结束")
    
    def start(self) -> bool:
        """启动系统"""
        try:
            self.logger.info("启动最终生产系统")
            
            # 初始化摄像头
            if not self.initialize_cameras():
                self.logger.error("摄像头初始化失败")
                return False
            
            # 初始化MQTT
            if not self.initialize_mqtt():
                self.logger.warning("MQTT初始化失败，继续运行检测功能")
            
            # 启动检测线程
            self.running = True
            self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
            self.detection_thread.start()
            
            # 如果启用视觉显示，启动显示线程
            if self.enable_view:
                self.view_thread = threading.Thread(target=self.visual_display_loop, daemon=True)
                self.view_thread.start()
                self.logger.info("视觉显示已启动")
            
            self.logger.info("最终生产系统启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"系统启动失败: {e}")
            return False
    
    def stop(self) -> None:
        """停止系统"""
        try:
            self.logger.info("停止最终生产系统")
            
            self.running = False
            
            # 等待检测线程结束
            if hasattr(self, 'detection_thread') and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=2.0)
            
            # 等待视觉显示线程结束
            if hasattr(self, 'view_thread') and self.view_thread and self.view_thread.is_alive():
                self.view_thread.join(timeout=2.0)
            
            # 关闭OpenCV窗口
            cv2.destroyAllWindows()
            
            # 释放摄像头
            for cap in self.cameras:
                if cap is not None:
                    cap.release()
            
            # 断开MQTT连接
            if self.mqtt_client:
                self.mqtt_client.disconnect()
            
            self.logger.info("最终生产系统已停止")
            
        except Exception as e:
            self.logger.error(f"系统停止错误: {e}")
    
    def get_status(self) -> Dict:
        """获取系统状态"""
        with self.detection_lock:
            status = {
                'running': self.running,
                'mqtt_triggered': self.mqtt_triggered,
                'active_cameras': len([c for c in self.cameras if c is not None]),
                'total_light_points': len(self.light_points),
                'camera_states': {}
            }
            
            for camera_id, state in self.camera_states.items():
                current_time = time.time()
                time_since_baseline = current_time - state.baseline_time if state.baseline_time > 0 else 0
                in_stable_period = state.baseline_established and time_since_baseline < state.stable_period
                
                status['camera_states'][camera_id] = {
                    'baseline_established': state.baseline_established,
                    'baseline_red_count': state.baseline_red_count,
                    'current_red_count': state.current_red_count,
                    'last_reported_count': state.last_reported_count,
                    'in_stable_period': in_stable_period,
                    'time_since_baseline': time_since_baseline
                }
            
            return status

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='最终生产系统 - 红色光点检测与MQTT')
    parser.add_argument('--view', action='store_true', help='启用视觉显示模式')
    args = parser.parse_args()
    
    print("=== 最终生产系统 ===")
    print("在成功的红色检测基础上加入MQTT逻辑")
    if args.view:
        print("视觉显示模式已启用 - 按 'q' 或 ESC 键退出")
    else:
        print("按 Ctrl+C 退出")
    print()
    
    if not os.path.exists("mask.png"):
        print("[ERROR] 未找到mask.png文件")
        return 1
    
    system = None
    
    try:
        # 创建系统
        system = FinalProductionSystem(enable_view=args.view)
        
        # 启动系统
        if not system.start():
            print("[ERROR] 系统启动失败")
            return 1
        
        if args.view:
            # 视觉模式 - 等待视觉显示线程结束
            print("视觉显示运行中...")
            while system.running:
                time.sleep(0.5)
        else:
            # 非视觉模式 - 定期输出状态
            while True:
                time.sleep(10)  # 每10秒输出状态
                
                status = system.get_status()
                print(f"系统状态: 运行={status['running']}, "
                      f"活跃摄像头={status['active_cameras']}, "
                      f"总光点数={status['total_light_points']}, "
                      f"MQTT触发={status['mqtt_triggered']}")
                
                # 输出摄像头状态
                for camera_id, state in status['camera_states'].items():
                    if state['baseline_established']:
                        stable_info = f"稳定期中({state['time_since_baseline']:.1f}s)" if state['in_stable_period'] else "正常检测中"
                        print(f"摄像头 {camera_id}: "
                               f"基线红色光点数={state['baseline_red_count']}, "
                               f"当前红色光点数={state['current_red_count']}, "
                               f"上次上报数量={state['last_reported_count']}, "
                               f"状态={stable_info}")
    
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"[ERROR] 系统错误: {e}")
        return 1
    finally:
        if system:
            system.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())