"""
MQTT Camera Monitoring System

A Python-based application that integrates MQTT messaging with USB camera monitoring.
The system connects to an MQTT broker to receive state change messages, processes JSON
payloads to count specific values, and controls multiple USB cameras to monitor red
light changes in real-time.
"""

__version__ = "1.0.0"

from .mqtt_client import MQTTClient
from .camera_manager import CameraManager
from .light_detector import RedLightDetector
from .trigger_publisher import TriggerPublisher
from .lightweight_monitor import LightweightVisualMonitor as VisualMonitor
from .main_controller import MainController
from .config import ConfigManager, SystemConfig
from .config_validator import ConfigurationValidator, ValidationResult, MQTTConfigData
from .diagnostic_tool import DiagnosticTool, DiagnosticReport, NetworkTest, BrokerTest
from .data_models import (
    MQTTConfiguration, ConnectionMetrics, HealthMetrics, PerformanceReport,
    LogEntry, SystemConfiguration, ConnectionEvent, QualityReport,
    ConnectionState, HealthStatus
)

__all__ = [
    'MQTTClient',
    'CameraManager', 
    'RedLightDetector',
    'TriggerPublisher',
    'VisualMonitor',
    'MainController',
    'ConfigManager',
    'SystemConfig',
    'ConfigurationValidator',
    'ValidationResult',
    'MQTTConfigData',
    'DiagnosticTool',
    'DiagnosticReport',
    'NetworkTest',
    'BrokerTest',
    'MQTTConfiguration',
    'ConnectionMetrics',
    'HealthMetrics',
    'PerformanceReport',
    'LogEntry',
    'SystemConfiguration',
    'ConnectionEvent',
    'QualityReport',
    'ConnectionState',
    'HealthStatus'
]