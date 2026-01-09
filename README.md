# Camer

一个支持多路 USB 摄像头的计算机视觉监控应用，具备实时画面处理、掩码（Mask）分析、自动基准建立、亮度扫描及 MQTT 远程控制功能。项目采用 Material Design 设计风格，提供现代化的用户界面体验。

## 功能特性

- **多路摄像头监控**: 支持 3 路摄像头同时监控
- **实时图像处理**: 帧差分析、掩码应用、变化检测
- **自动基准建立**: 系统接收到第一帧图像时自动建立初始基准
- **亮度扫描**: 可配置的 ROI 区域亮度扫描（默认 300ms）
- **MQTT 远程控制**: 支持通过 MQTT 接收控制命令和上报状态
- **报警机制**: 检测到像素变化或亮度波动时触发报警
- **智能触发**: 基线建立后只触发一次上报，避免重复
- **灵活配置**: 所有参数可通过 UI 或配置文件配置
- **自动启动**: 支持自动连接 broker 和激活摄像头

## 技术栈

- **编程语言**: Python 3.11
- **GUI 框架**: PySide6 (Qt6)
- **图像处理**: OpenCV (cv2)
- **数值计算**: Numpy
- **通信协议**: MQTT (paho-mqtt)
- **打包工具**: PyInstaller

## 项目结构

```
Camer/
├── run.py                      # 主入口文件
├── CamerApp.spec              # PyInstaller 打包规范
├── visual.ico                 # 应用图标
├── data/                      # 掩码文件目录
│   ├── 1.png
│   ├── 2.png
│   └── 3.png
├── src/
│   ├── main.py                # 应用主程序
│   ├── core/
│   │   ├── camera.py          # 摄像头线程（QThread）
│   │   ├── processor.py       # 图像处理器
│   │   └── mqtt_client.py     # MQTT 客户端
│   ├── gui/
│   │   ├── main_window.py     # 主窗口
│   │   ├── widgets.py         # 自定义控件
│   │   └── style.py           # Material Design 样式
│   └── utils/
│       ├── config.py          # 配置管理
│       └── logger.py          # 日志工具
├── camer311/                  # Python 3.11 虚拟环境
├── build/                     # PyInstaller 构建输出
└── dist/                      # PyInstaller 最终输出
    └── CamerApp.exe           # 可执行文件
```

## 快速开始

### 环境要求

- Python 3.11
- Windows 操作系统

### 依赖安装

```bash
# 创建虚拟环境
python -m venv camer311

# 激活虚拟环境
camer311\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

主要依赖：
- PySide6 6.10.1
- opencv-python 4.12.0.88
- paho-mqtt 1.6.1
- numpy 2.2.6
- Pillow (中文显示支持)
- PyInstaller 6.17.0

### 运行应用

```bash
# 激活虚拟环境
camer311\Scripts\activate

# 运行应用
python run.py
```

### 打包为可执行文件

```bash
# 激活虚拟环境
camer311\Scripts\activate

# 使用 PyInstaller 打包
pyinstaller CamerApp.spec

