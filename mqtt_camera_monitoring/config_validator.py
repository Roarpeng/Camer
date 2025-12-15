"""
Configuration Validator Component

Validates MQTT configuration parameters, detects configuration conflicts,
and provides configuration correction suggestions.
"""

import re
import socket
import ipaddress
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging


class ValidationStatus(Enum):
    """Validation result status"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


@dataclass
class ValidationResult:
    """Result of configuration validation"""
    status: ValidationStatus
    message: str
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed"""
        return self.status == ValidationStatus.VALID
    
    @property
    def is_warning(self) -> bool:
        """Check if validation has warnings"""
        return self.status == ValidationStatus.WARNING


@dataclass
class MQTTConfigData:
    """MQTT configuration data structure"""
    broker_host: str
    broker_port: int
    client_id: str
    subscribe_topic: str
    publish_topic: str
    keepalive: int
    max_reconnect_attempts: int
    reconnect_delay: int
    connection_timeout: int = 30
    quality_of_service: int = 0


class ConfigurationValidator:
    """
    Validates MQTT configuration parameters and detects configuration conflicts.
    
    Provides validation for host addresses, port numbers, complete configurations,
    and resolves conflicts between GUI and file configurations.
    """
    
    def __init__(self):
        """Initialize configuration validator"""
        self.logger = logging.getLogger(__name__)
        
        # Valid port ranges
        self.MIN_PORT = 1
        self.MAX_PORT = 65535
        self.COMMON_MQTT_PORTS = [1883, 8883, 8884]
        
        # Valid keepalive ranges
        self.MIN_KEEPALIVE = 10
        self.MAX_KEEPALIVE = 3600
        
        # Valid reconnect settings
        self.MIN_RECONNECT_ATTEMPTS = 1
        self.MAX_RECONNECT_ATTEMPTS = 100
        self.MIN_RECONNECT_DELAY = 1
        self.MAX_RECONNECT_DELAY = 300
        
        # Valid timeout ranges
        self.MIN_CONNECTION_TIMEOUT = 5
        self.MAX_CONNECTION_TIMEOUT = 300
    
    def validate_host_address(self, host: str) -> ValidationResult:
        """
        Validate MQTT broker host address format.
        
        Args:
            host: Host address to validate
            
        Returns:
            ValidationResult: Validation result with status and suggestions
        """
        try:
            if not host or not isinstance(host, str):
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message="主机地址不能为空",
                    suggestions=["请输入有效的IP地址或主机名", "例如: 192.168.1.100 或 mqtt.example.com"]
                )
            
            host = host.strip()
            
            if not host:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message="主机地址不能为空白字符",
                    suggestions=["请输入有效的IP地址或主机名"]
                )
            
            # Check for invalid characters
            if any(char in host for char in [' ', '\t', '\n', '\r']):
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message="主机地址包含无效字符（空格或制表符）",
                    suggestions=["移除所有空格和制表符", "确保地址格式正确"]
                )
            
            # Try to parse as IP address first
            try:
                ip = ipaddress.ip_address(host)
                
                # Check for localhost/loopback
                if ip.is_loopback:
                    return ValidationResult(
                        status=ValidationStatus.WARNING,
                        message="使用本地回环地址，仅适用于本地测试",
                        suggestions=["生产环境请使用实际的MQTT代理地址"]
                    )
                
                # Check for private networks
                if ip.is_private:
                    return ValidationResult(
                        status=ValidationStatus.VALID,
                        message="有效的私有网络IP地址"
                    )
                
                return ValidationResult(
                    status=ValidationStatus.VALID,
                    message="有效的IP地址"
                )
                
            except ValueError:
                # Not an IP address, validate as hostname
                return self._validate_hostname(host)
                
        except Exception as e:
            self.logger.error(f"Host validation error: {e}")
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=f"主机地址验证失败: {str(e)}",
                suggestions=["请检查地址格式是否正确"]
            )
    
    def _validate_hostname(self, hostname: str) -> ValidationResult:
        """
        Validate hostname format.
        
        Args:
            hostname: Hostname to validate
            
        Returns:
            ValidationResult: Validation result
        """
        # Basic hostname validation regex
        hostname_pattern = re.compile(
            r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*$'
        )
        
        if not hostname_pattern.match(hostname):
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message="无效的主机名格式",
                suggestions=[
                    "主机名只能包含字母、数字和连字符",
                    "不能以连字符开头或结尾",
                    "每个部分不能超过63个字符",
                    "例如: mqtt.example.com"
                ]
            )
        
        # Check length
        if len(hostname) > 253:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message="主机名过长（超过253个字符）",
                suggestions=["使用较短的主机名"]
            )
        
        # Check for common localhost names
        localhost_names = ['localhost', 'localhost.localdomain']
        if hostname.lower() in localhost_names:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                message="使用本地主机名，仅适用于本地测试",
                suggestions=["生产环境请使用实际的MQTT代理主机名"]
            )
        
        return ValidationResult(
            status=ValidationStatus.VALID,
            message="有效的主机名格式"
        )
    
    def validate_port_number(self, port: Union[int, str]) -> ValidationResult:
        """
        Validate MQTT broker port number range and availability.
        
        Args:
            port: Port number to validate
            
        Returns:
            ValidationResult: Validation result with status and suggestions
        """
        try:
            # Convert to integer if string
            if isinstance(port, str):
                try:
                    port = int(port.strip())
                except ValueError:
                    return ValidationResult(
                        status=ValidationStatus.INVALID,
                        message="端口号必须是数字",
                        suggestions=["请输入1-65535之间的数字", "常用MQTT端口: 1883, 8883"]
                    )
            
            if not isinstance(port, int):
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message="端口号必须是整数",
                    suggestions=["请输入1-65535之间的整数"]
                )
            
            # Check port range
            if port < self.MIN_PORT or port > self.MAX_PORT:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message=f"端口号超出有效范围 (1-65535): {port}",
                    suggestions=[
                        "请使用1-65535之间的端口号",
                        "常用MQTT端口: 1883 (非加密), 8883 (SSL/TLS)"
                    ]
                )
            
            # Check for well-known ports (1-1023)
            if 1 <= port <= 1023 and port not in self.COMMON_MQTT_PORTS:
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    message=f"使用系统保留端口 {port}，可能需要管理员权限",
                    suggestions=[
                        "建议使用1024以上的端口号",
                        "常用MQTT端口: 1883, 8883"
                    ]
                )
            
            # Provide suggestions for common MQTT ports
            if port in self.COMMON_MQTT_PORTS:
                port_descriptions = {
                    1883: "标准MQTT端口（非加密）",
                    8883: "MQTT over SSL/TLS端口",
                    8884: "MQTT over WebSocket端口"
                }
                return ValidationResult(
                    status=ValidationStatus.VALID,
                    message=f"有效的MQTT端口: {port} - {port_descriptions.get(port, '常用端口')}"
                )
            
            return ValidationResult(
                status=ValidationStatus.VALID,
                message=f"有效的端口号: {port}"
            )
            
        except Exception as e:
            self.logger.error(f"Port validation error: {e}")
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=f"端口号验证失败: {str(e)}",
                suggestions=["请检查端口号格式是否正确"]
            )
    
    def validate_complete_config(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Test connection and validate complete MQTT configuration.
        
        Args:
            config: Complete MQTT configuration dictionary
            
        Returns:
            ValidationResult: Validation result for complete configuration
        """
        try:
            # Validate required fields
            required_fields = [
                'broker_host', 'broker_port', 'client_id', 
                'subscribe_topic', 'publish_topic'
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in config or config[field] is None:
                    missing_fields.append(field)
            
            if missing_fields:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message=f"缺少必需的配置字段: {', '.join(missing_fields)}",
                    suggestions=[
                        "请确保所有必需字段都已配置",
                        "必需字段: broker_host, broker_port, client_id, subscribe_topic, publish_topic"
                    ]
                )
            
            # Validate individual components
            validation_errors = []
            validation_warnings = []
            
            # Validate host
            host_result = self.validate_host_address(config['broker_host'])
            if not host_result.is_valid:
                validation_errors.append(f"主机地址: {host_result.message}")
            elif host_result.is_warning:
                validation_warnings.append(f"主机地址: {host_result.message}")
            
            # Validate port
            port_result = self.validate_port_number(config['broker_port'])
            if not port_result.is_valid:
                validation_errors.append(f"端口号: {port_result.message}")
            elif port_result.is_warning:
                validation_warnings.append(f"端口号: {port_result.message}")
            
            # Validate client ID
            client_id_result = self._validate_client_id(config['client_id'])
            if not client_id_result.is_valid:
                validation_errors.append(f"客户端ID: {client_id_result.message}")
            
            # Validate topics
            sub_topic_result = self._validate_topic(config['subscribe_topic'], "订阅")
            if not sub_topic_result.is_valid:
                validation_errors.append(f"订阅主题: {sub_topic_result.message}")
            
            pub_topic_result = self._validate_topic(config['publish_topic'], "发布")
            if not pub_topic_result.is_valid:
                validation_errors.append(f"发布主题: {pub_topic_result.message}")
            
            # Validate optional parameters
            if 'keepalive' in config:
                keepalive_result = self._validate_keepalive(config['keepalive'])
                if not keepalive_result.is_valid:
                    validation_errors.append(f"保持连接: {keepalive_result.message}")
            
            if 'max_reconnect_attempts' in config:
                attempts_result = self._validate_reconnect_attempts(config['max_reconnect_attempts'])
                if not attempts_result.is_valid:
                    validation_errors.append(f"重连次数: {attempts_result.message}")
            
            if 'reconnect_delay' in config:
                delay_result = self._validate_reconnect_delay(config['reconnect_delay'])
                if not delay_result.is_valid:
                    validation_errors.append(f"重连延时: {delay_result.message}")
            
            # Return results
            if validation_errors:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message=f"配置验证失败: {'; '.join(validation_errors)}",
                    suggestions=[
                        "请修正所有配置错误",
                        "检查每个字段的格式和取值范围"
                    ]
                )
            
            if validation_warnings:
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    message=f"配置有警告: {'; '.join(validation_warnings)}",
                    suggestions=["建议检查警告项目以确保最佳配置"]
                )
            
            return ValidationResult(
                status=ValidationStatus.VALID,
                message="配置验证通过"
            )
            
        except Exception as e:
            self.logger.error(f"Complete config validation error: {e}")
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=f"配置验证异常: {str(e)}",
                suggestions=["请检查配置格式是否正确"]
            )
    
    def _validate_client_id(self, client_id: str) -> ValidationResult:
        """Validate MQTT client ID"""
        if not client_id or not isinstance(client_id, str):
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message="客户端ID不能为空",
                suggestions=["请提供唯一的客户端ID", "例如: receiver, camera_monitor_001"]
            )
        
        client_id = client_id.strip()
        if not client_id:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message="客户端ID不能为空白字符",
                suggestions=["请提供有效的客户端ID"]
            )
        
        # Check length (MQTT spec allows up to 23 characters for v3.1)
        if len(client_id) > 23:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                message="客户端ID过长，某些MQTT代理可能不支持",
                suggestions=["建议使用23个字符以内的客户端ID"]
            )
        
        # Check for invalid characters
        if any(char in client_id for char in [' ', '\t', '\n', '\r', '#', '+', '/']):
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message="客户端ID包含无效字符",
                suggestions=["客户端ID不能包含空格、#、+、/ 等特殊字符"]
            )
        
        return ValidationResult(
            status=ValidationStatus.VALID,
            message="有效的客户端ID"
        )
    
    def _validate_topic(self, topic: str, topic_type: str) -> ValidationResult:
        """Validate MQTT topic"""
        if not topic or not isinstance(topic, str):
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=f"{topic_type}主题不能为空",
                suggestions=["请提供有效的MQTT主题", "例如: sensor/data, device/status"]
            )
        
        topic = topic.strip()
        if not topic:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=f"{topic_type}主题不能为空白字符",
                suggestions=["请提供有效的MQTT主题"]
            )
        
        # Check for invalid characters
        if any(char in topic for char in ['\0', '\t', '\n', '\r']):
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=f"{topic_type}主题包含无效字符",
                suggestions=["主题不能包含空字符、制表符或换行符"]
            )
        
        # Check topic length
        if len(topic) > 65535:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=f"{topic_type}主题过长",
                suggestions=["主题长度不能超过65535个字符"]
            )
        
        return ValidationResult(
            status=ValidationStatus.VALID,
            message=f"有效的{topic_type}主题"
        )
    
    def _validate_keepalive(self, keepalive: Union[int, str]) -> ValidationResult:
        """Validate keepalive parameter"""
        try:
            if isinstance(keepalive, str):
                keepalive = int(keepalive.strip())
            
            if not isinstance(keepalive, int):
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message="保持连接时间必须是整数",
                    suggestions=["请输入10-3600之间的秒数"]
                )
            
            if keepalive < self.MIN_KEEPALIVE or keepalive > self.MAX_KEEPALIVE:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message=f"保持连接时间超出范围 (10-3600秒): {keepalive}",
                    suggestions=["建议使用60-300秒之间的值"]
                )
            
            return ValidationResult(
                status=ValidationStatus.VALID,
                message=f"有效的保持连接时间: {keepalive}秒"
            )
            
        except ValueError:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message="保持连接时间必须是数字",
                suggestions=["请输入10-3600之间的秒数"]
            )
    
    def _validate_reconnect_attempts(self, attempts: Union[int, str]) -> ValidationResult:
        """Validate max reconnect attempts"""
        try:
            if isinstance(attempts, str):
                attempts = int(attempts.strip())
            
            if not isinstance(attempts, int):
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message="最大重连次数必须是整数",
                    suggestions=["请输入1-100之间的数字"]
                )
            
            if attempts < self.MIN_RECONNECT_ATTEMPTS or attempts > self.MAX_RECONNECT_ATTEMPTS:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message=f"最大重连次数超出范围 (1-100): {attempts}",
                    suggestions=["建议使用5-20之间的值"]
                )
            
            return ValidationResult(
                status=ValidationStatus.VALID,
                message=f"有效的最大重连次数: {attempts}"
            )
            
        except ValueError:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message="最大重连次数必须是数字",
                suggestions=["请输入1-100之间的数字"]
            )
    
    def _validate_reconnect_delay(self, delay: Union[int, str]) -> ValidationResult:
        """Validate reconnect delay"""
        try:
            if isinstance(delay, str):
                delay = int(delay.strip())
            
            if not isinstance(delay, int):
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message="重连延时必须是整数",
                    suggestions=["请输入1-300之间的秒数"]
                )
            
            if delay < self.MIN_RECONNECT_DELAY or delay > self.MAX_RECONNECT_DELAY:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message=f"重连延时超出范围 (1-300秒): {delay}",
                    suggestions=["建议使用5-60秒之间的值"]
                )
            
            return ValidationResult(
                status=ValidationStatus.VALID,
                message=f"有效的重连延时: {delay}秒"
            )
            
        except ValueError:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message="重连延时必须是数字",
                suggestions=["请输入1-300之间的秒数"]
            )
    
    def resolve_config_conflicts(self, gui_config: Dict[str, Any], file_config: Dict[str, Any]) -> MQTTConfigData:
        """
        Resolve configuration conflicts between GUI and file configurations.
        GUI configuration takes priority over file configuration.
        
        Args:
            gui_config: Configuration from GUI
            file_config: Configuration from file
            
        Returns:
            MQTTConfigData: Resolved configuration with GUI priority
        """
        try:
            # Start with file config as base
            resolved_config = file_config.copy()
            
            # Override with GUI config values (GUI has priority)
            for key, value in gui_config.items():
                if value is not None and value != "":
                    resolved_config[key] = value
            
            # Ensure all required fields have default values
            defaults = {
                'broker_host': '192.168.10.80',
                'broker_port': 1883,
                'client_id': 'receiver',
                'subscribe_topic': 'changeState',
                'publish_topic': 'receiver/triggered',
                'keepalive': 60,
                'max_reconnect_attempts': 10,
                'reconnect_delay': 5,
                'connection_timeout': 30,
                'quality_of_service': 0
            }
            
            for key, default_value in defaults.items():
                if key not in resolved_config or resolved_config[key] is None:
                    resolved_config[key] = default_value
            
            # Create and return MQTTConfigData object
            return MQTTConfigData(
                broker_host=str(resolved_config['broker_host']),
                broker_port=int(resolved_config['broker_port']),
                client_id=str(resolved_config['client_id']),
                subscribe_topic=str(resolved_config['subscribe_topic']),
                publish_topic=str(resolved_config['publish_topic']),
                keepalive=int(resolved_config['keepalive']),
                max_reconnect_attempts=int(resolved_config['max_reconnect_attempts']),
                reconnect_delay=int(resolved_config['reconnect_delay']),
                connection_timeout=int(resolved_config['connection_timeout']),
                quality_of_service=int(resolved_config['quality_of_service'])
            )
            
        except Exception as e:
            self.logger.error(f"Config conflict resolution error: {e}")
            # Return default configuration in case of error
            return MQTTConfigData(
                broker_host='192.168.10.80',
                broker_port=1883,
                client_id='receiver',
                subscribe_topic='changeState',
                publish_topic='receiver/triggered',
                keepalive=60,
                max_reconnect_attempts=10,
                reconnect_delay=5,
                connection_timeout=30,
                quality_of_service=0
            )