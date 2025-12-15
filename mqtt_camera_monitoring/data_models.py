"""
Data Models for MQTT Connection Reliability

Defines data structures for configuration, diagnostic reports, 
performance metrics, and system monitoring.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import json


class ConnectionState(Enum):
    """MQTT connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class HealthStatus(Enum):
    """System health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class LogLevel(Enum):
    """Log severity levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """Log entry categories"""
    SYSTEM = "system"
    CONNECTION = "connection"
    PERFORMANCE = "performance"
    CONFIGURATION = "configuration"
    ERROR = "error"
    DIAGNOSTIC = "diagnostic"


@dataclass
class MQTTConfiguration:
    """Complete MQTT configuration data model"""
    broker_host: str
    broker_port: int
    client_id: str
    subscribe_topic: str
    publish_topic: str
    keepalive: int = 60
    max_reconnect_attempts: int = 10
    reconnect_delay: int = 5
    connection_timeout: int = 30
    quality_of_service: int = 0
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: bool = False
    ca_cert_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'broker_host': self.broker_host,
            'broker_port': self.broker_port,
            'client_id': self.client_id,
            'subscribe_topic': self.subscribe_topic,
            'publish_topic': self.publish_topic,
            'keepalive': self.keepalive,
            'max_reconnect_attempts': self.max_reconnect_attempts,
            'reconnect_delay': self.reconnect_delay,
            'connection_timeout': self.connection_timeout,
            'quality_of_service': self.quality_of_service,
            'username': self.username,
            'password': self.password,
            'use_ssl': self.use_ssl,
            'ca_cert_path': self.ca_cert_path
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MQTTConfiguration':
        """Create from dictionary"""
        return cls(
            broker_host=data.get('broker_host', ''),
            broker_port=data.get('broker_port', 1883),
            client_id=data.get('client_id', ''),
            subscribe_topic=data.get('subscribe_topic', ''),
            publish_topic=data.get('publish_topic', ''),
            keepalive=data.get('keepalive', 60),
            max_reconnect_attempts=data.get('max_reconnect_attempts', 10),
            reconnect_delay=data.get('reconnect_delay', 5),
            connection_timeout=data.get('connection_timeout', 30),
            quality_of_service=data.get('quality_of_service', 0),
            username=data.get('username'),
            password=data.get('password'),
            use_ssl=data.get('use_ssl', False),
            ca_cert_path=data.get('ca_cert_path')
        )


@dataclass
class ConnectionMetrics:
    """MQTT connection performance metrics"""
    connection_uptime: float = 0.0  # seconds
    message_success_rate: float = 0.0  # percentage (0-100)
    average_latency: float = 0.0  # milliseconds
    reconnection_count: int = 0
    last_error: Optional[str] = None
    quality_score: float = 0.0  # overall quality (0-100)
    total_messages_sent: int = 0
    total_messages_received: int = 0
    failed_messages: int = 0
    last_successful_connection: Optional[datetime] = None
    last_connection_attempt: Optional[datetime] = None
    
    def calculate_quality_score(self) -> float:
        """Calculate overall connection quality score"""
        try:
            # Base score from success rate (60% weight)
            success_score = self.message_success_rate * 0.6
            
            # Latency score (20% weight) - lower latency is better
            if self.average_latency > 0:
                # Good latency: <100ms=20, <500ms=15, <1000ms=10, >1000ms=5
                if self.average_latency < 100:
                    latency_score = 20
                elif self.average_latency < 500:
                    latency_score = 15
                elif self.average_latency < 1000:
                    latency_score = 10
                else:
                    latency_score = 5
            else:
                latency_score = 20  # No latency data, assume good
            
            # Stability score (20% weight) - fewer reconnections is better
            if self.reconnection_count == 0:
                stability_score = 20
            elif self.reconnection_count <= 2:
                stability_score = 15
            elif self.reconnection_count <= 5:
                stability_score = 10
            else:
                stability_score = 5
            
            self.quality_score = success_score + latency_score + stability_score
            return self.quality_score
            
        except Exception:
            self.quality_score = 0.0
            return 0.0
    
    def update_success_rate(self):
        """Update message success rate"""
        try:
            total_attempts = self.total_messages_sent + self.failed_messages
            if total_attempts > 0:
                self.message_success_rate = (self.total_messages_sent / total_attempts) * 100
            else:
                self.message_success_rate = 100.0
        except Exception:
            self.message_success_rate = 0.0


@dataclass
class HealthMetrics:
    """System health monitoring metrics"""
    timestamp: datetime = field(default_factory=datetime.now)
    connection_state: ConnectionState = ConnectionState.DISCONNECTED
    health_status: HealthStatus = HealthStatus.UNKNOWN
    active_connections: int = 0
    error_count: int = 0
    warning_count: int = 0
    last_heartbeat: Optional[datetime] = None
    system_load: float = 0.0  # CPU usage percentage
    memory_usage: float = 0.0  # Memory usage percentage
    network_latency: float = 0.0  # Network latency in ms
    
    def is_healthy(self) -> bool:
        """Check if system is in healthy state"""
        return (self.health_status == HealthStatus.HEALTHY and 
                self.connection_state == ConnectionState.CONNECTED)
    
    def get_status_summary(self) -> str:
        """Get human-readable status summary"""
        if self.is_healthy():
            return "系统运行正常"
        elif self.health_status == HealthStatus.WARNING:
            return "系统有警告"
        elif self.health_status == HealthStatus.CRITICAL:
            return "系统状态严重"
        else:
            return "系统状态未知"


