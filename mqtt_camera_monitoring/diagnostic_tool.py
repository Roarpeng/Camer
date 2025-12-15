"""
Diagnostic Tool Component

Provides network connectivity testing, broker availability checking,
and diagnostic report generation for MQTT connection issues.
"""

import socket
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import paho.mqtt.client as mqtt


class DiagnosticStatus(Enum):
    """Diagnostic test status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class NetworkTestType(Enum):
    """Types of network tests"""
    PING = "ping"
    TCP_CONNECT = "tcp_connect"
    DNS_RESOLVE = "dns_resolve"


@dataclass
class NetworkTest:
    """Network connectivity test result"""
    test_type: NetworkTestType
    target_host: str
    target_port: Optional[int] = None
    status: DiagnosticStatus = DiagnosticStatus.SKIPPED
    response_time_ms: float = 0.0
    error_message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def is_successful(self) -> bool:
        """Check if test passed"""
        return self.status == DiagnosticStatus.PASSED


@dataclass  
class BrokerTest:
    """MQTT broker availability test result"""
    broker_host: str
    broker_port: int
    status: DiagnosticStatus = DiagnosticStatus.SKIPPED
    connection_time_ms: float = 0.0
    error_message: str = ""
    broker_info: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def is_successful(self) -> bool:
        """Check if broker test passed"""
        return self.status == DiagnosticStatus.PASSED


@dataclass
class DiagnosticReport:
    """Complete diagnostic report"""
    timestamp: datetime
    network_test: NetworkTest
    broker_test: BrokerTest
    config_validation: Any  # ValidationResult from config_validator
    recommendations: List[str] = field(default_factory=list)
    overall_status: DiagnosticStatus = DiagnosticStatus.SKIPPED
    
    @property
    def is_successful(self) -> bool:
        """Check if overall diagnostics passed"""
        return self.overall_status == DiagnosticStatus.PASSED


class DiagnosticTool:
    """
    Diagnostic tool for MQTT connection issues.
    
    Provides comprehensive diagnostics including network connectivity tests,
    broker availability checks, and diagnostic report generation.
    """
    
    def __init__(self):
        """Initialize diagnostic tool"""
        self.logger = logging.getLogger(__name__)
        self._test_timeout = 10.0  # Default timeout for tests
        self._connection_timeout = 5.0  # MQTT connection timeout
    
    def run_full_diagnostics(self, config: Dict[str, Any]) -> DiagnosticReport:
        """
        Execute comprehensive connection diagnostics.
        
        Args:
            config: MQTT configuration dictionary
            
        Returns:
            DiagnosticReport: Complete diagnostic report with all test results
        """
        try:
            self.logger.info("Starting full MQTT connection diagnostics...")
            
            # Import config validator here to avoid circular imports
            from .config_validator import ConfigurationValidator
            
            # Initialize report
            report = DiagnosticReport(
                timestamp=datetime.now(),
                network_test=NetworkTest(NetworkTestType.TCP_CONNECT, ""),
                broker_test=BrokerTest("", 0),
                config_validation=None
            )
            
            # Step 1: Validate configuration
            self.logger.info("Step 1: Validating configuration...")
            validator = ConfigurationValidator()
            config_result = validator.validate_complete_config(config)
            report.config_validation = config_result
            
            if not config_result.is_valid:
                report.overall_status = DiagnosticStatus.FAILED
                report.recommendations.extend([
                    "修正配置错误后重新运行诊断",
                    "检查所有必需的配置字段"
                ])
                report.recommendations.extend(config_result.suggestions)
                return report
            
            # Step 2: Test network connectivity
            self.logger.info("Step 2: Testing network connectivity...")
            host = config.get('broker_host', '')
            port = config.get('broker_port', 1883)
            
            network_test = self.test_network_connectivity(host, port)
            report.network_test = network_test
            
            if not network_test.is_successful:
                report.overall_status = DiagnosticStatus.FAILED
                report.recommendations.extend([
                    "检查网络连接是否正常",
                    "确认MQTT代理地址和端口正确",
                    "检查防火墙设置"
                ])
                return report
            
            # Step 3: Test MQTT broker availability
            self.logger.info("Step 3: Testing MQTT broker availability...")
            broker_test = self.validate_broker_availability(config)
            report.broker_test = broker_test
            
            if not broker_test.is_successful:
                report.overall_status = DiagnosticStatus.FAILED
                report.recommendations.extend([
                    "检查MQTT代理服务是否运行",
                    "验证客户端ID是否唯一",
                    "检查认证设置"
                ])
                return report
            
            # All tests passed
            report.overall_status = DiagnosticStatus.PASSED
            report.recommendations.extend([
                "所有诊断测试通过",
                "MQTT连接配置正确",
                "可以尝试启动系统"
            ])
            
            self.logger.info("Full diagnostics completed successfully")
            return report
            
        except Exception as e:
            self.logger.error(f"Full diagnostics failed: {e}")
            
            # Create error report
            error_report = DiagnosticReport(
                timestamp=datetime.now(),
                network_test=NetworkTest(NetworkTestType.TCP_CONNECT, host if 'host' in locals() else ""),
                broker_test=BrokerTest(host if 'host' in locals() else "", port if 'port' in locals() else 0),
                config_validation=None,
                overall_status=DiagnosticStatus.FAILED,
                recommendations=[
                    f"诊断过程异常: {str(e)}",
                    "请检查配置格式是否正确",
                    "如问题持续，请联系技术支持"
                ]
            )
            
            return error_report
    
    def test_network_connectivity(self, host: str, port: int) -> NetworkTest:
        """
        Test network connectivity to MQTT broker.
        
        Args:
            host: Target host address
            port: Target port number
            
        Returns:
            NetworkTest: Network connectivity test result
        """
        test = NetworkTest(
            test_type=NetworkTestType.TCP_CONNECT,
            target_host=host,
            target_port=port
        )
        
        try:
            self.logger.info(f"Testing TCP connection to {host}:{port}...")
            
            start_time = time.time()
            
            # Create socket and test connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._test_timeout)
            
            try:
                result = sock.connect_ex((host, port))
                end_time = time.time()
                
                test.response_time_ms = (end_time - start_time) * 1000
                
                if result == 0:
                    test.status = DiagnosticStatus.PASSED
                    self.logger.info(f"TCP connection successful ({test.response_time_ms:.1f}ms)")
                else:
                    test.status = DiagnosticStatus.FAILED
                    test.error_message = f"连接失败，错误代码: {result}"
                    self.logger.error(f"TCP connection failed: {result}")
                
            finally:
                sock.close()
                
        except socket.timeout:
            test.status = DiagnosticStatus.FAILED
            test.error_message = f"连接超时 (>{self._test_timeout}秒)"
            self.logger.error(f"TCP connection timeout to {host}:{port}")
            
        except socket.gaierror as e:
            test.status = DiagnosticStatus.FAILED
            test.error_message = f"DNS解析失败: {str(e)}"
            self.logger.error(f"DNS resolution failed for {host}: {e}")
            
        except Exception as e:
            test.status = DiagnosticStatus.FAILED
            test.error_message = f"网络测试异常: {str(e)}"
            self.logger.error(f"Network test exception: {e}")
        
        return test
    
    def validate_broker_availability(self, config: Dict[str, Any]) -> BrokerTest:
        """
        Test MQTT broker availability and connection.
        
        Args:
            config: MQTT configuration dictionary
            
        Returns:
            BrokerTest: Broker availability test result
        """
        host = config.get('broker_host', '')
        port = config.get('broker_port', 1883)
        client_id = config.get('client_id', 'diagnostic_test')
        
        test = BrokerTest(
            broker_host=host,
            broker_port=port
        )
        
        try:
            self.logger.info(f"Testing MQTT broker connection to {host}:{port}...")
            
            # Create test MQTT client
            test_client = mqtt.Client(client_id=f"{client_id}_diagnostic_{int(time.time())}")
            
            # Connection result tracking
            connection_result = {'connected': False, 'error': None}
            connection_event = threading.Event()
            
            def on_connect(client, userdata, flags, rc):
                """Connection callback"""
                if rc == 0:
                    connection_result['connected'] = True
                    self.logger.info("MQTT broker connection successful")
                else:
                    connection_result['error'] = f"连接失败，返回码: {rc}"
                    self.logger.error(f"MQTT connection failed with code: {rc}")
                connection_event.set()
            
            def on_disconnect(client, userdata, rc):
                """Disconnection callback"""
                self.logger.debug(f"MQTT diagnostic client disconnected: {rc}")
            
            # Set callbacks
            test_client.on_connect = on_connect
            test_client.on_disconnect = on_disconnect
            
            start_time = time.time()
            
            # Attempt connection
            test_client.connect(host, port, keepalive=60)
            test_client.loop_start()
            
            # Wait for connection result
            if connection_event.wait(timeout=self._connection_timeout):
                end_time = time.time()
                test.connection_time_ms = (end_time - start_time) * 1000
                
                if connection_result['connected']:
                    test.status = DiagnosticStatus.PASSED
                    
                    # Gather broker information
                    test.broker_info = {
                        'connection_time_ms': test.connection_time_ms,
                        'client_id_used': test_client._client_id,
                        'protocol_version': '3.1.1'  # Default for paho-mqtt
                    }
                    
                    # Clean disconnect
                    test_client.disconnect()
                    
                else:
                    test.status = DiagnosticStatus.FAILED
                    test.error_message = connection_result['error'] or "未知连接错误"
            else:
                test.status = DiagnosticStatus.FAILED
                test.error_message = f"连接超时 (>{self._connection_timeout}秒)"
                self.logger.error(f"MQTT connection timeout to {host}:{port}")
            
            # Stop client loop
            test_client.loop_stop()
            
        except Exception as e:
            test.status = DiagnosticStatus.FAILED
            test.error_message = f"MQTT测试异常: {str(e)}"
            self.logger.error(f"MQTT broker test exception: {e}")
        
        return test
    
    def generate_diagnostic_report(self, network_test: NetworkTest, broker_test: BrokerTest, 
                                 config_validation: Any) -> DiagnosticReport:
        """
        Generate comprehensive diagnostic report.
        
        Args:
            network_test: Network connectivity test result
            broker_test: Broker availability test result
            config_validation: Configuration validation result
            
        Returns:
            DiagnosticReport: Complete diagnostic report
        """
        try:
            report = DiagnosticReport(
                timestamp=datetime.now(),
                network_test=network_test,
                broker_test=broker_test,
                config_validation=config_validation
            )
            
            # Determine overall status
            if (config_validation and config_validation.is_valid and 
                network_test.is_successful and broker_test.is_successful):
                report.overall_status = DiagnosticStatus.PASSED
                report.recommendations = [
                    "所有诊断检查通过",
                    "MQTT连接配置正确",
                    "系统可以正常启动"
                ]
            else:
                report.overall_status = DiagnosticStatus.FAILED
                
                # Generate specific recommendations
                recommendations = []
                
                if config_validation and not config_validation.is_valid:
                    recommendations.append("修正配置验证错误")
                    recommendations.extend(config_validation.suggestions)
                
                if not network_test.is_successful:
                    recommendations.extend([
                        "检查网络连接",
                        "验证主机地址和端口",
                        "检查防火墙设置"
                    ])
                
                if not broker_test.is_successful:
                    recommendations.extend([
                        "检查MQTT代理服务状态",
                        "验证认证设置",
                        "确认客户端ID唯一性"
                    ])
                
                report.recommendations = recommendations
            
            return report
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            
            # Return minimal error report
            return DiagnosticReport(
                timestamp=datetime.now(),
                network_test=network_test,
                broker_test=broker_test,
                config_validation=config_validation,
                overall_status=DiagnosticStatus.FAILED,
                recommendations=[f"报告生成失败: {str(e)}"]
            )