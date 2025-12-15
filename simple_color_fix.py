#!/usr/bin/env python3
"""
简单彩色修复
直接修复摄像头彩色问题，不搞复杂测试
"""

import cv2
import numpy as np
import time

def simple_color_test():
    """简单彩色测试"""
    
    print("=== 简单彩色修复 ===")
    print("直接修复摄像头彩色问题")
    print()
    
    # 最简单的摄像头初始化
    cap = cv2.VideoCapture(0)  # 不指定后端，让系统自动选择
    
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return False
    
    print("摄像头打开成功，使用默认设置...")
    
    # 只设置最基本的参数
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # 不设置任何颜色相关的参数，让摄像头使用默认设置
    
    # 预热
    for i in range(5):
        ret, frame = cap.read()
        time.sleep(0.1)
    
    # 捕获测试帧
    ret, frame = cap.read()
    
    if ret and frame is not None:
        print(f"捕获帧尺寸: {frame.shape}")
        
        if len(frame.shape) == 3:
            b_avg = np.mean(frame[:,:,0])
            g_avg = np.mean(frame[:,:,1])
            r_avg = np.mean(frame[:,:,2])
            
            print(f"BGR平均值: B={b_avg:.1f}, G={g_avg:.1f}, R={r_avg:.1f}")
            
            color_variance = np.var([b_avg, g_avg, r_avg])
            print(f"颜色方差: {color_variance:.2f}")
            
            if color_variance > 1:  # 降低阈值
                print("✓ 检测到彩色图像")
                result = True
            else:
                print("✗ 仍然是灰度图像")
                result = False
            
            # 保存图像
            cv2.imwrite("simple_color_test.jpg", frame)
            print(f"图像已保存: simple_color_test.jpg")
            
        else:
            print("✗ 捕获的是灰度图像")
            result = False
    else:
        print("[ERROR] 无法捕获帧")
        result = False
    
    cap.release()
    return result

def test_different_backends():
    """测试不同后端，找到彩色的"""
    
    print("\n=== 测试不同后端 ===")
    
    # 简单测试几个主要后端
    backends = [
        (cv2.CAP_ANY, "Auto"),
        (cv2.CAP_DSHOW, "DirectShow"), 
        (cv2.CAP_MSMF, "MediaFoundation")
    ]
    
    for backend, name in backends:
        print(f"\n--- 测试 {name} ---")
        
        try:
            cap = cv2.VideoCapture(0, backend)
            
            if cap.isOpened():
                # 最简单的设置
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                
                time.sleep(0.5)
                
                ret, frame = cap.read()
                
                if ret and frame is not None and len(frame.shape) == 3:
                    b_avg = np.mean(frame[:,:,0])
                    g_avg = np.mean(frame[:,:,1])
                    r_avg = np.mean(frame[:,:,2])
                    
                    color_variance = np.var([b_avg, g_avg, r_avg])
                    
                    print(f"  BGR: ({b_avg:.1f}, {g_avg:.1f}, {r_avg:.1f})")
                    print(f"  方差: {color_variance:.2f}")
                    
                    if color_variance > 1:
                        print(f"  ✓ {name} 支持彩色")
                        
                        # 保存成功的图像
                        filename = f"color_success_{name}.jpg"
                        cv2.imwrite(filename, frame)
                        print(f"  保存: {filename}")
                        
                        cap.release()
                        return backend, name
                    else:
                        print(f"  ✗ {name} 是灰度")
                else:
                    print(f"  ✗ {name} 无法捕获帧")
                
                cap.release()
            else:
                print(f"  ✗ {name} 无法打开")
                
        except Exception as e:
            print(f"  ✗ {name} 错误: {e}")
    
    return None, None

def update_red_detection_analyzer():
    """更新红色检测分析器使用正确的后端"""
    
    print("\n=== 更新红色检测分析器 ===")
    
    # 找到工作的后端
    backend, backend_name = test_different_backends()
    
    if backend is None:
        print("[ERROR] 没有找到支持彩色的后端")
        return False
    
    print(f"\n找到工作的后端: {backend_name}")
    
    # 读取红色检测分析器文件
    try:
        with open("red_detection_analyzer.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 备份原文件
        with open("red_detection_analyzer.py.backup", "w", encoding="utf-8") as f:
            f.write(content)
        
        # 修改后端设置
        if backend == cv2.CAP_ANY:
            # 使用自动后端
            new_line = "                    cap = cv2.VideoCapture(camera_id)  # 使用自动后端"
        else:
            new_line = f"                    cap = cv2.VideoCapture(camera_id, {backend})  # 使用{backend_name}后端"
        
        # 替换后端设置行
        import re
        content = re.sub(
            r'cap = cv2\.VideoCapture\(camera_id, [^)]+\)',
            new_line.strip(),
            content
        )
        
        # 移除所有复杂的颜色设置，只保留基本设置
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            # 跳过复杂的颜色设置
            if 'CAP_PROP_CONVERT_RGB' in line or 'CAP_PROP_FOURCC' in line:
                continue
            new_lines.append(line)
        
        content = '\n'.join(new_lines)
        
        # 保存修改后的文件
        with open("red_detection_analyzer.py", "w", encoding="utf-8") as f:
            f.write(content)
        
        print("red_detection_analyzer.py 已更新")
        return True
        
    except Exception as e:
        print(f"[ERROR] 更新文件失败: {e}")
        return False

def main():
    """主函数"""
    
    print("摄像头本身是彩色的，问题出在代码配置上")
    print("让我直接修复这个问题")
    print()
    
    # 1. 简单测试
    if simple_color_test():
        print("\n✓ 使用默认设置就能获得彩色图像")
        print("问题解决！")
    else:
        print("\n需要找到正确的后端...")
        
        # 2. 更新分析器
        if update_red_detection_analyzer():
            print("\n✓ 红色检测分析器已更新")
            print("现在可以运行: run_red_detection_analyzer.bat")
        else:
            print("\n✗ 更新失败")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())