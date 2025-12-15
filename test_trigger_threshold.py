#!/usr/bin/env python3
"""
测试触发阈值逻辑 - 验证只有减少3个或以上才触发
"""

import time
import logging
import sys
from mqtt_camera_monitoring.config import ConfigManager

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def test_trigger_logic():
    """测试触发逻辑"""
    print("=== 触发阈值逻辑测试 ===")
    print()
    
    # 加载配置
    config_manager = ConfigManager("config.yaml")
    config = config_manager.load_config()
    
    threshold = getattr(config.red_light_detection, 'count_decrease_threshold', 3)
    print(f"配置的触发阈值: {threshold}")
    print()
    
    # 测试不同的变化情况
    test_cases = [
        {"baseline": 10, "current": 10, "expected": False, "desc": "无变化"},
        {"baseline": 10, "current": 9, "expected": False, "desc": "减少1个"},
        {"baseline": 10, "current": 8, "expected": False, "desc": "减少2个"},
        {"baseline": 10, "current": 7, "expected": True, "desc": "减少3个"},
        {"baseline": 10, "current": 6, "expected": True, "desc": "减少4个"},
        {"baseline": 10, "current": 5, "expected": True, "desc": "减少5个"},
        {"baseline": 10, "current": 12, "expected": False, "desc": "增加2个"},
        {"baseline": 5, "current": 2, "expected": True, "desc": "减少3个"},
        {"baseline": 3, "current": 0, "expected": True, "desc": "减少3个"},
        {"baseline": 2, "current": 0, "expected": False, "desc": "减少2个"},
    ]
    
    print("测试用例:")
    print("基线 -> 当前 | 变化 | 是否触发 | 描述")
    print("-" * 50)
    
    for i, case in enumerate(test_cases):
        baseline = case["baseline"]
        current = case["current"]
        expected = case["expected"]
        desc = case["desc"]
        
        count_change = current - baseline
        should_trigger = count_change <= -threshold
        
        status = "✅" if should_trigger == expected else "❌"
        trigger_text = "触发" if should_trigger else "不触发"
        
        print(f"{baseline:2d} -> {current:2d}   | {count_change:+3d} | {trigger_text:4s}   | {desc} {status}")
    
    print()
    print("触发条件: 红光数量减少 >= 3个")
    print("✅ = 测试通过, ❌ = 测试失败")

def main():
    """主函数"""
    setup_logging()
    
    try:
        test_trigger_logic()
        print("\n🎯 触发阈值逻辑测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())