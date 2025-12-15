#!/usr/bin/env python3
"""
路径工具模块
解决PyInstaller打包后的文件路径问题
"""

import os
import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> str:
    """
    获取资源文件的绝对路径
    
    在开发环境中，返回相对于脚本的路径
    在PyInstaller打包后，返回临时目录中的路径
    
    Args:
        relative_path: 相对路径
        
    Returns:
        str: 绝对路径
    """
    try:
        # PyInstaller创建临时文件夹，并将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except AttributeError:
        # 开发环境中，使用脚本所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)


def get_config_path(config_filename: str = "config.yaml") -> str:
    """
    获取配置文件路径
    
    优先级：
    1. 当前工作目录中的配置文件（用户可修改）
    2. 程序目录中的配置文件（默认配置）
    3. 打包资源中的配置文件
    
    Args:
        config_filename: 配置文件名
        
    Returns:
        str: 配置文件路径
    """
    # 1. 检查当前工作目录
    current_dir_config = os.path.join(os.getcwd(), config_filename)
    if os.path.exists(current_dir_config):
        return current_dir_config
    
    # 2. 检查程序所在目录
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller环境：检查EXE所在目录
        exe_dir = os.path.dirname(sys.executable)
        exe_dir_config = os.path.join(exe_dir, config_filename)
        if os.path.exists(exe_dir_config):
            return exe_dir_config
    else:
        # 开发环境：检查脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_dir_config = os.path.join(script_dir, config_filename)
        if os.path.exists(script_dir_config):
            return script_dir_config
    
    # 3. 检查打包资源中的配置文件
    resource_config = get_resource_path(config_filename)
    if os.path.exists(resource_config):
        return resource_config
    
    # 4. 如果都不存在，返回当前工作目录路径（用于创建新文件）
    return current_dir_config


def get_executable_dir() -> str:
    """
    获取可执行文件所在目录
    
    Returns:
        str: 可执行文件目录路径
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller环境
        return os.path.dirname(sys.executable)
    else:
        # 开发环境
        return os.path.dirname(os.path.abspath(__file__))


def ensure_config_in_exe_dir(config_filename: str = "config.yaml") -> str:
    """
    确保配置文件存在于EXE所在目录
    
    如果EXE目录中没有配置文件，从资源中复制一份
    
    Args:
        config_filename: 配置文件名
        
    Returns:
        str: 配置文件路径
    """
    exe_dir = get_executable_dir()
    exe_config_path = os.path.join(exe_dir, config_filename)
    
    # 如果EXE目录中已有配置文件，直接返回
    if os.path.exists(exe_config_path):
        return exe_config_path
    
    # 尝试从资源中复制配置文件
    try:
        resource_config = get_resource_path(config_filename)
        if os.path.exists(resource_config):
            import shutil
            shutil.copy2(resource_config, exe_config_path)
            print(f"已复制默认配置文件到: {exe_config_path}")
            return exe_config_path
    except Exception as e:
        print(f"复制配置文件失败: {e}")
    
    # 如果复制失败，返回EXE目录路径（用于创建新文件）
    return exe_config_path


def get_mask_path(mask_filename: str) -> str:
    """
    获取掩码文件路径
    
    Args:
        mask_filename: 掩码文件名
        
    Returns:
        str: 掩码文件路径
    """
    # 1. 检查当前工作目录
    current_dir_mask = os.path.join(os.getcwd(), mask_filename)
    if os.path.exists(current_dir_mask):
        return current_dir_mask
    
    # 2. 检查程序所在目录
    exe_dir = get_executable_dir()
    exe_dir_mask = os.path.join(exe_dir, mask_filename)
    if os.path.exists(exe_dir_mask):
        return exe_dir_mask
    
    # 3. 检查打包资源
    resource_mask = get_resource_path(mask_filename)
    if os.path.exists(resource_mask):
        return resource_mask
    
    # 4. 返回当前工作目录路径
    return current_dir_mask


def print_path_info():
    """打印路径信息，用于调试"""
    print("=== 路径信息 ===")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"脚本/EXE目录: {get_executable_dir()}")
    
    if hasattr(sys, '_MEIPASS'):
        print(f"PyInstaller临时目录: {sys._MEIPASS}")
        print("运行环境: PyInstaller打包")
    else:
        print("运行环境: 开发环境")
    
    print(f"配置文件路径: {get_config_path()}")
    print(f"掩码文件路径: {get_mask_path('fmask.png')}")
    print("===============")


if __name__ == "__main__":
    # 测试路径工具
    print_path_info()
    
    # 测试配置文件路径
    config_path = get_config_path()
    print(f"\n配置文件路径: {config_path}")
    print(f"配置文件存在: {os.path.exists(config_path)}")
    
    # 测试掩码文件路径
    mask_path = get_mask_path("fmask.png")
    print(f"掩码文件路径: {mask_path}")
    print(f"掩码文件存在: {os.path.exists(mask_path)}")