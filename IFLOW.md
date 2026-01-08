# Camer 项目说明

## 项目概述

Camer 是一个支持多路 USB 摄像头的计算机视觉监控应用，具备实时画面处理、掩码（Mask）分析、自动基准建立、亮度扫描及 MQTT 远程控制功能。项目采用 Material Design 设计风格，提供现代化的用户界面体验。

### 核心技术栈

- **编程语言**: Python 3.11
- **GUI 框架**: PySide6 (Qt6)
- **图像处理**: OpenCV (cv2)
- **数值计算**: Numpy
- **通信协议**: MQTT (paho-mqtt)
- **打包工具**: PyInstaller

### 主要功能

1. **多路摄像头监控**: 支持 3 路摄像头同时监控
2. **实时图像处理**: 帧差分析、掩码应用、变化检测
3. **自动基准建立**: 系统接收到第一帧图像时自动建立初始基准
4. **亮度扫描**: 每 300ms 对 ROI 区域进行均值亮度扫描
5. **MQTT 远程控制**: 支持通过 MQTT 接收控制命令和上报状态
6. **报警机制**: 检测到像素变化或亮度波动时触发报警

## 项目结构

```
Camer/
├── run.py                      # 主入口文件
├── CamerApp.spec              # PyInstaller 打包规范
├── spec.md                    # 项目规格说明书
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
│       └── logger.py          # 日志工具
├── camer311/                  # Python 3.11 虚拟环境
├── build/                     # PyInstaller 构建输出
└── dist/                      # PyInstaller 最终输出
    └── CamerApp.exe           # 可执行文件
```

## 构建与运行

### 环境准备

项目使用 Python 3.11 虚拟环境（`camer311`），主要依赖包括：

- PySide6 6.10.1
- opencv-python 4.12.0.88
- paho-mqtt 1.6.1
- numpy 2.2.6
- PyInstaller 6.17.0

### 开发环境运行

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

### 打包说明

- 使用 `CamerApp.spec` 配置文件进行打包
- 自动包含 `data/` 目录中的掩码文件
- 使用 `visual.ico` 作为应用图标
- 无控制台窗口（`console=False`）
- 使用 UPX 压缩可执行文件

## 开发约定

### 代码风格

- **GUI 框架**: 使用 PySide6 的 Signal/Slot 机制进行组件间通信
- **多线程**: 摄像头采集使用 `QThread`，确保不阻塞主界面
- **日志系统**: 使用 Python `logging` 模块，日志通过 Signal 传递到 GUI 显示
- **资源路径**: 使用 `get_resource_path()` 函数处理开发环境和打包环境的路径差异

### 架构设计

项目采用清晰的分层架构：

1. **MqttWorker**: 独立 QObject 管理 MQTT 连接、重连及消息收发逻辑
2. **ImageProcessor**: 封装 OpenCV 算法逻辑，支持掩码管理及亮度计算
3. **CameraThread**: 利用 QThread 确保视频采集不阻塞主界面
4. **MainWindow**: 主窗口，协调各组件并管理业务逻辑

### MQTT 配置

- **ClientID**: `camer`
- **订阅主题**: 
  - `changeState` - 接收控制命令
  - `receiver` - 接收上报消息
- **发布主题**: `receiver` - 上报亮度变化
- **控制命令**: 接收到 `"2"` 时触发全局基准重置

### 界面布局

采用三栏式 Material Design 布局：

- **左侧面板**: 配置与控制（MQTT 配置、摄像头激活、掩码选择、灵敏度调节）
- **中间面板**: 实时监控（3 路摄像头画面）
- **右侧面板**: 系统日志

### 关键参数

- **Sensitivity（阈值）**: 像素差异触发门限（默认 50，范围 1-255）
- **Min Area（最小面积）**: 过滤噪点，只有达到此面积的变化才触发报警（默认 500，范围 1-5000）
- **亮度扫描间隔**: 300ms
- **亮度变化阈值**: 10（与基准亮度的差值）

## 核心处理逻辑

### 图像处理流程

1. **基准建立**: 系统接收到第一帧图像时自动建立初始基准
2. **帧差分析**: 计算当前帧与基准帧的绝对差值
3. **阈值处理**: 应用阈值提取变化区域
4. **掩码应用**: 如果选择了掩码，仅处理掩码区域
5. **变化检测**: 统计变化像素数量，超过最小面积则触发报警
6. **亮度扫描**: 每 300ms 计算 ROI 区域的均值亮度，显著变化时上报

### 掩码逻辑

- 未选择掩码时显示完整图像
- 选择掩码后仅显示 ROI（非感兴趣区域全黑处理）
- 算法仅处理掩码区域

### 报警机制

1. **像素变化报警**: 帧差面积超过 `Min Area` 时在画面上绘制红色检测框
2. **亮度变化上报**: ROI 亮度波动超过阈值时向 MQTT `receiver` 主题发布空报文

