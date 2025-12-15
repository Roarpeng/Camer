# MQTT GUI配置功能使用指南

## 🎯 功能概述

现在您可以直接在GUI界面中配置MQTT连接参数，无需手动编辑配置文件。系统会优先使用GUI中的配置，如果GUI中没有对应参数，则从配置文件读取。

## 📋 新增的MQTT配置选项

在GUI的"系统参数"部分，您现在可以看到以下MQTT配置选项：

### 🔧 MQTT配置字段

1. **MQTT代理地址** (`broker_host`)
   - 默认值：`192.168.10.80`
   - 说明：MQTT代理服务器的IP地址或域名
   - 示例：`192.168.1.100`, `mqtt.example.com`

2. **MQTT端口** (`broker_port`)
   - 默认值：`1883`
   - 范围：1-65535
   - 说明：MQTT代理服务器端口

3. **客户端ID** (`client_id`)
   - 默认值：`receiver`
   - 说明：MQTT客户端标识符
   - 注意：每个客户端应使用唯一的ID

4. **订阅主题** (`subscribe_topic`)
   - 默认值：`changeState`
   - 说明：系统订阅的MQTT主题，用于接收状态变化消息

5. **发布主题** (`publish_topic`)
   - 默认值：`receiver/triggered`
   - 说明：系统发布触发消息的MQTT主题

## 🔄 配置优先级

系统按以下优先级读取配置：

1. **GUI配置** - 最高优先级
   - 用户在GUI中填写的参数
   - 实时保存到配置文件

2. **配置文件** - 备用配置
   - `config.yaml` 中的 `mqtt` 部分
   - 当GUI中没有对应参数时使用

## 💾 自动保存功能

- **实时保存**：修改任何MQTT参数后自动保存到配置文件
- **配置验证**：输入参数时进行实时验证
- **错误提示**：无效配置会在界面上显示错误信息

## 🚀 使用步骤

### 1. 启动GUI应用
```bash
camer311\Scripts\activate
python gui_main.py
```

### 2. 配置MQTT参数
1. 在左侧面板找到"系统参数"组
2. 向下滚动找到MQTT配置部分
3. 填写您的MQTT服务器信息：
   - MQTT代理地址：输入您的MQTT服务器IP
   - MQTT端口：通常为1883
   - 客户端ID：输入唯一的客户端标识
   - 订阅主题：输入接收消息的主题
   - 发布主题：输入发送消息的主题

### 3. 验证配置
- 系统会自动验证输入的参数
- 如果有错误，会在"自动保存"标签处显示错误信息
- 正确配置会显示"自动保存: 就绪"

### 4. 启动系统
- 点击"启动系统"按钮
- 系统会使用GUI中配置的MQTT参数
- 在右侧面板可以查看MQTT连接状态

## 📊 配置示例

### 示例1：本地MQTT服务器
```
MQTT代理地址: 127.0.0.1
MQTT端口: 1883
客户端ID: camera_monitor_01
订阅主题: sensors/changeState
发布主题: alerts/triggered
```

### 示例2：远程MQTT服务器
```
MQTT代理地址: mqtt.mycompany.com
MQTT端口: 8883
客户端ID: factory_camera_01
订阅主题: factory/line1/status
发布主题: factory/line1/alerts
```

## 🔍 状态监控

在GUI右侧面板的"MQTT连接状态"部分，您可以看到：

- **连接状态**：显示是否已连接到MQTT服务器
- **服务器信息**：显示当前连接的服务器地址
- **客户端ID**：显示当前使用的客户端标识
- **最后消息时间**：显示最后接收到消息的时间

## ⚠️ 注意事项

### 配置要求
1. **MQTT代理地址**不能为空
2. **客户端ID**不能为空
3. **订阅主题**和**发布主题**不能为空
4. **端口**必须在1-65535范围内

### 网络要求
1. 确保MQTT服务器可访问
2. 检查防火墙设置
3. 验证网络连接

### 客户端ID冲突
- 每个连接到同一MQTT服务器的客户端必须有唯一的ID
- 如果ID重复，可能导致连接不稳定

## 🛠️ 故障排除

### 问题1：无法连接到MQTT服务器
**解决方案：**
1. 检查MQTT代理地址是否正确
2. 验证端口是否正确
3. 确认MQTT服务器正在运行
4. 检查网络连接

### 问题2：配置保存失败
**解决方案：**
1. 检查配置文件权限
2. 确认所有必填字段已填写
3. 验证输入格式是否正确

### 问题3：客户端连接被拒绝
**解决方案：**
1. 更改客户端ID为唯一值
2. 检查MQTT服务器认证设置
3. 验证用户名和密码（如果需要）

## 📝 配置文件格式

GUI配置会自动保存到 `config.yaml` 文件中：

```yaml
mqtt:
  broker_host: "192.168.10.80"
  broker_port: 1883
  client_id: "receiver"
  subscribe_topic: "changeState"
  publish_topic: "receiver/triggered"
  keepalive: 60
  max_reconnect_attempts: 10
  reconnect_delay: 5

gui_config:
  mqtt:
    broker_host: "192.168.10.80"
    broker_port: 1883
    client_id: "receiver"
    subscribe_topic: "changeState"
    publish_topic: "receiver/triggered"
```

## 🔄 配置迁移

如果您之前手动编辑过 `config.yaml` 文件：

1. **自动迁移**：GUI启动时会自动读取现有配置
2. **优先级**：GUI中的修改会覆盖文件中的配置
3. **备份建议**：建议备份原始配置文件

## 🎉 总结

现在您可以：
- ✅ 在GUI中直接配置MQTT参数
- ✅ 实时验证和保存配置
- ✅ 监控MQTT连接状态
- ✅ 无需手动编辑配置文件
- ✅ 配置自动持久化保存

这大大简化了MQTT配置过程，提高了用户体验！