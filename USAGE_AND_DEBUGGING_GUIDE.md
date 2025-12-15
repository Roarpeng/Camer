# MQTT摄像头监控系统 - 使用和调试指南

## 系统启动方法

### 1. GUI模式启动（推荐）
```bash
# 激活虚拟环境
camer311\Scripts\activate

# 启动GUI界面
python gui_main.py
```

### 2. 命令行模式启动
```bash
# 激活虚拟环境
camer311\Scripts\activate

# 启动命令行版本
python main.py
```

### 3. 批处理文件启动
```bash
# 启动生产系统（无界面）
run_final_production_system.bat

# 启动生产系统（带可视化）
run_final_production_with_view.bat
```

## 系统配置

### USB摄像头检测和配置

#### 1. 检测可用摄像头
在配置系统之前，首先检测系统中可用的USB摄像头：

```bash
# 运行摄像头检测工具
python usb_camera_detector.py
```

输出示例：
```
正在检测USB摄像头...

发现 2 个摄像头:
------------------------------------------------------------
ID: 0
名称: USB2.0 HD UVC WebCam
描述: USB摄像头 0
分辨率: 1920x1080
帧率: 30.0 FPS
支持分辨率: 1920x1080, 1280x720, 640x480
------------------------------------------------------------
ID: 1
名称: Integrated Camera
描述: USB摄像头 1
分辨率: 1280x720
帧率: 30.0 FPS
支持分辨率: 1280x720, 640x480
------------------------------------------------------------
```

#### 2. 验证摄像头分辨率支持
确保选择的摄像头支持1920x1080分辨率（系统要求）：

```bash
# 检查特定摄像头的分辨率支持
python -c "
from usb_camera_detector import USBCameraDetector
detector = USBCameraDetector()
info = detector.get_camera_info(0)  # 替换为你的摄像头ID
if info and (1920, 1080) in info['supported_resolutions']:
    print('✓ 支持1920x1080分辨率')
else:
    print('✗ 不支持1920x1080分辨率，请选择其他摄像头')
"
```

### 摄像头配置
- 支持最多6个USB摄像头
- 每个摄像头需要配置：
  - **摄像头ID选择**：从USB设备列表中选择具体的USB摄像头名称（不是简单的数字0-5）
  - **掩码文件路径**：必须是1920x1080分辨率的PNG/JPG文件
  - **基线红光数量**：初始检测的红光数量基准值
  - **比较阈值**：触发检测的阈值差值

### 系统参数
- **延迟时间**：默认0.4秒，changeState消息处理延迟
- **监控间隔**：默认0.2秒，摄像头检测频率
- **比较阈值**：默认2，触发阈值

### MQTT配置
- 代理地址：192.168.10.80
- 客户端ID：receiver
- 订阅主题：changeState
- 发布主题：receiver/triggered

## 调试方法

### 1. 日志文件检查
#### 主要日志文件：
```bash
# GUI应用日志
gui_application.log

# 生产系统日志
final_production.log
```

#### 日志内容包括：
- MQTT连接状态
- 摄像头初始化信息
- 基线建立事件
- 触发事件详情
- 错误信息和异常

### 2. 实时状态监控

#### GUI界面监控：
- **左侧面板**：摄像头配置和状态
- **右侧面板**：系统状态和事件日志
- **MQTT状态**：连接状态和最后消息时间
- **基线事件**：显示基线建立的时间戳
- **触发事件**：显示设备ID和触发详情

#### 命令行监控：
```bash
# 查看实时日志
tail -f final_production.log

# 查看GUI日志
tail -f gui_application.log
```

### 3. 常见问题诊断

#### MQTT连接问题：
```bash
# 检查网络连接
ping 192.168.10.80

# 检查MQTT服务
telnet 192.168.10.80 1883
```

#### 摄像头问题：
```bash
# 检测可用的USB摄像头设备
python usb_camera_detector.py

# 或者简单检测摄像头索引
python -c "import cv2; print([i for i in range(10) if cv2.VideoCapture(i).isOpened()])"

# 检测特定摄像头的详细信息
python -c "
from usb_camera_detector import USBCameraDetector
detector = USBCameraDetector()
info = detector.get_camera_info(0)  # 检测摄像头0
print(f'摄像头信息: {info}')
"
```
#### 掩码文件问题：
```bash
# 检查掩码文件分辨率
python -c "import cv2; img=cv2.imread('mask.png'); print(f'分辨率: {img.shape}')"
```