## 测试与调试

### 日志查看

应用右侧面板实时显示系统日志，包括：
- 系统初始化信息
- 摄像头状态
- MQTT 连接事件
- 亮度变化触发

### 常见问题

1. **摄像头无法打开**: 检查摄像头连接和索引，确保摄像头未被其他程序占用
2. **MQTT 连接失败**: 检查 Broker 地址和网络连接
3. **掩码文件未显示**: 确保 `data/` 目录下存在 PNG 或 JPG 格式的掩码文件

## 资源路径处理

项目使用 `get_resource_path()` 函数处理资源路径，确保在开发环境和打包环境下都能正确访问资源文件：

```python
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)
```

## 更新日志

### 2026-01-08 - 基线建立逻辑优化

#### MQTT 客户端改进 (mqtt_client.py)
- **JSON 报文解析**: 支持解析 JSON 格式的 `changeState` 报文
  - 支持格式：`{"state":[1,1,1,2,0,...,1,1,1]}`（144个元素）
  - 检测到 `state` 数组中包含 `2` 时触发基线建立
  - 保留向后兼容性：JSON 解析失败时仍支持字符串匹配
- **基线触发机制**: 监听 `changeState` 主题，自动检测基线建立指令

#### 主窗口逻辑优化 (main_window.py)
- **亮度变化检测**: 改为使用处理器的 `threshold` 参数作为亮度变化阈值
  - 替换之前的固定值 `10`
  - 与 UI 上的灵敏度滑块保持一致
  - 提供更灵活的灵敏度控制

#### 参数应用验证
确认 UI 参数已正确应用到对比过程：
- **Sensitivity（阈值）**: 
  - 范围：1-255，默认 50
  - 用于帧差阈值处理和亮度变化检测
- **Min Area（最小面积）**: 
  - 范围：1-5000，默认 500
  - 用于过滤噪点，只有达到此面积的变化才触发报警

#### 工作流程优化
1. **基线建立**: 监听 `changeState` 主题，检测到 `state` 数组中包含 `2` 时，触发所有摄像头建立新基线
2. **扫描对比**: 每 300ms 扫描 ROI 区域亮度，使用 UI 参数进行对比
3. **触发上报**: 检测到差异时，向 `receiver` 主题发送空报文给 broker

### 2026-01-08 - MQTT 发布修复与主题配置增强

#### MQTT 发布逻辑深度修复 (mqtt_client.py)
- **连接状态管理**: 添加 `_connected` 标志跟踪 MQTT 连接状态
- **发布确认机制**: 实现 `on_publish` 回调，确认消息发布成功
- **错误处理优化**: 
  - 检查连接状态，未连接时阻止发布
  - 正确处理 MQTT 返回码（`MQTT_ERR_SUCCESS`、`MQTT_ERR_NO_CONN`、`MQTT_ERR_QUEUE_SIZE`）
  - 详细的日志记录，包括 Message ID
- **修复关键问题**: 修复了之前检查不存在的 `result.rc` 属性的严重 bug

#### UI 主题配置功能 (widgets.py)
- **订阅主题配置**: 新增订阅主题输入框
  - 支持逗号分隔多个主题（如：`changeState,receiver`）
  - 实时更新并保存到配置文件
- **发布主题配置**: 新增发布主题输入框
  - 可自定义发布主题名称
  - 与订阅主题独立配置
- **配置同步**: UI 配置变更时自动保存到本地

#### 配置管理增强 (config.py)
- **主题配置支持**: 
  - `subscribe_topics`: 订阅主题列表
  - `publish_topic`: 发布主题名称
- **自动保存**: 主题配置变更时自动保存到 `config.json`
- **配置持久化**: 软件启动时自动加载上次的主题配置

#### 主窗口集成 (main_window.py)
- **动态主题配置**: 
  - 启动时加载订阅和发布主题配置
  - 连接时使用配置的主题列表
  - 发布时使用配置的发布主题
- **配置刷新**: MQTT 配置更新时同时刷新订阅和发布主题
- **参数应用**: 所有主题配置通过配置管理器统一管理

#### 配置文件格式更新
```json
{
  "mqtt": {
    "broker": "localhost",
    "subscribe_topics": ["changeState", "receiver"],
    "publish_topic": "receiver"
  },
  "cameras": [...]
}
```

#### 问题解决
- **MQTT 发布失败**: 修复了发布逻辑中的关键 bug，现在可以正确发布消息到 broker
- **主题灵活性**: 用户现在可以通过 UI 灵活配置订阅和发布主题，无需修改代码
- **配置持久化**: 所有 MQTT 和主题配置都会自动保存和加载

## 版本信息

- **项目名称**: Camer
- **Python 版本**: 3.11
- **最后更新**: 2026-01-08
- **Git 仓库**: git@github.com:Roarpeng/Camer.git