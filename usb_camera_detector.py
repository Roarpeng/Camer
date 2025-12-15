#!/usr/bin/env python3
"""
USB摄像头检测工具
检测系统中可用的USB摄像头设备并获取设备名称
"""

import cv2
import platform
import subprocess
import re
from typing import List, Dict, Tuple, Optional


class USBCameraDetector:
    """USB摄像头检测器"""
    
    def __init__(self):
        self.system = platform.system()
    
    def detect_cameras(self) -> List[Dict[str, any]]:
        """
        检测系统中可用的USB摄像头
        
        Returns:
            List[Dict]: 摄像头信息列表，包含id, name, description
        """
        cameras = []
        
        if self.system == "Windows":
            cameras = self._detect_windows_cameras()
        elif self.system == "Linux":
            cameras = self._detect_linux_cameras()
        elif self.system == "Darwin":  # macOS
            cameras = self._detect_macos_cameras()
        
        # 验证摄像头是否真正可用
        verified_cameras = []
        for camera in cameras:
            if self._verify_camera(camera['id']):
                verified_cameras.append(camera)
        
        return verified_cameras
    
    def _detect_windows_cameras(self) -> List[Dict[str, any]]:
        """检测Windows系统中的USB摄像头"""
        cameras = []
        
        try:
            # 使用PowerShell获取摄像头设备信息
            cmd = [
                "powershell", "-Command",
                "Get-WmiObject -Class Win32_PnPEntity | Where-Object {$_.Name -match 'camera|webcam|usb.*video'} | Select-Object Name, DeviceID"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                camera_id = 0
                
                for line in lines[3:]:  # 跳过标题行
                    if line.strip() and not line.startswith('-'):
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            name = ' '.join(parts[:-1])
                            if name and ('camera' in name.lower() or 'webcam' in name.lower() or 'usb' in name.lower()):
                                cameras.append({
                                    'id': camera_id,
                                    'name': name.strip(),
                                    'description': f"USB摄像头 {camera_id}",
                                    'device_path': f"Camera_{camera_id}"
                                })
                                camera_id += 1
        
        except Exception as e:
            print(f"Windows摄像头检测失败: {e}")
        
        # 如果PowerShell方法失败，使用简单的数字检测
        if not cameras:
            cameras = self._detect_cameras_by_index()
        
        return cameras
    
    def _detect_linux_cameras(self) -> List[Dict[str, any]]:
        """检测Linux系统中的USB摄像头"""
        cameras = []
        
        try:
            # 使用v4l2-ctl获取摄像头信息
            result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                current_device = None
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('\t') and ':' in line:
                        current_device = line.split(':')[0].strip()
                    elif line.startswith('\t/dev/video'):
                        device_path = line.strip()
                        device_id = int(re.search(r'video(\d+)', device_path).group(1))
                        
                        cameras.append({
                            'id': device_id,
                            'name': current_device or f"USB Camera {device_id}",
                            'description': f"Linux视频设备 {device_path}",
                            'device_path': device_path
                        })
        
        except Exception as e:
            print(f"Linux摄像头检测失败: {e}")
            # 回退到简单检测
            cameras = self._detect_cameras_by_index()
        
        return cameras
    
    def _detect_macos_cameras(self) -> List[Dict[str, any]]:
        """检测macOS系统中的USB摄像头"""
        cameras = []
        
        try:
            # 使用system_profiler获取USB设备信息
            result = subprocess.run([
                'system_profiler', 'SPCameraDataType', '-xml'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                # 简化处理，直接使用索引检测
                cameras = self._detect_cameras_by_index()
        
        except Exception as e:
            print(f"macOS摄像头检测失败: {e}")
            cameras = self._detect_cameras_by_index()
        
        return cameras
    
    def _detect_cameras_by_index(self) -> List[Dict[str, any]]:
        """通过索引检测摄像头（回退方法）"""
        cameras = []
        
        # 测试索引0-9的摄像头
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # 尝试读取一帧来确认摄像头工作
                ret, frame = cap.read()
                if ret and frame is not None:
                    cameras.append({
                        'id': i,
                        'name': f"USB摄像头 {i}",
                        'description': f"摄像头设备 {i}",
                        'device_path': f"Camera_{i}"
                    })
                cap.release()
        
        return cameras
    
    def _verify_camera(self, camera_id: int) -> bool:
        """验证摄像头是否可用"""
        try:
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                return ret and frame is not None
            return False
        except:
            return False
    
    def get_camera_info(self, camera_id: int) -> Optional[Dict[str, any]]:
        """获取特定摄像头的详细信息"""
        try:
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                return None
            
            # 获取摄像头属性
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            cap.release()
            
            return {
                'id': camera_id,
                'resolution': f"{width}x{height}",
                'fps': fps,
                'supported_resolutions': self._get_supported_resolutions(camera_id)
            }
        
        except Exception as e:
            print(f"获取摄像头 {camera_id} 信息失败: {e}")
            return None
    
    def _get_supported_resolutions(self, camera_id: int) -> List[Tuple[int, int]]:
        """获取摄像头支持的分辨率列表"""
        common_resolutions = [
            (1920, 1080),  # 1080p
            (1280, 720),   # 720p
            (640, 480),    # VGA
            (320, 240),    # QVGA
        ]
        
        supported = []
        
        try:
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                return supported
            
            for width, height in common_resolutions:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                
                actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                if actual_width == width and actual_height == height:
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        supported.append((width, height))
            
            cap.release()
        
        except Exception as e:
            print(f"检测摄像头 {camera_id} 支持分辨率失败: {e}")
        
        return supported


def main():
    """主函数 - 用于测试摄像头检测"""
    print("正在检测USB摄像头...")
    
    detector = USBCameraDetector()
    cameras = detector.detect_cameras()
    
    if cameras:
        print(f"\n发现 {len(cameras)} 个摄像头:")
        print("-" * 60)
        
        for camera in cameras:
            print(f"ID: {camera['id']}")
            print(f"名称: {camera['name']}")
            print(f"描述: {camera['description']}")
            
            # 获取详细信息
            info = detector.get_camera_info(camera['id'])
            if info:
                print(f"分辨率: {info['resolution']}")
                print(f"帧率: {info['fps']:.1f} FPS")
                if info['supported_resolutions']:
                    resolutions = [f"{w}x{h}" for w, h in info['supported_resolutions']]
                    print(f"支持分辨率: {', '.join(resolutions)}")
            
            print("-" * 60)
    else:
        print("未发现可用的USB摄像头")
    
    return cameras


if __name__ == "__main__":
    main()