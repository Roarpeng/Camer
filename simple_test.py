#!/usr/bin/env python3
"""
简单测试脚本 - 诊断视窗显示问题
"""

import cv2
import numpy as np
import time
import sys

def test_basic_opencv():
    """测试基础OpenCV功能"""
    print("测试基础OpenCV功能...")
    
    try:
        # 创建测试画面
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (50, 100, 150)  # 蓝色背景
        
        # 添加文字
        cv2.putText(frame, "OpenCV Test", (200, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        
        # 创建窗口
        cv2.namedWindow("OpenCV Test", cv2.WINDOW_NORMAL)
        cv2.imshow("OpenCV Test", frame)
        
        print("✓ OpenCV基础功能正常")
        print("按任意键继续...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return True
        
    except Exception as e:
        print(f"❌ OpenCV测试失败: {e}")
        return False

def test_multiple_windows():
    """测试多个窗口"""
    print("测试多个窗口...")
    
    try:
        windows = []
        
        # 创建6个窗口
        for i in range(6):
            window_name = f"Test Window {i}"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 320, 240)
            
            # 排列窗口
            col = i % 3
            row = i // 3
            x = col * 330
            y = row * 270
            cv2.moveWindow(window_name, x, y)
            
            windows.append(window_name)
            
            # 创建不同颜色的画面
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), 
                     (255, 255, 0), (255, 0, 255), (0, 255, 255)]
            frame[:] = colors[i]
            
            # 添加窗口标识
            cv2.putText(frame, f"Window {i}", (50, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            cv2.imshow(window_name, frame)
        
        print("✓ 6个窗口创建成功")
        print("按 'q' 键退出...")
        
        # 保持窗口显示
        while True:
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
        
        cv2.destroyAllWindows()
        return True
        
    except Exception as e:
        print(f"❌ 多窗口测试失败: {e}")
        return False

def test_tkinter():
    """测试tkinter GUI"""
    print("测试tkinter GUI...")
    
    try:
        import tkinter as tk
        from tkinter import ttk
        
        root = tk.Tk()
        root.title("Tkinter Test")
        root.geometry("400x300")
        
        label = ttk.Label(root, text="Tkinter GUI 测试成功！", font=("Arial", 16))
        label.pack(pady=50)
        
        button = ttk.Button(root, text="关闭", command=root.destroy)
        button.pack(pady=20)
        
        print("✓ Tkinter GUI创建成功")
        print("关闭GUI窗口继续...")
        
        root.mainloop()
        return True
        
    except Exception as e:
        print(f"❌ Tkinter测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("🔧 视窗显示问题诊断测试")
    print("=" * 50)
    
    # 测试1: 基础OpenCV
    if not test_basic_opencv():
        print("基础OpenCV测试失败，请检查OpenCV安装")
        return
    
    print("\n" + "=" * 30)
    
    # 测试2: 多个窗口
    if not test_multiple_windows():
        print("多窗口测试失败")
        return
    
    print("\n" + "=" * 30)
    
    # 测试3: Tkinter GUI
    if not test_tkinter():
        print("Tkinter GUI测试失败")
        return
    
    print("\n✅ 所有基础测试通过！")
    print("如果这些测试都正常，问题可能在于增强监控组件的实现")

if __name__ == "__main__":
    main()