#### 配置文件问题：
```bash
# 检查配置文件
cat config.yaml
```

### 4. 性能调试

#### 内存使用监控：
```bash
# 使用任务管理器监控python进程内存使用
# 或使用psutil
python -c "import psutil; print(f'内存使用: {psutil.virtual_memory().percent}%')"
```

#### CPU使用监控：
```bash
# 监控CPU使用率
python -c "import psutil; print(f'CPU使用: {psutil.cpu_percent()}%')"
```

### 5. 测试和验证

#### 运行完整测试套件：
```bash
# 运行所有测试
python -m pytest test_*.py -v

# 运行特定测试
python -m pytest test_integration_gui_system.py -v
```

#### 属性测试：
```bash
# 基线重置测试
python -m pytest test_property_baseline_reset.py -v

# 阈值触发测试
python -m pytest test_property_threshold_triggering.py -v

# 时序基线测试
python -m pytest test_property_timing_baseline.py -v
```
### 6. 故障排除步骤

#### 系统无法启动：
1. 检查虚拟环境是否激活
2. 验证所有依赖包是否安装：`pip install -r requirements.txt`
3. 检查Python版本兼容性
4. 查看启动日志中的错误信息

#### MQTT连接失败：
1. 确认网络连接：`ping 192.168.10.80`
2. 检查防火墙设置
3. 验证MQTT代理是否运行
4. 检查客户端ID冲突

#### 摄像头检测失败：
1. **确认摄像头硬件连接**
   ```bash
   # 检测USB设备
   python usb_camera_detector.py
   ```

2. **检查摄像头驱动程序**
   - Windows: 设备管理器 → 图像设备
   - Linux: `lsusb` 或 `v4l2-ctl --list-devices`

3. **验证摄像头ID配置**
   ```bash
   # 测试特定摄像头ID
   python -c "
   import cv2
   camera_id = 0  # 替换为你的摄像头ID
   cap = cv2.VideoCapture(camera_id)
   print(f'摄像头 {camera_id} 可用: {cap.isOpened()}')
   cap.release()
   "
   ```

4. **测试摄像头是否被其他程序占用**
   - 关闭所有可能使用摄像头的程序（Skype、Teams、浏览器等）
   - 重新运行检测工具

#### 掩码文件错误：
1. 确认文件路径正确
2. 验证文件格式（PNG/JPG）
3. 检查分辨率是否为1920x1080
4. 确认文件权限

#### 触发逻辑异常：
1. 检查基线值设置
2. 验证比较阈值配置
3. 确认延迟时间设置
4. 查看检测区域掩码

### 7. 调试工具和命令

#### 快速系统检查：
```bash
# 检查所有组件
python -c "
import final_production_system
import gui_main
import mqtt_camera_monitoring
print('所有模块导入成功')
"
```
#### 配置验证：
```bash
# 验证配置文件格式
python -c "
import yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    print('配置文件格式正确')
    print(f'配置内容: {config}')
"
```

#### 摄像头测试：
```bash
# 检测所有可用摄像头
python usb_camera_detector.py

# 测试特定摄像头
python -c "
import cv2
from usb_camera_detector import USBCameraDetector

detector = USBCameraDetector()
cameras = detector.detect_cameras()

for camera in cameras:
    print(f'摄像头ID: {camera[\"id\"]}, 名称: {camera[\"name\"]}')
    
    cap = cv2.VideoCapture(camera['id'])
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f'  - 工作正常，分辨率: {frame.shape}')
        cap.release()
    else:
        print('  - 无法打开')
"

# 测试摄像头是否支持1920x1080分辨率
python -c "
import cv2
cap = cv2.VideoCapture(0)  # 替换为你的摄像头ID
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
ret, frame = cap.read()
if ret:
    print(f'1920x1080分辨率支持: {frame.shape}')
else:
    print('不支持1920x1080分辨率')
cap.release()
"
```

