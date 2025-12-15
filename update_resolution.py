#!/usr/bin/env python3
"""
批量更新所有文件的分辨率设置为720p (1280x720)
"""

import os
import re

def update_file_resolution(filepath):
    """更新单个文件的分辨率设置"""
    if not os.path.exists(filepath):
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换1376x768为1280x720
        content = re.sub(r'1376', '1280', content)
        content = re.sub(r'768', '720', content)
        
        # 替换1920x1080为1280x720
        content = re.sub(r'1920', '1280', content)
        content = re.sub(r'1080', '720', content)
        
        # 更新注释
        content = re.sub(r'1080p分辨率', '720p分辨率', content)
        content = re.sub(r'分辨率匹配mask \(1376x768\)', '720p分辨率 (1280x720)', content)
        content = re.sub(r'使用分辨率匹配mask \(1376x768\)', '使用720p分辨率 (1280x720)', content)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[OK] 更新: {filepath}")
        return True
        
    except Exception as e:
        print(f"[ERROR] 更新失败 {filepath}: {e}")
        return False

def main():
    """主函数"""
    print("=== 批量更新分辨率设置为720p ===")
    
    # 需要更新的文件列表
    files_to_update = [
        'mask_detection_visualizer.py',
        'red_light_detection_system.py',
        'quick_detection_test.py',
        'debug_detection.py',
        'mqtt_camera_monitoring/async_camera_manager.py',
        'detection_status_display.py',
        'camera_erosion_tuner.py',
        'camera_exposure_test.py'
    ]
    
    updated_count = 0
    
    for filepath in files_to_update:
        if update_file_resolution(filepath):
            updated_count += 1
    
    print(f"\n更新完成: {updated_count}/{len(files_to_update)} 个文件")

if __name__ == "__main__":
    main()