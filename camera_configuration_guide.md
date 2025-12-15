# 摄像头配置详细指南

## 1. USB摄像头检测

### 检测系统中的摄像头
```bash
# 运行摄像头检测工具
python usb_camera_detector.py
```

### 如果没有检测到摄像头
可能的原因和解决方案：

1. **没有连接USB摄像头**
   - 连接USB摄像头到计算机
   - 确保USB端口工作正常

2. **摄像头被其他程序占用**
   ```bash
   # 关闭可能占用摄像头的程序：
   # - Skype, Teams, Zoom等视频会议软件
   # - 浏览器中的视频通话页面
   # - 其他摄像头应用程序
   ```

3. **驱动程序问题**
   - Windows: 检查设备管理器中的"图像设备"
   - 更新或重新安装摄像头驱动程序

4. **权限问题（Linux）**
   ```bash
   # 添加用户到video组
   sudo usermod -a -G video $USER
   # 重新登录后生效
   ```

## 2. 摄像头配置要求

### 分辨率要求
- **必须支持1920x1080分辨率**
- 系统使用的掩码文件都是基于1920x1080分辨率制作

### 验证摄像头分辨率支持
```bash
python -c "
import cv2
camera_id = 0  # 替换为你的摄像头ID

cap = cv2.VideoCapture(camera_id)
if cap.isOpened():
    # 设置为1920x1080
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    # 读取一帧
    ret, frame = cap.read()
    if ret and frame is not None:
        actual_resolution = frame.shape[:2][::-1]  # (width, height)
        if actual_resolution == (1920, 1080):
            print('✓ 摄像头支持1920x1080分辨率')
        else:
            print(f'✗ 摄像头实际分辨率: {actual_resolution}')
    else:
        print('✗ 无法读取摄像头画面')
    cap.release()
else:
    print('✗ 无法打开摄像头')
"
```

## 3. GUI配置步骤

### 步骤1：启动GUI
```bash
camer311\Scripts\activate
python gui_main.py
```

### 步骤2：配置摄像头（左侧面板）

#### 对于每个摄像头配置行：

1. **启用摄像头**
   - 勾选"启用"复选框
   - 只有启用的摄像头才会参与监控

2. **选择摄像头ID**
   - 从下拉列表选择摄像头ID（0-5）
   - 确保选择的ID对应实际连接的摄像头
   - 避免重复选择同一个物理摄像头

3. **设置掩码文件路径**
   - 点击"浏览"按钮选择掩码文件
   - 掩码文件必须是1920x1080分辨率
   - 支持PNG和JPG格式
   - 掩码文件定义了检测区域（白色区域为检测区域）

4. **配置基线红光数量**
   - 设置初始基线值
   - 系统会在运行时动态建立实际基线

5. **设置比较阈值**
   - 默认值为2
   - 当检测到的红光数量比基线少这个数值时触发

### 步骤3：配置系统参数

- **延迟时间（秒）**：默认0.4秒
  - MQTT消息更新后等待多长时间再建立基线
  
- **监控间隔（秒）**：默认0.2秒
  - 摄像头检测的频率
  
- **全局比较阈值**：默认2
  - 全局的触发阈值设置

### 步骤4：验证配置

在启动系统前，确保：
- [ ] 至少启用了一个摄像头
- [ ] 所有启用的摄像头都有有效的掩码文件
- [ ] 没有重复使用同一个物理摄像头ID
- [ ] 掩码文件路径正确且文件存在
- [ ] MQTT代理地址正确（192.168.10.80）

## 4. 常见配置问题

### 问题1：摄像头无法打开
```bash
# 检查摄像头是否被占用
python -c "
import cv2
for i in range(6):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f'摄像头 {i}: 可用')
        cap.release()
    else:
        print(f'摄像头 {i}: 不可用')
"
```

### 问题2：掩码文件错误
```bash
# 检查掩码文件分辨率
python -c "
import cv2
mask_path = 'mask.png'  # 替换为你的掩码文件路径
img = cv2.imread(mask_path)
if img is not None:
    height, width = img.shape[:2]
    print(f'掩码文件分辨率: {width}x{height}')
    if width == 1920 and height == 1080:
        print('✓ 分辨率正确')
    else:
        print('✗ 分辨率不正确，需要1920x1080')
else:
    print('✗ 无法读取掩码文件')
"
```

### 问题3：重复摄像头ID
- GUI会自动检测并提示重复的摄像头ID
- 确保每个启用的摄像头使用不同的物理ID

### 问题4：MQTT连接失败
```bash
# 测试MQTT连接
python -c "
import paho.mqtt.client as mqtt
import time

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print('✓ MQTT连接成功')
    else:
        print(f'✗ MQTT连接失败，错误码: {rc}')

client = mqtt.Client('test_client')
client.on_connect = on_connect

try:
    client.connect('192.168.10.80', 1883, 60)
    client.loop_start()
    time.sleep(2)
    client.loop_stop()
    client.disconnect()
except Exception as e:
    print(f'✗ MQTT连接异常: {e}')
"
```

## 5. 测试配置

### 完整系统测试
```bash
# 运行集成测试
python -m pytest test_integration_gui_system.py -v

# 运行GUI测试
python -m pytest test_gui_integration.py -v
```

### 单独测试摄像头
```bash
# 测试摄像头捕获
python -c "
import cv2
import time

camera_id = 0  # 替换为你的摄像头ID
cap = cv2.VideoCapture(camera_id)

if cap.isOpened():
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    print('开始测试摄像头捕获...')
    for i in range(10):
        ret, frame = cap.read()
        if ret:
            print(f'帧 {i+1}: {frame.shape}')
        else:
            print(f'帧 {i+1}: 捕获失败')
        time.sleep(0.1)
    
    cap.release()
    print('测试完成')
else:
    print('无法打开摄像头')
"
```

## 6. 配置文件

### 自动保存配置
- GUI会自动保存配置到 `config.yaml`
- 每次参数更改都会立即保存

### 手动备份配置
```bash
# 备份当前配置
copy config.yaml config_backup.yaml

# 恢复配置
copy config_backup.yaml config.yaml
```

### 配置文件格式示例
```yaml
cameras:
  - camera_id: 0
    enabled: true
    physical_camera_id: 0
    mask_path: "mask.png"
    baseline_count: 10
    threshold: 2
  - camera_id: 1
    enabled: false
    physical_camera_id: 1
    mask_path: ""
    baseline_count: 0
    threshold: 2

system_parameters:
  delay_time: 0.4
  monitoring_interval: 0.2
  global_threshold: 2
```

这个配置指南应该能帮助您正确配置和使用MQTT摄像头监控系统。