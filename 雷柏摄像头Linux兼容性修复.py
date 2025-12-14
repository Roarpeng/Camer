#!/usr/bin/env python3
"""
雷柏摄像头Linux兼容性修复工具

解决雷柏USB摄像头在Linux环境下的兼容性问题
- 安装必要的驱动和工具
- 配置V4L2参数
- 测试不同的后端
"""

import subprocess
import os
import time
import cv2

def check_system_info():
    """检查系统信息"""
    print("🖥️ 检查系统信息...")
    
    try:
        # 检查Linux发行版
        with open('/etc/os-release', 'r') as f:
            os_info = f.read()
            for line in os_info.split('\n'):
                if line.startswith('PRETTY_NAME'):
                    system_name = line.split('=')[1].strip('"')
                    print(f"   系统: {system_name}")
                    break
    except:
        print("   系统: 未知Linux发行版")
    
    try:
        # 检查内核版本
        result = subprocess.run(['uname', '-r'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   内核: {result.stdout.strip()}")
    except:
        print("   内核: 无法获取")
    
    try:
        # 检查USB控制器
        result = subprocess.run(['lspci', '|', 'grep', '-i', 'usb'], 
                              shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            print(f"   USB控制器: 已检测到")
        else:
            print(f"   USB控制器: 未检测到或不支持")
    except:
        print("   USB控制器: 检查失败")

def install_camera_drivers():
    """安装摄像头驱动和工具"""
    print("\n🔧 安装摄像头驱动和工具...")
    
    packages = [
        "v4l-utils",           # Video4Linux工具
        "uvcdynctrl",          # UVC摄像头控制
        "guvcview",            # 摄像头查看器
        "cheese",              # 摄像头应用
        "ffmpeg",              # 视频处理
        "gstreamer1.0-plugins-good",  # GStreamer插件
        "gstreamer1.0-plugins-bad",
        "gstreamer1.0-plugins-ugly"
    ]
    
    print("正在更新软件包列表...")
    try:
        subprocess.run(['sudo', 'apt-get', 'update'], check=True, timeout=120)
        print("✅ 软件包列表更新完成")
    except subprocess.CalledProcessError:
        print("⚠️  软件包列表更新失败，继续安装...")
    except subprocess.TimeoutExpired:
        print("⚠️  软件包列表更新超时，继续安装...")
    
    for package in packages:
        print(f"安装 {package}...")
        try:
            result = subprocess.run(['sudo', 'apt-get', 'install', '-y', package], 
                                  capture_output=True, text=True, timeout=180)
            if result.returncode == 0:
                print(f"✅ {package} 安装成功")
            else:
                print(f"⚠️  {package} 安装失败: {result.stderr}")
        except subprocess.TimeoutExpired:
            print(f"⚠️  {package} 安装超时")
        except Exception as e:
            print(f"❌ {package} 安装异常: {e}")

def configure_udev_rules():
    """配置udev规则以改善摄像头兼容性"""
    print("\n⚙️ 配置udev规则...")
    
    udev_rule = '''# 雷柏USB摄像头udev规则
# 改善USB摄像头的兼容性和权限

# 通用USB摄像头规则
SUBSYSTEM=="usb", ATTRS{idVendor}=="*", ATTRS{idProduct}=="*", ATTRS{product}=="*Camera*", MODE="0666", GROUP="video"
SUBSYSTEM=="video4linux", GROUP="video", MODE="0664"

# 雷柏设备特殊规则（如果知道具体的VID/PID）
# SUBSYSTEM=="usb", ATTRS{idVendor}=="xxxx", ATTRS{idProduct}=="xxxx", MODE="0666", GROUP="video"

# UVC设备规则
SUBSYSTEM=="usb", ATTRS{bInterfaceClass}=="0e", ATTRS{bInterfaceSubClass}=="01", MODE="0666", GROUP="video"
'''
    
    try:
        udev_file = "/etc/udev/rules.d/99-rapoo-camera.rules"
        
        # 写入udev规则
        with open("/tmp/99-rapoo-camera.rules", "w") as f:
            f.write(udev_rule)
        
        # 复制到系统目录
        subprocess.run(['sudo', 'cp', '/tmp/99-rapoo-camera.rules', udev_file], check=True)
        
        # 重新加载udev规则
        subprocess.run(['sudo', 'udevadm', 'control', '--reload-rules'], check=True)
        subprocess.run(['sudo', 'udevadm', 'trigger'], check=True)
        
        print("✅ udev规则配置完成")
        
    except Exception as e:
        print(f"⚠️  udev规则配置失败: {e}")

def add_user_to_video_group():
    """将用户添加到video组"""
    print("\n👤 配置用户权限...")
    
    try:
        # 获取当前用户名
        import getpass
        username = getpass.getuser()
        
        # 添加用户到video组
        subprocess.run(['sudo', 'usermod', '-a', '-G', 'video', username], check=True)
        print(f"✅ 用户 {username} 已添加到 video 组")
        print("⚠️  需要重新登录或重启系统以使权限生效")
        
    except Exception as e:
        print(f"❌ 用户权限配置失败: {e}")

def test_v4l2_tools():
    """测试V4L2工具"""
    print("\n🧪 测试V4L2工具...")
    
    try:
        # 列出视频设备
        result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ v4l2-ctl 工作正常")
            print("检测到的设备:")
            for line in result.stdout.split('\n'):
                if line.strip():
                    print(f"   {line}")
        else:
            print("❌ v4l2-ctl 无法列出设备")
            
    except subprocess.TimeoutExpired:
        print("⚠️  v4l2-ctl 超时")
    except FileNotFoundError:
        print("❌ v4l2-ctl 未安装")
    except Exception as e:
        print(f"❌ v4l2-ctl 测试失败: {e}")

def configure_camera_parameters(camera_id):
    """配置摄像头参数"""
    print(f"\n⚙️ 配置摄像头 {camera_id} 参数...")
    
    device_path = f"/dev/video{camera_id}"
    
    if not os.path.exists(device_path):
        print(f"❌ 设备 {device_path} 不存在")
        return False
    
    # 基本参数配置
    params = [
        ("brightness", "128"),
        ("contrast", "128"),
        ("saturation", "128"),
        ("auto_exposure", "3"),  # 手动曝光
        ("exposure_time_absolute", "250")
    ]
    
    for param, value in params:
        try:
            result = subprocess.run(['v4l2-ctl', '--device', device_path, 
                                   '--set-ctrl', f'{param}={value}'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"   ✅ {param} = {value}")
            else:
                print(f"   ⚠️  {param} 设置失败: {result.stderr}")
        except Exception as e:
            print(f"   ❌ {param} 配置异常: {e}")
    
    return True

def test_opencv_backends(camera_id):
    """测试OpenCV不同后端"""
    print(f"\n🎥 测试摄像头 {camera_id} 的OpenCV后端...")
    
    backends = [
        (cv2.CAP_V4L2, "V4L2"),
        (cv2.CAP_GSTREAMER, "GStreamer"),
        (cv2.CAP_FFMPEG, "FFmpeg")
    ]
    
    working_backends = []
    
    for backend, name in backends:
        try:
            print(f"   测试 {name} 后端...")
            cap = cv2.VideoCapture(camera_id, backend)
            
            if cap.isOpened():
                # 设置基本参数
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
                
                # 尝试读取画面
                ret, frame = cap.read()
                if ret and frame is not None:
                    height, width = frame.shape[:2]
                    print(f"   ✅ {name}: 成功 ({width}x{height})")
                    working_backends.append((backend, name))
                else:
                    print(f"   ❌ {name}: 无法读取画面")
            else:
                print(f"   ❌ {name}: 无法打开摄像头")
            
            cap.release()
            
        except Exception as e:
            print(f"   ❌ {name}: 异常 - {e}")
    
    return working_backends

def create_rapoo_camera_launcher():
    """创建雷柏摄像头启动器"""
    print("\n🚀 创建雷柏摄像头启动器...")
    
    launcher_script = '''#!/usr/bin/env python3
"""
雷柏摄像头专用启动器

针对Linux环境下的雷柏USB摄像头优化
"""

import cv2
import numpy as np
import time
import sys
import os

def test_rapoo_camera(camera_id):
    """测试雷柏摄像头"""
    print(f"测试雷柏摄像头 {camera_id}...")
    
    # 尝试不同后端
    backends = [
        (cv2.CAP_V4L2, "V4L2"),
        (cv2.CAP_GSTREAMER, "GStreamer"),
        (cv2.CAP_ANY, "Auto")
    ]
    
    for backend, name in backends:
        try:
            cap = cv2.VideoCapture(camera_id, backend)
            if cap.isOpened():
                # 配置参数
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
                cap.set(cv2.CAP_PROP_BRIGHTNESS, 128)
                cap.set(cv2.CAP_PROP_CONTRAST, 128)
                
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"✅ 摄像头 {camera_id} 使用 {name} 后端成功")
                    cap.release()
                    return True, backend
                
            cap.release()
        except Exception as e:
            print(f"❌ 摄像头 {camera_id} {name} 后端失败: {e}")
    
    return False, None

def main():
    print("🎥 雷柏摄像头启动器")
    print("=" * 40)
    
    # 检查权限
    if os.getuid() == 0:
        print("⚠️  不建议以root用户运行")
    
    # 测试摄像头1-6（跳过摄像头0）
    working_cameras = []
    
    for camera_id in range(1, 7):
        success, backend = test_rapoo_camera(camera_id)
        if success:
            working_cameras.append((camera_id, backend))
    
    if not working_cameras:
        print("❌ 未检测到可用的雷柏USB摄像头")
        return
    
    print(f"✅ 检测到 {len(working_cameras)} 个雷柏USB摄像头")
    
    # 启动监控系统
    print("启动雷柏摄像头监控系统...")
    # 这里可以调用主监控系统

if __name__ == "__main__":
    main()
'''
    
    try:
        with open("雷柏摄像头启动器.py", "w", encoding="utf-8") as f:
            f.write(launcher_script)
        
        # 设置执行权限
        os.chmod("雷柏摄像头启动器.py", 0o755)
        
        print("✅ 雷柏摄像头启动器创建完成")
        
    except Exception as e:
        print(f"❌ 启动器创建失败: {e}")

def main():
    """主修复流程"""
    print("🔧 雷柏摄像头Linux兼容性修复工具")
    print("=" * 60)
    print("此工具将帮助解决雷柏USB摄像头在Linux环境下的兼容性问题")
    print()
    
    try:
        # 检查系统信息
        check_system_info()
        
        # 询问是否继续
        print(f"\n⚠️  此操作需要管理员权限来安装驱动和配置系统")
        choice = input("是否继续？(y/n): ").strip().lower()
        
        if choice != 'y':
            print("操作已取消")
            return
        
        # 安装驱动和工具
        install_camera_drivers()
        
        # 配置udev规则
        configure_udev_rules()
        
        # 配置用户权限
        add_user_to_video_group()
        
        # 测试V4L2工具
        test_v4l2_tools()
        
        # 测试摄像头
        print(f"\n🧪 测试雷柏摄像头...")
        working_cameras = []
        
        for camera_id in range(1, 7):  # 跳过摄像头0
            if os.path.exists(f"/dev/video{camera_id}"):
                # 配置参数
                configure_camera_parameters(camera_id)
                
                # 测试后端
                backends = test_opencv_backends(camera_id)
                if backends:
                    working_cameras.append(camera_id)
        
        # 创建启动器
        create_rapoo_camera_launcher()
        
        print(f"\n📊 修复结果:")
        print(f"   - 可用雷柏摄像头: {len(working_cameras)} 个")
        print(f"   - 摄像头ID: {working_cameras}")
        
        if working_cameras:
            print(f"\n✅ 雷柏摄像头兼容性修复完成！")
            print(f"建议操作:")
            print(f"1. 重新登录或重启系统以使权限生效")
            print(f"2. 运行 'python 雷柏USB摄像头检测工具.py' 进行测试")
            print(f"3. 使用 'python 模拟USB摄像头启动.py' 测试系统")
        else:
            print(f"\n⚠️  未检测到可用的雷柏USB摄像头")
            print(f"建议:")
            print(f"1. 检查USB摄像头连接")
            print(f"2. 重启系统后重新测试")
            print(f"3. 尝试不同的USB端口")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断修复过程")
    except Exception as e:
        print(f"\n❌ 修复过程异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()