# 打包后的可执行文件位于 dist/CamerApp.exe
```

## 配置说明

### 配置文件

应用启动后会自动创建 `config.json` 配置文件，支持以下配置：

```json
{
  "mqtt": {
    "broker": "localhost",
    "client_id": "camer",
    "subscribe_topics": ["changeState", "receiver"],
    "publish_topic": "receiver",
    "auto_connect": true
  },
  "cameras": [
    {
      "active": false,
      "mask": "",
      "threshold": 50,
      "min_area": 500,
      "scan_interval": 300
    }
  ]
}
```

### MQTT 配置

- **ClientID**: 用于标识 MQTT 客户端身份（默认：`camer`）
- **订阅主题**: 接收控制命令和上报消息（默认：`changeState, receiver`）
- **发布主题**: 上报亮度变化（默认：`receiver`）
- **控制命令**: 接收到 `{"state":[1,1,1,2,0,...]}` 中包含 `2` 时触发全局基准重置

### 摄像头参数

- **Sensitivity（阈值）**: 像素差异触发门限（默认 50，范围 1-255）
- **Min Area（最小面积）**: 过滤噪点，只有达到此面积的变化才触发报警（默认 500，范围 1-5000）
- **扫描间隔**: 亮度扫描时间间隔（默认 300ms，范围 100-5000ms）

## 使用说明

### 界面布局

采用三栏式 Material Design 布局：

- **左侧面板**: 配置与控制（MQTT 配置、摄像头激活、掩码选择、灵敏度调节）
- **中间面板**: 实时监控（3 路摄像头画面）
- **右侧面板**: 系统日志

### 工作流程

1. **配置 MQTT**: 设置 broker 地址、主题和 Client ID
2. **激活摄像头**: 选择要监控的摄像头并配置参数
3. **选择掩码**: 可选，用于指定 ROI 区域
4. **建立基线**: 通过 MQTT 发送包含 `2` 的 `changeState` 命令建立基线
5. **监控运行**: 系统自动进行帧差分析和亮度扫描
6. **报警触发**: 检测到变化时在画面上显示红色检测框并上报

### 掩码逻辑

- 未选择掩码时显示完整图像
- 选择掩码后仅显示 ROI（非感兴趣区域全黑处理）
- 算法仅处理掩码区域

## 核心处理逻辑

### 图像处理流程

1. **基准建立**: 收到 MQTT 命令后建立初始基准
2. **帧差分析**: 计算当前帧与基准帧的绝对差值
3. **阈值处理**: 应用阈值提取变化区域
4. **掩码应用**: 如果选择了掩码，仅处理掩码区域
5. **变化检测**: 统计变化像素数量，超过最小面积则触发报警
6. **亮度扫描**: 按配置间隔计算 ROI 区域的均值亮度，显著变化时上报

### 报警机制

1. **像素变化报警**: 帧差面积超过 `Min Area` 时在画面上绘制红色检测框
2. **亮度变化上报**: ROI 亮度波动超过阈值时向 MQTT 发布主题发送空报文

## 常见问题

### 摄像头无法打开

检查摄像头连接和索引，确保摄像头未被其他程序占用。

### MQTT 连接失败

检查 Broker 地址和网络连接。

### 掩码文件未显示

确保 `data/` 目录下存在 PNG 或 JPG 格式的掩码文件。

### 中文显示异常

确保已安装 Pillow 库，系统会自动加载 Windows 中文字体。

## 架构设计

项目采用清晰的分层架构：

1. **MqttWorker**: 独立 QObject 管理 MQTT 连接、重连及消息收发逻辑
2. **ImageProcessor**: 封装 OpenCV 算法逻辑，支持掩码管理及亮度计算
3. **CameraThread**: 利用 QThread 确保视频采集不阻塞主界面
4. **MainWindow**: 主窗口，协调各组件并管理业务逻辑

## 版本信息

- **项目名称**: Camer
- **Python 版本**: 3.11
- **最后更新**: 2026-01-09
- **Git 仓库**: git@github.com:Roarpeng/Camer.git

## 许可证

本项目采用 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### 2026-01-09 - UI 布局深度优化与架构重构

- 引入左侧滚动条，解决布局挤压问题
- 组件垂直化重构，提升调节体验
- 视觉主题精调，采用 Ant Design 风格

### 2026-01-08 - MQTT Client ID 配置功能

- 支持自定义 MQTT Client ID
- 多实例支持，不同实例可使用不同的 Client ID

### 2026-01-08 - 自动配置与打包发布

- 支持自动连接 broker 和激活摄像头
- 配置持久化，所有参数自动保存和加载
- 打包为单文件 exe，易于部署

### 2026-01-08 - UI 乱码修复与智能触发优化

- 修复中文显示问题，支持 Windows 中文字体
- 智能触发机制，基线建立后只触发一次上报
- 添加扫描间隔配置功能

### 2026-01-08 - MQTT 发布修复与主题配置增强

- 修复 MQTT 发布逻辑中的关键 bug
- 支持自定义订阅和发布主题
- 配置持久化，主题配置自动保存和加载

### 2026-01-08 - 基线建立逻辑优化

- 支持 JSON 格式的 `changeState` 报文
- 亮度变化检测使用 UI 参数，提供更灵活的控制