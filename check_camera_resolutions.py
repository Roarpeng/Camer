#!/usr/bin/env python3
"""
检查摄像头支持的分辨率
"""

import cv2

def check_camera_resolutions():
    """检查摄像头支持的分辨率"""
    
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return
    
    print("=== 摄像头分辨率检查 ===")
    
    # 常见分辨率列表
    resolutions = [
        (640, 480),    # VGA
        (800, 600),    # SVGA
        (1024, 768),   # XGA
        (1280, 720),   # HD 720p
        (1280, 960),   # SXGA
        (1376, 768),   # 目标分辨率
        (1920, 1080),  # Full HD 1080p
        (2560, 1440),  # QHD
    ]
    
    supported = []
    
    for width, height in resolutions:
        # 设置分辨率
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # 读取实际分辨率
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 测试是否能读取帧
        ret, frame = cap.read()
        
        if ret and frame is not None:
            frame_shape = frame.shape[:2]  # (height, width)
            
            print(f"设置: {width}x{height} -> 实际: {actual_width}x{actual_height} -> 帧: {frame_shape[1]}x{frame_shape[0]}")
            
            if actual_width == width and actual_height == height:
                supported.append((width, height))
                print(f"  ✓ 完全支持")
            elif frame_shape == (height, width):
                supported.append((width, height))
                print(f"  ✓ 帧匹配")
            else:
                print(f"  ✗ 不匹配")
        else:
            print(f"设置: {width}x{height} -> 无法读取帧")
    
    cap.release()
    
    print(f"\n支持的分辨率: {len(supported)} 个")
    for width, height in supported:
        print(f"  {width}x{height}")
    
    # 检查mask尺寸
    mask_img = cv2.imread("m.png")
    if mask_img is not None:
        mask_shape = mask_img.shape
        print(f"\nMask尺寸: {mask_shape[1]}x{mask_shape[0]} (宽x高)")
        
        # 查找最接近的支持分辨率
        mask_width, mask_height = mask_shape[1], mask_shape[0]
        
        best_match = None
        min_diff = float('inf')
        
        for width, height in supported:
            diff = abs(width - mask_width) + abs(height - mask_height)
            if diff < min_diff:
                min_diff = diff
                best_match = (width, height)
        
        if best_match:
            print(f"最接近的支持分辨率: {best_match[0]}x{best_match[1]}")
            print(f"差异: 宽度{abs(best_match[0] - mask_width)}, 高度{abs(best_match[1] - mask_height)}")

if __name__ == "__main__":
    check_camera_resolutions()