@dataclass
class PerformanceReport:
    """Performance analysis report"""
    report_id: str
    timestamp: datetime
    time_period: str  # e.g., "last_24h", "last_week"
    connection_metrics: ConnectionMetrics
    health_metrics: HealthMetrics
    trend_analysis: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    def to_json(self) -> str:
        """Convert report to JSON string"""
        try:
            data = {
                'report_id': self.report_id,
                'timestamp': self.timestamp.isoformat(),
                'time_period': self.time_period,
                'connection_metrics': {
                    'connection_uptime': self.connection_metrics.connection_uptime,
                    'message_success_rate': self.connection_metrics.message_success_rate,
                    'average_latency': self.connection_metrics.average_latency,
                    'reconnection_count': self.connection_metrics.reconnection_count,
                    'quality_score': self.connection_metrics.quality_score,
                    'total_messages_sent': self.connection_metrics.total_messages_sent,
                    'total_messages_received': self.connection_metrics.total_messages_received,
                    'failed_messages': self.connection_metrics.failed_messages
                },
                'health_metrics': {
                    'connection_state': self.health_metrics.connection_state.value,
                    'health_status': self.health_metrics.health_status.value,
                    'active_connections': self.health_metrics.active_connections,
                    'error_count': self.health_metrics.error_count,
                    'warning_count': self.health_metrics.warning_count,
                    'system_load': self.health_metrics.system_load,
                    'memory_usage': self.health_metrics.memory_usage,
                    'network_latency': self.health_metrics.network_latency
                },
                'trend_analysis': self.trend_analysis,
                'recommendations': self.recommendations
            }
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            return f'{{"error": "Failed to serialize report: {str(e)}"}}'


@dataclass
class LogEntry:
    """Enhanced system log entry with detailed tracking"""
    entry_id: str
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    component: str  # Component that generated the log
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    error_details: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'entry_id': self.entry_id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'category': self.category.value,
            'component': self.component,
            'message': self.message,
            'details': self.details,
            'error_details': self.error_details,
            'stack_trace': self.stack_trace
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """Create from dictionary"""
        return cls(
            entry_id=data['entry_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            level=LogLevel(data['level']),
            category=LogCategory(data['category']),
            component=data['component'],
            message=data['message'],
            details=data.get('details', {}),
            error_details=data.get('error_details'),
            stack_trace=data.get('stack_trace')
        )


@dataclass
class SystemConfiguration:
    """Complete system configuration"""
    mqtt_config: MQTTConfiguration
    logging_level: str = "INFO"
    monitoring_interval: float = 1.0  # seconds
    health_check_interval: float = 30.0  # seconds
    performance_report_interval: float = 3600.0  # seconds (1 hour)
    max_log_entries: int = 10000
    log_rotation_size: int = 10485760  # 10MB
    enable_performance_monitoring: bool = True
    enable_health_monitoring: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'mqtt_config': self.mqtt_config.to_dict(),
            'logging_level': self.logging_level,
            'monitoring_interval': self.monitoring_interval,
            'health_check_interval': self.health_check_interval,
            'performance_report_interval': self.performance_report_interval,
            'max_log_entries': self.max_log_entries,
            'log_rotation_size': self.log_rotation_size,
            'enable_performance_monitoring': self.enable_performance_monitoring,
            'enable_health_monitoring': self.enable_health_monitoring
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemConfiguration':
        """Create from dictionary"""
        return cls(
            mqtt_config=MQTTConfiguration.from_dict(data.get('mqtt_config', {})),
            logging_level=data.get('logging_level', 'INFO'),
            monitoring_interval=data.get('monitoring_interval', 1.0),
            health_check_interval=data.get('health_check_interval', 30.0),
            performance_report_interval=data.get('performance_report_interval', 3600.0),
            max_log_entries=data.get('max_log_entries', 10000),
            log_rotation_size=data.get('log_rotation_size', 10485760),
            enable_performance_monitoring=data.get('enable_performance_monitoring', True),
            enable_health_monitoring=data.get('enable_health_monitoring', True)
        )


@dataclass
class ConnectionEvent:
    """MQTT connection event"""
    timestamp: datetime
    event_type: str  # connect, disconnect, reconnect, error
    connection_state: ConnectionState
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'connection_state': self.connection_state.value,
            'details': self.details,
            'error_message': self.error_message
        }


@dataclass
class QualityReport:
    """Connection quality assessment report"""
    timestamp: datetime
    overall_quality: float  # 0-100 score
    connection_stability: float  # 0-100 score
    message_reliability: float  # 0-100 score
    performance_score: float  # 0-100 score
    issues_detected: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def get_quality_level(self) -> str:
        """Get quality level description"""
        if self.overall_quality >= 90:
            return "优秀"
        elif self.overall_quality >= 75:
            return "良好"
        elif self.overall_quality >= 60:
            return "一般"
        elif self.overall_quality >= 40:
            return "较差"
        else:
            return "很差"
    
    def is_acceptable(self) -> bool:
        """Check if quality is acceptable"""
        return self.overall_quality >= 60