#### MQTT连接测试：
```bash
# 测试MQTT连接
python -c "
import paho.mqtt.client as mqtt
client = mqtt.Client('test_client')
try:
    client.connect('192.168.10.80', 1883, 60)
    print('MQTT连接成功')
    client.disconnect()
except Exception as e:
    print(f'MQTT连接失败: {e}')
"
```

### 8. 生产环境部署建议

#### 系统要求：
- Windows 10/11
- Python 3.11+
- 至少4GB RAM
- USB 3.0端口（用于多摄像头）
- 稳定的网络连接

#### 性能优化：
- 使用SSD存储提高I/O性能
- 确保充足的USB带宽
- 定期清理日志文件
- 监控系统资源使用

#### 维护建议：
- 定期备份配置文件
- 监控日志文件大小
- 定期重启系统（建议每周）
- 保持系统和驱动程序更新
### 9. 紧急故障处理

#### 系统崩溃恢复：
1. 重启系统
2. 检查日志文件中的错误信息
3. 验证配置文件完整性
4. 重新初始化摄像头
5. 如果问题持续，使用备份配置

#### 数据丢失预防：
- 定期备份`config.yaml`
- 保存重要的掩码文件
- 记录关键配置参数
- 建立系统恢复流程

### 10. 联系和支持

#### 日志收集（用于技术支持）：
```bash
# 收集所有相关日志
copy gui_application.log logs_backup\
copy final_production.log logs_backup\
copy config.yaml logs_backup\
```

#### 系统信息收集：
```bash
# 生成系统报告
python -c "
import platform
import sys
import cv2
print(f'操作系统: {platform.system()} {platform.release()}')
print(f'Python版本: {sys.version}')
print(f'OpenCV版本: {cv2.__version__}')
"
```

---

## 快速使用步骤

### 1. 系统准备
```bash
# 激活虚拟环境
camer311\Scripts\activate

# 检测可用摄像头
python usb_camera_detector.py
```

### 2. 启动GUI系统
```bash
python gui_main.py
```

### 3. 配置摄像头（GUI左侧面板）
对于每个要使用的摄像头：

1. **启用摄像头**：勾选"启用"复选框
2. **选择摄像头ID**：从下拉列表中选择检测到的USB摄像头
   - 注意：应该选择支持1920x1080分辨率的摄像头
3. **设置掩码文件**：
   - 点击"浏览"按钮选择掩码文件
   - 确保掩码文件分辨率为1920x1080
4. **配置检测参数**：
   - 基线红光数量：根据实际环境设置
   - 比较阈值：默认2，可根据需要调整

### 4. 配置系统参数
- **延迟时间**：MQTT消息处理延迟（默认0.4秒）
- **监控间隔**：摄像头检测频率（默认0.2秒）
- **全局阈值**：全局比较阈值（默认2）

### 5. 启动监控
1. 点击"启动系统"按钮
2. 检查右侧面板的系统状态
3. 观察MQTT连接状态和事件日志

### 6. 监控和调试
- **右侧面板监控**：查看MQTT状态、基线事件、触发事件
- **日志文件**：查看 `gui_application.log` 和 `final_production.log`
- **实时状态**：观察摄像头状态和检测数据

---

## 快速参考

### 常用命令：
- 检测摄像头：`python usb_camera_detector.py`
- 启动GUI：`python gui_main.py`
- 运行测试：`python -m pytest test_*.py -v`
- 检查日志：`type gui_application.log`
- 测试摄像头：`python -c "from usb_camera_detector import USBCameraDetector; print(USBCameraDetector().detect_cameras())"`

### 重要文件：
- 主配置：`config.yaml`
- GUI日志：`gui_application.log`
- 系统日志：`final_production.log`
- 掩码文件：`mask.png`, `fmask.png`
- 摄像头检测：`usb_camera_detector.py`
- 详细配置指南：`camera_configuration_guide.md`

### 默认设置：
- MQTT代理：192.168.10.80:1883
- 延迟时间：0.4秒
- 监控间隔：0.2秒
- 比较阈值：2