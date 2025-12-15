#!/usr/bin/env python3
"""
摄像头配置更新工具
根据测试结果更新系统配置
"""

import yaml
import os

def update_camera_config():
    """更新摄像头配置"""
    
    print("=== 摄像头配置更新工具 ===")
    print("根据测试结果更新系统配置")
    print()
    
    config_file = "config.yaml"
    
    if not os.path.exists(config_file):
        print(f"[ERROR] 配置文件不存在: {config_file}")
        return False
    
    # 读取当前配置
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"[ERROR] 读取配置文件失败: {e}")
        return False
    
    print("当前摄像头配置:")
    cameras = config.get('cameras', {})
    print(f"  摄像头数量: {cameras.get('count', 1)}")
    print(f"  分辨率: {cameras.get('resolution_width', 1920)}x{cameras.get('resolution_height', 1080)}")
    print(f"  亮度: {cameras.get('brightness', 60)}")
    print(f"  曝光: {cameras.get('exposure', -4)}")
    print(f"  对比度: {cameras.get('contrast', 60)}")
    print(f"  饱和度: {cameras.get('saturation', 80)}")
    print(f"  自动曝光: {cameras.get('auto_exposure', False)}")
    print(f"  增益: {cameras.get('gain', 50)}")
    print()
    
    # 推荐的高亮度配置
    recommended_configs = [
        {
            "name": "自动曝光+高亮度",
            "auto_exposure": True,
            "exposure": 0,
            "brightness": 100,
            "contrast": 100,
            "gain": 100
        },
        {
            "name": "手动曝光10+高亮度",
            "auto_exposure": False,
            "exposure": 10,
            "brightness": 100,
            "contrast": 100,
            "gain": 100
        },
        {
            "name": "手动曝光8+高亮度",
            "auto_exposure": False,
            "exposure": 8,
            "brightness": 100,
            "contrast": 100,
            "gain": 100
        },
        {
            "name": "手动曝光6+高亮度",
            "auto_exposure": False,
            "exposure": 6,
            "brightness": 100,
            "contrast": 100,
            "gain": 100
        },
        {
            "name": "手动曝光5+高亮度",
            "auto_exposure": False,
            "exposure": 5,
            "brightness": 100,
            "contrast": 100,
            "gain": 100
        },
        {
            "name": "手动曝光3+高亮度",
            "auto_exposure": False,
            "exposure": 3,
            "brightness": 100,
            "contrast": 100,
            "gain": 100
        },
        {
            "name": "当前配置+提高亮度",
            "auto_exposure": cameras.get('auto_exposure', False),
            "exposure": cameras.get('exposure', -4),
            "brightness": 90,
            "contrast": 90,
            "gain": 90
        }
    ]
    
    print("推荐的配置选项:")
    for i, cfg in enumerate(recommended_configs, 1):
        print(f"{i}. {cfg['name']}")
        print(f"   自动曝光: {cfg['auto_exposure']}")
        if not cfg['auto_exposure']:
            print(f"   曝光: {cfg['exposure']}")
        print(f"   亮度: {cfg['brightness']}")
        print(f"   对比度: {cfg['contrast']}")
        print(f"   增益: {cfg['gain']}")
        print()
    
    print("8. 自定义配置")
    print("9. 不更新，退出")
    print()
    
    try:
        choice = input("请选择配置 (1-9): ").strip()
        
        if choice == "9":
            print("退出，不更新配置")
            return True
        
        selected_config = None
        
        if choice in ["1", "2", "3", "4", "5", "6", "7"]:
            selected_config = recommended_configs[int(choice) - 1]
        elif choice == "8":
            # 自定义配置
            print("\n=== 自定义配置 ===")
            
            auto_exp_input = input("使用自动曝光? (y/n): ").strip().lower()
            auto_exposure = auto_exp_input in ['y', 'yes', '是']
            
            exposure = 0
            if not auto_exposure:
                exposure = int(input("曝光值 (-11 到 10): "))
            
            brightness = int(input("亮度 (0-100): "))
            contrast = int(input("对比度 (0-100): "))
            gain = int(input("增益 (0-100): "))
            
            selected_config = {
                "name": "自定义配置",
                "auto_exposure": auto_exposure,
                "exposure": exposure,
                "brightness": brightness,
                "contrast": contrast,
                "gain": gain
            }
        else:
            print("[ERROR] 无效选择")
            return False
        
        if selected_config:
            # 更新配置
            print(f"\n应用配置: {selected_config['name']}")
            
            cameras['auto_exposure'] = selected_config['auto_exposure']
            cameras['exposure'] = selected_config['exposure']
            cameras['brightness'] = selected_config['brightness']
            cameras['contrast'] = selected_config['contrast']
            cameras['gain'] = selected_config['gain']
            
            # 备份原配置
            backup_file = f"{config_file}.backup"
            try:
                with open(backup_file, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                print(f"原配置已备份到: {backup_file}")
            except Exception as e:
                print(f"[WARNING] 备份失败: {e}")
            
            # 保存新配置
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                
                print(f"配置已更新到: {config_file}")
                print("\n新的摄像头配置:")
                print(f"  自动曝光: {cameras['auto_exposure']}")
                print(f"  曝光: {cameras['exposure']}")
                print(f"  亮度: {cameras['brightness']}")
                print(f"  对比度: {cameras['contrast']}")
                print(f"  增益: {cameras['gain']}")
                
                return True
                
            except Exception as e:
                print(f"[ERROR] 保存配置失败: {e}")
                return False
    
    except Exception as e:
        print(f"[ERROR] 配置更新错误: {e}")
        return False

def main():
    """主函数"""
    try:
        update_camera_config()
        return 0
    except Exception as e:
        print(f"[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())