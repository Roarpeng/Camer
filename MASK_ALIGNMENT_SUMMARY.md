# Mask对齐完成总结

## 问题描述
- 原始mask图片 (m.png) 尺寸: 768x1376 (高x宽)
- 摄像头不支持1376x768分辨率
- 需要实现mask和摄像头分辨率对齐

## 解决方案
1. **检测摄像头支持的分辨率**
   - 摄像头支持: 640x480, 800x600, 1024x768, 1280x720, 1280x960, 1920x1080
   - 最接近mask尺寸的是: 1280x720 (720p)

2. **实现智能mask缩放**
   - 自动将mask从768x1376缩放到720x1280
   - 使用INTER_NEAREST插值保持mask的二值特性
   - 缩放后检测点数: 49,088个

3. **统一分辨率配置**
   - 更新config.yaml: 1280x720
   - 更新所有相关Python文件的摄像头配置
   - 确保所有工具使用相同的720p分辨率

## 完成的文件更新

### 配置文件
- `config.yaml` - 摄像头分辨率设置

### 核心检测系统
- `mask_based_detection_system.py` - 主要的mask检测系统
- `mask_detection_visualizer.py` - mask检测可视化工具
- `red_light_detection_system.py` - 原有的红光检测系统

### 测试和调试工具
- `test_mask_alignment.py` - 完整的对齐测试工具
- `quick_mask_alignment_test.py` - 快速对齐验证
- `test_mask_detection_simple.py` - 简化的mask检测测试
- `check_camera_resolutions.py` - 摄像头分辨率检查工具

### 其他相关文件
- `quick_detection_test.py`
- `debug_detection.py`
- `mqtt_camera_monitoring/async_camera_manager.py`
- `detection_status_display.py`
- `camera_erosion_tuner.py`
- `camera_exposure_test.py`

### 批处理文件
- `run_mask_detection_system.bat` - 运行完整mask检测系统
- `run_simple_mask_test.bat` - 运行简化测试
- `run_alignment_test.bat` - 运行对齐测试

## 验证结果
✅ **对齐测试成功**
- Mask缩放: 768x1376 → 720x1280
- 摄像头输出: 720x1280
- 所有49,088个mask点都在帧范围内

## 使用说明

### 1. 快速验证对齐
```bash
run_alignment_test.bat
```

### 2. 简化mask检测测试
```bash
run_simple_mask_test.bat
```
- 不需要MQTT连接
- 实时显示mask区域
- 按空格键建立基线
- 检测颜色变化

### 3. 完整mask检测系统
```bash
run_mask_detection_system.bat
```
- 需要MQTT服务器连接
- 完整的检测和上报功能

## 技术细节

### Mask缩放算法
- 使用cv2.INTER_NEAREST插值
- 保持mask的二值特性
- 自动适配目标分辨率

### 检测逻辑
1. 加载mask并缩放到720p
2. 提取白色区域坐标点
3. 建立基线颜色状态
4. 实时监控颜色变化
5. 检测红色光点的出现/消失

### 红色检测参数
- HSV范围1: [0,50,50] - [10,255,255]
- HSV范围2: [170,50,50] - [180,255,255]
- 支持红色色调的环绕特性

## 下一步工作
1. 集成mask检测到主要监控系统
2. 优化检测算法的敏感度
3. 添加更多的颜色变化检测模式
4. 完善MQTT触发逻辑