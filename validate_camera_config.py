#!/usr/bin/env python3
"""
摄像头配置验证工具
验证当前系统的摄像头配置是否正确
"""

import cv2
import os
import yaml
from typing import List, Dict, Tuple
from usb_camera_detector import USBCameraDetector


class CameraConfigValidator:
    """摄像头配置验证器"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.detector = USBCameraDetector()
    
    def validate_system(self) -> Tuple[bool, List[str]]:
        """
        验证整个系统配置
        
        Returns:
            Tuple[bool, List[str]]: (是否通过验证, 错误信息列表)
        """
        errors = []
        
        # 1. 检测可用摄像头
        print("1. 检测可用摄像头...")
        available_cameras = self.detector.detect_cameras()
        
        if not available_cameras:
            errors.append("❌ 未检测到可用的USB摄像头")
            print("   ❌ 未检测到可用的USB摄像头")
        else:
            print(f"   ✅ 检测到 {len(available_cameras)} 个摄像头")
            for camera in available_cameras:
                print(f"      - ID {camera['id']}: {camera['name']}")
        
        # 2. 验证配置文件
        print("\n2. 验证配置文件...")
        config_errors = self._validate_config_file()
        errors.extend(config_errors)
        
        # 3. 验证摄像头分辨率支持
        print("\n3. 验证摄像头分辨率支持...")
        resolution_errors = self._validate_camera_resolutions(available_cameras)
        errors.extend(resolution_errors)
        
        # 4. 验证掩码文件
        print("\n4. 验证掩码文件...")
        mask_errors = self._validate_mask_files()
        errors.extend(mask_errors)
        
        # 5. 验证MQTT连接
        print("\n5. 验证MQTT连接...")
        mqtt_errors = self._validate_mqtt_connection()
        errors.extend(mqtt_errors)
        
        # 总结
        print(f"\n{'='*50}")
        if errors:
            print(f"❌ 验证失败，发现 {len(errors)} 个问题:")
            for i, error in enumerate(errors, 1):
                print(f"   {i}. {error}")
            return False, errors
        else:
            print("✅ 所有验证通过，系统配置正确！")
            return True, []
    
    def _validate_config_file(self) -> List[str]:
        """验证配置文件"""
        errors = []
        
        if not os.path.exists(self.config_file):
            errors.append(f"配置文件 {self.config_file} 不存在")
            print(f"   ❌ 配置文件 {self.config_file} 不存在")
            return errors
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            print(f"   ✅ 配置文件 {self.config_file} 读取成功")
            
            # 验证配置结构 - 适应实际的配置文件格式
            gui_config = config.get('gui_config', {})
            
            if 'cameras' not in gui_config:
                errors.append("配置文件缺少 'gui_config.cameras' 部分")
            
            if 'system_parameters' not in gui_config:
                errors.append("配置文件缺少 'gui_config.system_parameters' 部分")
            
            # 验证摄像头配置
            enabled_cameras = 0
            used_physical_ids = []
            
            for i, camera_config in enumerate(gui_config.get('cameras', [])):
                if camera_config.get('enabled', False):
                    enabled_cameras += 1
                    physical_id = camera_config.get('physical_camera_id', -1)
                    
                    if physical_id in used_physical_ids:
                        errors.append(f"摄像头 {i} 使用了重复的物理ID {physical_id}")
                    else:
                        used_physical_ids.append(physical_id)
            
            if enabled_cameras == 0:
                errors.append("没有启用任何摄像头")
            else:
                print(f"   ✅ 配置了 {enabled_cameras} 个启用的摄像头")
        
        except Exception as e:
            errors.append(f"读取配置文件失败: {e}")
            print(f"   ❌ 读取配置文件失败: {e}")
        
        return errors
    
    def _validate_camera_resolutions(self, available_cameras: List[Dict]) -> List[str]:
        """验证摄像头分辨率支持"""
        errors = []
        
        if not available_cameras:
            return ["没有可用摄像头进行分辨率验证"]
        
        for camera in available_cameras:
            camera_id = camera['id']
            
            try:
                cap = cv2.VideoCapture(camera_id)
                if not cap.isOpened():
                    errors.append(f"摄像头 {camera_id} 无法打开")
                    print(f"   ❌ 摄像头 {camera_id} 无法打开")
                    continue
                
                # 设置1920x1080分辨率
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                
                # 读取一帧验证
                ret, frame = cap.read()
                if ret and frame is not None:
                    height, width = frame.shape[:2]
                    if width == 1920 and height == 1080:
                        print(f"   ✅ 摄像头 {camera_id} 支持1920x1080分辨率")
                    else:
                        errors.append(f"摄像头 {camera_id} 不支持1920x1080分辨率 (实际: {width}x{height})")
                        print(f"   ❌ 摄像头 {camera_id} 不支持1920x1080分辨率 (实际: {width}x{height})")
                else:
                    errors.append(f"摄像头 {camera_id} 无法捕获画面")
                    print(f"   ❌ 摄像头 {camera_id} 无法捕获画面")
                
                cap.release()
            
            except Exception as e:
                errors.append(f"验证摄像头 {camera_id} 时出错: {e}")
                print(f"   ❌ 验证摄像头 {camera_id} 时出错: {e}")
        
        return errors
    
    def _validate_mask_files(self) -> List[str]:
        """验证掩码文件"""
        errors = []
        
        # 检查默认掩码文件
        default_masks = ['mask.png', 'fmask.png']
        
        for mask_file in default_masks:
            if os.path.exists(mask_file):
                try:
                    img = cv2.imread(mask_file)
                    if img is not None:
                        height, width = img.shape[:2]
                        if width == 1920 and height == 1080:
                            print(f"   ✅ 掩码文件 {mask_file} 分辨率正确 (1920x1080)")
                        else:
                            errors.append(f"掩码文件 {mask_file} 分辨率不正确: {width}x{height}")
                            print(f"   ❌ 掩码文件 {mask_file} 分辨率不正确: {width}x{height}")
                    else:
                        errors.append(f"无法读取掩码文件 {mask_file}")
                        print(f"   ❌ 无法读取掩码文件 {mask_file}")
                except Exception as e:
                    errors.append(f"验证掩码文件 {mask_file} 时出错: {e}")
                    print(f"   ❌ 验证掩码文件 {mask_file} 时出错: {e}")
            else:
                print(f"   ⚠️  掩码文件 {mask_file} 不存在")
        
        # 检查配置文件中指定的掩码文件
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                gui_config = config.get('gui_config', {})
                for camera_config in gui_config.get('cameras', []):
                    if camera_config.get('enabled', False):
                        mask_path = camera_config.get('mask_path', '')
                        if mask_path and mask_path not in default_masks:
                            if os.path.exists(mask_path):
                                try:
                                    img = cv2.imread(mask_path)
                                    if img is not None:
                                        height, width = img.shape[:2]
                                        if width == 1920 and height == 1080:
                                            print(f"   ✅ 配置的掩码文件 {mask_path} 分辨率正确")
                                        else:
                                            errors.append(f"配置的掩码文件 {mask_path} 分辨率不正确: {width}x{height}")
                                    else:
                                        errors.append(f"无法读取配置的掩码文件 {mask_path}")
                                except Exception as e:
                                    errors.append(f"验证配置的掩码文件 {mask_path} 时出错: {e}")
                            else:
                                errors.append(f"配置的掩码文件 {mask_path} 不存在")
            
            except Exception as e:
                errors.append(f"读取配置文件验证掩码时出错: {e}")
        
        return errors
    
    def _validate_mqtt_connection(self) -> List[str]:
        """验证MQTT连接"""
        errors = []
        
        try:
            import paho.mqtt.client as mqtt
            import time
            
            connection_result = {'success': False, 'error': None}
            
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    connection_result['success'] = True
                    print("   ✅ MQTT连接成功")
                else:
                    connection_result['error'] = f"连接失败，错误码: {rc}"
                    print(f"   ❌ MQTT连接失败，错误码: {rc}")
            
            def on_connect_fail(client, userdata):
                connection_result['error'] = "连接失败"
                print("   ❌ MQTT连接失败")
            
            client = mqtt.Client('config_validator')
            client.on_connect = on_connect
            client.on_connect_fail = on_connect_fail
            
            # 尝试连接
            client.connect('192.168.10.80', 1883, 60)
            client.loop_start()
            
            # 等待连接结果
            time.sleep(3)
            
            client.loop_stop()
            client.disconnect()
            
            if not connection_result['success']:
                error_msg = connection_result['error'] or "连接超时"
                errors.append(f"MQTT连接失败: {error_msg}")
        
        except ImportError:
            errors.append("paho-mqtt库未安装，无法验证MQTT连接")
            print("   ⚠️  paho-mqtt库未安装，无法验证MQTT连接")
        except Exception as e:
            errors.append(f"MQTT连接验证出错: {e}")
            print(f"   ❌ MQTT连接验证出错: {e}")
        
        return errors
    
    def generate_report(self) -> str:
        """生成验证报告"""
        success, errors = self.validate_system()
        
        report = f"""
摄像头监控系统配置验证报告
{'='*50}
验证时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

验证结果: {'✅ 通过' if success else '❌ 失败'}

"""
        
        if errors:
            report += f"发现问题 ({len(errors)} 个):\n"
            for i, error in enumerate(errors, 1):
                report += f"  {i}. {error}\n"
        else:
            report += "✅ 所有检查项目都通过验证\n"
        
        report += f"\n{'='*50}\n"
        
        return report


def main():
    """主函数"""
    print("MQTT摄像头监控系统 - 配置验证工具")
    print("="*50)
    
    validator = CameraConfigValidator()
    success, errors = validator.validate_system()
    
    # 生成报告文件
    report = validator.generate_report()
    with open('validation_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n详细报告已保存到: validation_report.txt")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())