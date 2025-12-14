#!/usr/bin/env python3
"""
最小化测试 - 只测试窗口创建
"""

import cv2
import numpy as np

def main():
    print("最小化窗口测试...")
    
    try:
        # 创建6个窗口
        for i in range(6):
            window_name = f"摄像头 {i}"
            print(f"创建窗口: {window_name}")
            
            # 创建窗口
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 400, 300)
            
            # 排列窗口
            col = i % 3
            row = i // 3
            x = col * 410
            y = row * 350
            cv2.moveWindow(window_name, x, y)
            
            # 创建测试画面
            frame = np.zeros((300, 400, 3), dtype=np.uint8)
            colors = [(255, 100, 100), (100, 255, 100), (100, 100, 255),
                     (255, 255, 100), (255, 100, 255), (100, 255, 255)]
            frame[:] = colors[i]
            
            # 添加文字
            cv2.putText(frame, f"Camera {i}", (100, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
            
            # 显示画面
            cv2.imshow(window_name, frame)
        
        print("✓ 6个窗口创建完成")
        print("按 'q' 键退出...")
        
        # 等待用户输入
        while True:
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
        
        cv2.destroyAllWindows()
        print("✓ 测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()