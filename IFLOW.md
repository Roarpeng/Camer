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
2. **MQTT 连接失败**: 检查 Broker 地址 and 网络连接
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

### 2026-01-08 - UI 乱码修复与智能触发优化

#### 中文显示修复 (processor.py)
- **Pillow 集成**: 添加 PIL (Pillow) 库支持中文文字渲染
- **字体自动检测**: 自动尝试加载 Windows 系统中文字体
  - 微软雅黑 (`msyh.ttc`)
  - 黑体 (`simhei.ttf`)
  - 宋体 (`simsun.ttc`)
- **降级机制**: 字体加载失败时自动回退到英文 "ALERT"
- **新增方法**: `put_chinese_text()` 方法支持中文文字绘制
- **依赖要求**: 需要安装 `Pillow` 库

#### 智能触发机制 (main_window.py)
- **单次上报限制**: 基线建立后，亮度变化只触发一次 MQTT 上报
  - 添加 `brightness_reported_flags` 跟踪上报状态
  - 避免重复上报同一触发事件
  - 基线重置时清除上报标志
- **基线建立优化**: 移除自动基线建立逻辑
  - 基线仅在收到 `changeState` 包含 `2` 时建立
  - 基线未建立时不进行检测
  - 基线建立后才开始帧差分析和亮度扫描

#### 扫描间隔配置 (widgets.py, config.py, main_window.py)
- **UI 增强**: 每个摄像头控制面板添加"扫描间隔"滑块
  - 范围：100ms - 5000ms
  - 默认：300ms
- **配置管理**: 
  - 添加 `scan_interval` 参数到配置文件
  - 自动保存和加载扫描间隔设置
- **动态调整**: 运行时实时调整扫描间隔，无需重启

#### MQTT 连接修复 (main_window.py)
- **参数传递修复**: 修复 `reconnect` 方法调用错误
  - 使用关键字参数确保参数正确传递
  - 修复 `list` 和 `int` 类型不匹配问题
- **连接稳定性**: 改善 MQTT broker 连接的可靠性

### 2026-01-08 - 自动配置与打包发布

#### 自动配置功能 (config.py, widgets.py, main_window.py)
- **自动连接 broker**: 
  - 添加 `auto_connect` 配置选项
  - 启动时根据配置自动连接 MQTT broker
  - 默认启用自动连接
- **自动激活摄像头**:
  - 读取配置文件中的 `active` 状态
  - 启动时自动激活标记为活动的摄像头
  - 自动加载对应的 mask 文件
- **配置完整性**: 启动时加载所有配置参数
  - MQTT 配置（broker、主题、自动连接）
  - 摄像头配置（激活、mask、阈值、最小面积、扫描间隔）
  - 所有参数自动应用到 UI 和处理器

#### 项目打包发布
- **PyInstaller 配置** (CamerApp.spec):
  - 添加 `config.json` 到打包列表
  - 包含 `data` 目录及其所有掩码文件
  - 单文件打包模式
- **打包结果** (dist/ 目录):
  - `CamerApp.exe` - 可执行文件
  - `config.json` - 配置文件
  - `data/` - 掩码文件目录
- **部署说明**:
  - 整个 dist 目录可直接部署
  - 配置文件位于 exe 同级目录
  - 用户可直接编辑配置文件
  - 支持添加自定义掩码文件

