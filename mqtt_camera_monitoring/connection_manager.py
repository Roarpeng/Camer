"""
Connection Manager Component

Coordinates MQTT connection lifecycle, manages component interactions,
and provides centralized connection management with health monitoring
and performance tracking.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from .mqtt_client import MQTTClientEnhanced
from .config_validator import ConfigurationValidator
from .diagnostic_tool import DiagnosticTool
from .data_models import (
    MQTTConfiguration, ConnectionState, ConnectionEvent, 
    ConnectionMetrics, HealthMetrics, HealthStatus,
    PerformanceReport, QualityReport, SystemConfiguration
)


class ConnectionResult:
    """Result of connection operation"""
    
    def __init__(self, success: bool, message: str = "", error: Optional[str] = None):
        self.success = success
        self.message = message
        self.error = error
        self.timestamp = datetime.now()


class ConnectionManager:
    """
    Manages MQTT connection lifecycle and coordinates component interactions.
    
    Provides centralized connection management, health monitoring, performance
    tracking, and integration with diagnostic and validation components.
    """
    
    def __init__(self, system_config: SystemConfiguration):
        """
        Initialize connection manager with system configuration
        
        Args:
            system_config: Complete system configuration
        """
        self.system_config = system_config
        self.mqtt_config = system_config.mqtt_config
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.mqtt_client: Optional[MQTTClientEnhanced] = None
        self.config_validator = ConfigurationValidator()
        self.diagnostic_tool = DiagnosticTool()
        
        # Connection state management
        self.connection_state = ConnectionState.DISCONNECTED
        self.is_running = False
        self.start_time = None
        
        # Health monitoring
        self.health_metrics = HealthMetrics()
        self.health_monitor_thread = None
        self.health_check_interval = system_config.health_check_interval
        self.last_health_check = None
        
        # Performance monitoring
        self.performance_reports: List[PerformanceReport] = []
        self.performance_monitor_thread = None
        self.performance_report_interval = system_config.performance_report_interval
        self.last_performance_report = None
        
        # Event callbacks
        self.connection_callbacks: List[Callable[[ConnectionEvent], None]] = []
        self.health_callbacks: List[Callable[[HealthMetrics], None]] = []
        self.performance_callbacks: List[Callable[[PerformanceReport], None]] = []
        
        # Thread safety
        self._lock = threading.Lock()
        self._stop_monitoring = False
    
    def start_connection(self, config: Optional[MQTTConfiguration] = None) -> ConnectionResult:
        """
        Start MQTT connection with comprehensive validation and monitoring
        
        Args:
            config: Optional MQTT configuration (uses system config if None)
            
        Returns:
            ConnectionResult: Result of connection attempt
        """
        try:
            # Use provided config or system default
            mqtt_config = config or self.mqtt_config
            
            self.logger.info("Starting MQTT connection with validation and diagnostics")
            
            # Step 1: Validate configuration
            validation_result = self.config_validator.validate_complete_config(mqtt_config)
            if not validation_result.is_valid:
                error_msg = f"Configuration validation failed: {validation_result.error_message}"
                self.logger.error(error_msg)
                return ConnectionResult(False, error=error_msg)
            
            # Step 2: Run diagnostics
            diagnostic_report = self.diagnostic_tool.run_full_diagnostics(mqtt_config)
            if diagnostic_report.overall_status.name != "HEALTHY":
                warning_msg = f"Diagnostic warnings detected: {diagnostic_report.recommendations}"
                self.logger.warning(warning_msg)
                # Continue with connection despite warnings
            
            # Step 3: Initialize MQTT client
            with self._lock:
                if self.mqtt_client:
                    self.mqtt_client.disconnect_gracefully()
                
                # Convert to legacy config format for client
                legacy_config = self._convert_to_legacy_config(mqtt_config)
                self.mqtt_client = MQTTClientEnhanced(legacy_config)
                
                # Set up callbacks
                self.mqtt_client.set_connection_callback(self._on_connection_event)
            
            # Step 4: Attempt connection
            if self.mqtt_client.connect_with_retry():
                with self._lock:
                    self.connection_state = ConnectionState.CONNECTED
                    self.is_running = True
                    self.start_time = datetime.now()
                
                # Start monitoring threads
                self._start_monitoring()
                
                success_msg = "MQTT connection established successfully"
                self.logger.info(success_msg)
                return ConnectionResult(True, success_msg)
            else:
                error_msg = "Failed to establish MQTT connection"
                self.logger.error(error_msg)
                return ConnectionResult(False, error=error_msg)
                
        except Exception as e:
            error_msg = f"Error starting MQTT connection: {e}"
            self.logger.error(error_msg)
            return ConnectionResult(False, error=error_msg)
    
    def stop_connection(self) -> bool:
        """
        Stop MQTT connection and clean up resources
        
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        try:
            self.logger.info("Stopping MQTT connection and monitoring")
            
            with self._lock:
                self._stop_monitoring = True
                self.is_running = False
                self.connection_state = ConnectionState.DISCONNECTED
            
            # Stop monitoring threads
            self._stop_monitoring_threads()
            
            # Disconnect MQTT client
            if self.mqtt_client:
                self.mqtt_client.disconnect_gracefully()
                self.mqtt_client = None
            
            self.logger.info("MQTT connection stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping MQTT connection: {e}")
            return False
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get comprehensive connection status information
        
        Returns:
            Dict containing detailed connection status
        """
        with self._lock:
            base_status = {
                'connection_state': self.connection_state.value,
                'is_running': self.is_running,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'health_status': self.health_metrics.health_status.value,
                'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None
            }
            
            # Add MQTT client status if available
            if self.mqtt_client:
                mqtt_status = self.mqtt_client.get_connection_status()
                base_status.update({
                    'mqtt_client': mqtt_status,
                    'connection_metrics': self.mqtt_client.get_connection_metrics().__dict__
                })
            
            return base_status
    
    def handle_connection_lost(self) -> None:
        """
        Handle connection loss event and coordinate recovery
        """
        self.logger.warning("Handling connection loss event")
        
        with self._lock:
            if self.connection_state != ConnectionState.FAILED:
                self.connection_state = ConnectionState.RECONNECTING
        
        # Update health status
        self.health_metrics.health_status = HealthStatus.WARNING
        self.health_metrics.error_count += 1
        
        # Notify callbacks
        self._notify_health_callbacks()
        
        # The MQTT client will handle automatic reconnection
        # We just need to monitor and update our state accordingly
    
    def apply_configuration_changes(self, config: MQTTConfiguration) -> bool:
        """
        Apply new MQTT configuration with validation and reconnection
        
        Args:
            config: New MQTT configuration
            
        Returns:
            bool: True if configuration applied successfully, False otherwise
        """
        try:
            self.logger.info("Applying new MQTT configuration")
            
            # Validate new configuration
            validation_result = self.config_validator.validate_complete_config(config)
            if not validation_result.is_valid:
                self.logger.error(f"New configuration is invalid: {validation_result.error_message}")
                return False
            
            # Store old state
            was_running = self.is_running
            
            # Stop current connection if running
            if was_running:
                self.stop_connection()
            
            # Update configuration
            self.mqtt_config = config
            self.system_config.mqtt_config = config
            
            # Restart connection if it was running
            if was_running:
                result = self.start_connection(config)
                return result.success
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying configuration changes: {e}")
            return False
    
    def get_performance_report(self) -> Optional[PerformanceReport]:
        """
        Generate current performance report
        
        Returns:
            PerformanceReport: Current performance analysis or None if not available
        """
        if not self.mqtt_client:
            return None
        
        try:
            metrics = self.mqtt_client.get_connection_metrics()
            
            # Generate trend analysis
            trend_analysis = self._analyze_performance_trends()
            
            # Generate recommendations
            recommendations = self._generate_performance_recommendations(metrics)
            
            report = PerformanceReport(
                report_id=f"perf_{int(time.time())}",
                timestamp=datetime.now(),
                time_period="current",
                connection_metrics=metrics,
                health_metrics=self.health_metrics,
                trend_analysis=trend_analysis,
                recommendations=recommendations
            )
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating performance report: {e}")
            return None
    
    def add_connection_callback(self, callback: Callable[[ConnectionEvent], None]):
        """Add callback for connection events"""
        self.connection_callbacks.append(callback)
    
    def add_health_callback(self, callback: Callable[[HealthMetrics], None]):
        """Add callback for health status changes"""
        self.health_callbacks.append(callback)
    
    def add_performance_callback(self, callback: Callable[[PerformanceReport], None]):
        """Add callback for performance reports"""
        self.performance_callbacks.append(callback)
    
    def _convert_to_legacy_config(self, mqtt_config: MQTTConfiguration):
        """Convert new config format to legacy format for MQTT client"""
        from .config import MQTTConfig
        
        return MQTTConfig(
            broker_host=mqtt_config.broker_host,
            broker_port=mqtt_config.broker_port,
            client_id=mqtt_config.client_id,
            subscribe_topic=mqtt_config.subscribe_topic,
            publish_topic=mqtt_config.publish_topic,
            keepalive=mqtt_config.keepalive,
            reconnect_delay=mqtt_config.reconnect_delay,
            max_reconnect_attempts=mqtt_config.max_reconnect_attempts
        )
    
    def _on_connection_event(self, event: ConnectionEvent):
        """Handle connection events from MQTT client"""
        self.logger.debug(f"Connection event: {event.event_type} - {event.connection_state.value}")
        
        # Update our connection state
        with self._lock:
            self.connection_state = event.connection_state
        
        # Update health metrics based on event
        if event.event_type == "connect":
            self.health_metrics.health_status = HealthStatus.HEALTHY
            self.health_metrics.connection_state = event.connection_state
        elif event.event_type in ["disconnect", "connect_failed", "reconnect_failed"]:
            self.health_metrics.health_status = HealthStatus.CRITICAL
            self.health_metrics.error_count += 1
        elif event.event_type == "reconnect_attempt":
            self.health_metrics.health_status = HealthStatus.WARNING
        
        # Notify callbacks
        for callback in self.connection_callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Error in connection callback: {e}")
    
    def _start_monitoring(self):
        """Start health and performance monitoring threads"""
        with self._lock:
            self._stop_monitoring = False
        
        # Start health monitoring
        if self.system_config.enable_health_monitoring:
            self.health_monitor_thread = threading.Thread(
                target=self._health_monitor_worker,
                daemon=True
            )
            self.health_monitor_thread.start()
        
        # Start performance monitoring
        if self.system_config.enable_performance_monitoring:
            self.performance_monitor_thread = threading.Thread(
                target=self._performance_monitor_worker,
                daemon=True
            )
            self.performance_monitor_thread.start()
    
    def _stop_monitoring_threads(self):
        """Stop monitoring threads"""
        # Wait for threads to finish
        if self.health_monitor_thread and self.health_monitor_thread.is_alive():
            self.health_monitor_thread.join(timeout=5)
        
        if self.performance_monitor_thread and self.performance_monitor_thread.is_alive():
            self.performance_monitor_thread.join(timeout=5)
    
    def _health_monitor_worker(self):
        """Worker thread for health monitoring"""
        while not self._stop_monitoring:
            try:
                self._perform_health_check()
                time.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"Error in health monitoring: {e}")
                time.sleep(5)  # Brief pause before retrying
    
    def _performance_monitor_worker(self):
        """Worker thread for performance monitoring"""
        while not self._stop_monitoring:
            try:
                self._generate_performance_report()
                time.sleep(self.performance_report_interval)
            except Exception as e:
                self.logger.error(f"Error in performance monitoring: {e}")
                time.sleep(60)  # Brief pause before retrying
    
    def _perform_health_check(self):
        """Perform comprehensive health check"""
        with self._lock:
            self.last_health_check = datetime.now()
            
            # Update basic health metrics
            self.health_metrics.timestamp = self.last_health_check
            self.health_metrics.last_heartbeat = self.last_health_check
            
            if self.mqtt_client:
                # Get connection metrics
                metrics = self.mqtt_client.get_connection_metrics()
                
                # Update health based on connection quality
                quality_report = self.mqtt_client.check_connection_quality()
                
                if quality_report.overall_quality >= 80:
                    self.health_metrics.health_status = HealthStatus.HEALTHY
                elif quality_report.overall_quality >= 60:
                    self.health_metrics.health_status = HealthStatus.WARNING
                else:
                    self.health_metrics.health_status = HealthStatus.CRITICAL
                
                # Update connection state
                self.health_metrics.connection_state = self.connection_state
                self.health_metrics.active_connections = 1 if self.mqtt_client.connected else 0
                self.health_metrics.network_latency = metrics.average_latency
        
        # Notify health callbacks
        self._notify_health_callbacks()
    
    def _generate_performance_report(self):
        """Generate and store performance report"""
        report = self.get_performance_report()
        if report:
            # Store report
            self.performance_reports.append(report)
            
            # Keep only recent reports (last 24)
            if len(self.performance_reports) > 24:
                self.performance_reports = self.performance_reports[-24:]
            
            self.last_performance_report = datetime.now()
            
            # Notify performance callbacks
            for callback in self.performance_callbacks:
                try:
                    callback(report)
                except Exception as e:
                    self.logger.error(f"Error in performance callback: {e}")
    
    def _notify_health_callbacks(self):
        """Notify all health callbacks"""
        for callback in self.health_callbacks:
            try:
                callback(self.health_metrics)
            except Exception as e:
                self.logger.error(f"Error in health callback: {e}")
    
    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends from recent reports"""
        if len(self.performance_reports) < 2:
            return {"trend": "insufficient_data"}
        
        # Get recent reports for trend analysis
        recent_reports = self.performance_reports[-5:]  # Last 5 reports
        
        # Analyze quality trend
        quality_scores = [r.connection_metrics.quality_score for r in recent_reports]
        quality_trend = "stable"
        
        if len(quality_scores) >= 3:
            if quality_scores[-1] > quality_scores[0] + 10:
                quality_trend = "improving"
            elif quality_scores[-1] < quality_scores[0] - 10:
                quality_trend = "degrading"
        
        # Analyze latency trend
        latencies = [r.connection_metrics.average_latency for r in recent_reports if r.connection_metrics.average_latency > 0]
        latency_trend = "stable"
        
        if len(latencies) >= 3:
            if latencies[-1] > latencies[0] * 1.2:
                latency_trend = "increasing"
            elif latencies[-1] < latencies[0] * 0.8:
                latency_trend = "decreasing"
        
        return {
            "quality_trend": quality_trend,
            "latency_trend": latency_trend,
            "report_count": len(recent_reports),
            "analysis_period": "last_5_reports"
        }
    
    def _generate_performance_recommendations(self, metrics: ConnectionMetrics) -> List[str]:
        """Generate performance recommendations based on metrics"""
        recommendations = []
        
        if metrics.quality_score < 60:
            recommendations.append("连接质量较差，建议检查网络配置")
        
        if metrics.average_latency > 1000:
            recommendations.append("消息延迟过高，建议优化网络连接")
        
        if metrics.reconnection_count > 5:
            recommendations.append("重连次数过多，建议检查网络稳定性")
        
        if metrics.message_success_rate < 90:
            recommendations.append("消息成功率较低，建议检查MQTT代理状态")
        
        if not recommendations:
            recommendations.append("连接性能良好，继续保持")
        
        return recommendations