#### 配置文件完整格式
```json
{
  "mqtt": {
    "broker": "localhost",
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

#### 功能特性总结
- **独立基线管理**: 每个摄像头 independent 建立基线，但共用触发信号
- **智能触发**: 基线建立后只触发一次上报，避免重复
- **灵活配置**: 所有参数可通过 UI 或配置文件配置
- **自动启动**: 支持自动连接 broker 和激活摄像头
- **易于部署**: 打包为单文件 exe，配置文件同级管理

### 2026-01-08 - MQTT Client ID 配置功能

#### Client ID 配置支持 (config.py)
- **配置项新增**: 添加 `client_id` 配置字段
  - 默认值：`"camer"`
  - 用于标识 MQTT 客户端身份
- **配置管理**: 
  - 新增 `get_client_id()` 方法获取配置
  - 新增 `set_client_id()` 方法保存配置
  - 配置变更自动保存到 `config.json`

#### UI 配置界面 (widgets.py)
- **Client ID 输入框**: 在 MqttConfigWidget 中添加
  - 位置：Broker 地址下方
  - 默认值：`camer`
  - 支持自定义 Client ID
- **信号更新**: 
  - `config_updated` 信号增加 `client_id` 参数
  - 连接时自动发送配置的 Client ID
- **配置同步**: UI 配置变更时自动保存

#### 主窗口集成 (main_window.py)
- **初始化集成**: 
  - 启动时从配置加载 Client ID
  - 使用配置的 Client ID 初始化 MqttWorker
- **配置加载**: `load_config()` 方法加载 Client ID
- **配置更新**: `on_mqtt_config_updated()` 方法处理 Client ID 更新
- **自动连接**: 自动连接时使用配置的 Client ID

#### MQTT 客户端增强 (mqtt_client.py)
- **Client ID 支持**: 
  - `__init__()` 方法添加 `client_id` 参数
  - 使用配置的 Client ID 创建 MQTT 客户端
  - 存储为 `self.client_id_str` 供后续使用
- **动态更新**: 
  - `reconnect()` 方法支持动态更新 Client ID
  - Client ID 变更时重新创建客户端对象
  - 保持回调函数配置不变

#### 配置文件更新
```json
{
  "mqtt": {
    "broker": "localhost",
    "client_id": "camer",
    "subscribe_topics": ["changeState", "receiver"],
    "publish_topic": "receiver",
    "auto_connect": true
  }
}
```

#### 功能说明
- **身份标识**: Client ID 用于在 MQTT broker 中唯一标识客户端
- **多实例支持**: 不同实例可使用不同的 Client ID
- **连接管理**: Client ID 变更时自动重新连接
- **配置持久化**: Client ID 配置自动保存和加载

## 版本信息

- **项目名称**: Camer
- **Python 版本**: 3.11
- **最后更新**: 2026-01-09
- **Git 仓库**: git@github.com:Roarpeng/Camer.git

### 2026-01-09 - UI 布局深度优化与架构重构

#### 架构级更新 (main_window.py)
- **引入左侧滚动条 (QScrollArea)**: 为左侧控制面板添加了滚动支持，彻底解决了因组件垂直增长导致的布局挤压和控件重叠问题。
- **布局间距标准化**: 统一了面板宽度 (340px) 和内边距，提升了界面的整体呼吸感。

#### 组件垂直化重构 (widgets.py)
- **LabeledSlider 垂直化**: 滑块组件改为“标签在左上、数值在右上、滑块占满全宽”的垂直堆叠模式。提供了更宽的调节区域，解决了数值被遮挡的问题。
- **MQTT/摄像头配置垂直化**: 所有的输入字段统一采用“标签在上，输入框在下”的排版方式。这在窄面板环境下提供了最佳的稳定性。
- **固定高度与弹性布局**: 移除了导致布局混乱的硬性高度限制，改用 `min-height` 配合内容自适应。

#### 视觉主题精调 (style.py)
- **Ant Design 风格强化**: 采用 `#1890FF`（主色蓝）和 `#F0F2F5`（浅灰背景）的专业配色方案。
- **卡片式设计优化**: 配置项采用白色卡片背景、圆角及微阴影处理，视觉层次更加清晰。
- **交互回馈**: 优化了按钮悬停、滑块拖动及下拉框的样式细节。

#### 体验改进
- **无重叠操作**: 即使在小分辨率屏幕下，通过滚动条也能确保所有控制项完整可触达。
- **中文字体渲染**: 优化了中文字体的显示效果，确保在高 DPI 下依然清晰。

### 2026-01-09 - 基线建立延时功能

#### 功能需求
收到 `changeState` 报文（含有 `2`）后，延时一段可配置的时间，再检测 ROI 区域亮度并设立基线。

#### 配置管理 (config.py)
- **新增配置项**: `baseline_delay`（毫秒），默认值 `1000`
- **配置方法**: `get_baseline_delay()` / `set_baseline_delay()`
- **配置持久化**: 自动保存到 `config.json`

#### UI 界面 (widgets.py)
- **新增滑块**: "基线建立延时" 滑块
  - 范围：100ms - 10000ms
  - 默认：1000ms（1秒）
- **实时调整**: 滑块值变更时立即生效

#### 延时逻辑 (main_window.py)
- **非阻塞实现**: 使用 `currenttime - lasttime` 时间戳逻辑
- **触发流程**:
  1. 收到 MQTT 信号 → 记录 `baseline_trigger_time` 时间戳
  2. 在 `process_frame()` 中检查 `current_time - baseline_trigger_time >= delay`
  3. 条件满足时执行基线重置

#### 配置文件格式
```json
{
  "mqtt": {
    "broker": "localhost",
    "client_id": "camer",
    "subscribe_topics": ["changeState", "receiver"],
    "publish_topic": "receiver",
    "auto_connect": true,
    "baseline_delay": 1000
  }
}
```