"""
Health Monitor Component

Real-time monitoring of connection status and performance metrics,
connection quality assessment, anomaly detection, and performance
report generation with trend analysis.
"""

import threading
import time
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from collections import deque
import uuid

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from .data_models import (
    HealthMetrics, ConnectionMetrics, PerformanceReport, 
    QualityReport, ConnectionEvent, HealthStatus, 
    ConnectionState, LogEntry
)


class HealthMonitor:
    """
    Real-time health monitoring and performance tracking system.
    
    Monitors connection status, collects performance metrics, assesses
    connection quality, detects anomalies, and generates performance reports.
    """
    
    def __init__(self, monitoring_interval: float = 1.0, 
                 health_check_interval: float = 30.0,
                 performance_report_interval: float = 3600.0):
        """
        Initialize health monitor.
        
        Args:
            monitoring_interval: Interval between monitoring checks (seconds)
            health_check_interval: Interval between health assessments (seconds)
            performance_report_interval: Interval between performance reports (seconds)
        """
        self.monitoring_interval = monitoring_interval
        self.health_check_interval = health_check_interval
        self.performance_report_interval = performance_report_interval
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._health_thread: Optional[threading.Thread] = None
        self._report_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Current metrics
        self.current_health = HealthMetrics()
        self.current_connection_metrics = ConnectionMetrics()
        
        # Historical data storage (limited to prevent memory issues)
        self.max_history_size = 1000
        self.health_history: deque = deque(maxlen=self.max_history_size)
        self.connection_events: deque = deque(maxlen=self.max_history_size)
        self.performance_history: deque = deque(maxlen=self.max_history_size)
        
        # Callbacks for status updates
        self.status_callbacks: List[Callable[[HealthMetrics], None]] = []
        self.quality_callbacks: List[Callable[[QualityReport], None]] = []
        self.report_callbacks: List[Callable[[PerformanceReport], None]] = []
        
        # Anomaly detection thresholds
        self.quality_threshold = 60.0  # Below this is considered poor quality
        self.latency_threshold = 1000.0  # Above this is considered high latency
        self.error_rate_threshold = 10.0  # Above this percentage is concerning
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self._last_performance_check = datetime.now()
        self._connection_start_time: Optional[datetime] = None
        
    def start_monitoring(self) -> None:
        """Start the health monitoring system."""
        if self._monitoring:
            self.logger.warning("Health monitoring is already running")
            return
            
        self.logger.info("Starting health monitoring system")
        self._monitoring = True
        self._stop_event.clear()
        
        # Start monitoring threads
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop, 
            name="HealthMonitor"
        )
        self._health_thread = threading.Thread(
            target=self._health_check_loop, 
            name="HealthChecker"
        )
        self._report_thread = threading.Thread(
            target=self._report_generation_loop, 
            name="ReportGenerator"
        )
        
        self._monitor_thread.daemon = True
        self._health_thread.daemon = True
        self._report_thread.daemon = True
        
        self._monitor_thread.start()
        self._health_thread.start()
        self._report_thread.start()
        
        self.logger.info("Health monitoring system started successfully")
    
    def stop_monitoring(self) -> None:
        """Stop the health monitoring system."""
        if not self._monitoring:
            return
            
        self.logger.info("Stopping health monitoring system")
        self._monitoring = False
        self._stop_event.set()
        
        # Wait for threads to finish
        threads = [self._monitor_thread, self._health_thread, self._report_thread]
        for thread in threads:
            if thread and thread.is_alive():
                thread.join(timeout=5.0)
                
        self.logger.info("Health monitoring system stopped")
    
    def get_current_metrics(self) -> HealthMetrics:
        """Get current health metrics."""
        return self.current_health
    
    def get_connection_metrics(self) -> ConnectionMetrics:
        """Get current connection metrics."""
        return self.current_connection_metrics
    
    def check_connection_quality(self) -> QualityReport:
        """
        Assess current connection quality and generate quality report.
        
        Returns:
            QualityReport with quality assessment and recommendations
        """
        now = datetime.now()
        
        # Calculate quality scores
        connection_stability = self._calculate_stability_score()
        message_reliability = self.current_connection_metrics.message_success_rate
        performance_score = self._calculate_performance_score()
        
        # Overall quality is weighted average
        overall_quality = (
            connection_stability * 0.4 +
            message_reliability * 0.4 +
            performance_score * 0.2
        )
        
        # Detect issues
        issues = self._detect_quality_issues()
        recommendations = self._generate_quality_recommendations(issues)
        
        quality_report = QualityReport(
            timestamp=now,
            overall_quality=overall_quality,
            connection_stability=connection_stability,
            message_reliability=message_reliability,
            performance_score=performance_score,
            issues_detected=issues,
            recommendations=recommendations
        )
        
        # Notify callbacks
        for callback in self.quality_callbacks:
            try:
                callback(quality_report)
            except Exception as e:
                self.logger.error(f"Error in quality callback: {e}")
        
        return quality_report
    
    def generate_performance_report(self, time_period: str = "last_1h") -> PerformanceReport:
        """
        Generate comprehensive performance report.
        
        Args:
            time_period: Time period for analysis ("last_1h", "last_24h", "last_week")
            
        Returns:
            PerformanceReport with detailed analysis
        """
        report_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Calculate time range
        if time_period == "last_1h":
            start_time = now - timedelta(hours=1)
        elif time_period == "last_24h":
            start_time = now - timedelta(hours=24)
        elif time_period == "last_week":
            start_time = now - timedelta(weeks=1)
        else:
            start_time = now - timedelta(hours=1)
        
        # Analyze trends
        trend_analysis = self._analyze_performance_trends(start_time, now)
        
        # Generate recommendations
        recommendations = self._generate_performance_recommendations(trend_analysis)
        
        report = PerformanceReport(
            report_id=report_id,
            timestamp=now,
            time_period=time_period,
            connection_metrics=self.current_connection_metrics,
            health_metrics=self.current_health,
            trend_analysis=trend_analysis,
            recommendations=recommendations
        )
        
        # Store in history
        self.performance_history.append(report)
        
        # Notify callbacks
        for callback in self.report_callbacks:
            try:
                callback(report)
            except Exception as e:
                self.logger.error(f"Error in report callback: {e}")
        
        return report
    
    def record_connection_event(self, event_type: str, connection_state: ConnectionState,
                              details: Optional[Dict[str, Any]] = None,
                              error_message: Optional[str] = None) -> None:
        """
        Record a connection event for tracking.
        
        Args:
            event_type: Type of event (connect, disconnect, reconnect, error)
            connection_state: Current connection state
            details: Additional event details
            error_message: Error message if applicable
        """
        event = ConnectionEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            connection_state=connection_state,
            details=details or {},
            error_message=error_message
        )
        
        self.connection_events.append(event)
        
        # Update current state
        self.current_health.connection_state = connection_state
        
        # Update connection metrics based on event
        if event_type == "connect":
            self._connection_start_time = event.timestamp
            self.current_health.last_heartbeat = event.timestamp
        elif event_type == "disconnect":
            if self._connection_start_time:
                uptime = (event.timestamp - self._connection_start_time).total_seconds()
                self.current_connection_metrics.connection_uptime += uptime
            self._connection_start_time = None
        elif event_type == "reconnect":
            self.current_connection_metrics.reconnection_count += 1
        elif event_type == "error":
            self.current_connection_metrics.last_error = error_message
            self.current_health.error_count += 1
        
        self.logger.info(f"Connection event recorded: {event_type} - {connection_state.value}")
    
    def update_message_stats(self, sent: int = 0, received: int = 0, failed: int = 0) -> None:
        """
        Update message transmission statistics.
        
        Args:
            sent: Number of messages sent successfully
            received: Number of messages received
            failed: Number of failed message transmissions
        """
        self.current_connection_metrics.total_messages_sent += sent
        self.current_connection_metrics.total_messages_received += received
        self.current_connection_metrics.failed_messages += failed
        
        # Update success rate
        self.current_connection_metrics.update_success_rate()
        
        # Update quality score
        self.current_connection_metrics.calculate_quality_score()
        
        if failed > 0:
            self.logger.warning(f"Message transmission failures: {failed}")
    
    def update_latency(self, latency_ms: float) -> None:
        """
        Update network latency measurement.
        
        Args:
            latency_ms: Latency in milliseconds
        """
        # Simple moving average for latency
        if self.current_connection_metrics.average_latency == 0:
            self.current_connection_metrics.average_latency = latency_ms
        else:
            # Exponential moving average with alpha = 0.1
            alpha = 0.1
            self.current_connection_metrics.average_latency = (
                alpha * latency_ms + 
                (1 - alpha) * self.current_connection_metrics.average_latency
            )
        
        self.current_health.network_latency = latency_ms
        
        # Check for high latency
        if latency_ms > self.latency_threshold:
            self.logger.warning(f"High network latency detected: {latency_ms:.2f}ms")
    
    def add_status_callback(self, callback: Callable[[HealthMetrics], None]) -> None:
        """Add callback for status updates."""
        self.status_callbacks.append(callback)
    
    def add_quality_callback(self, callback: Callable[[QualityReport], None]) -> None:
        """Add callback for quality reports."""
        self.quality_callbacks.append(callback)
    
    def add_report_callback(self, callback: Callable[[PerformanceReport], None]) -> None:
        """Add callback for performance reports."""
        self.report_callbacks.append(callback)
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop that runs continuously."""
        while self._monitoring and not self._stop_event.is_set():
            try:
                self._update_system_metrics()
                self._update_health_status()
                
                # Store current metrics in history
                self.health_history.append(HealthMetrics(
                    timestamp=datetime.now(),
                    connection_state=self.current_health.connection_state,
                    health_status=self.current_health.health_status,
                    active_connections=self.current_health.active_connections,
                    error_count=self.current_health.error_count,
                    warning_count=self.current_health.warning_count,
                    last_heartbeat=self.current_health.last_heartbeat,
                    system_load=self.current_health.system_load,
                    memory_usage=self.current_health.memory_usage,
                    network_latency=self.current_health.network_latency
                ))
                
                # Notify status callbacks
                for callback in self.status_callbacks:
                    try:
                        callback(self.current_health)
                    except Exception as e:
                        self.logger.error(f"Error in status callback: {e}")
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def _health_check_loop(self) -> None:
        """Health check loop that runs periodically."""
        while self._monitoring and not self._stop_event.is_set():
            try:
                # Perform quality check
                quality_report = self.check_connection_quality()
                
                # Update health status based on quality
                if quality_report.overall_quality >= 80:
                    self.current_health.health_status = HealthStatus.HEALTHY
                elif quality_report.overall_quality >= 60:
                    self.current_health.health_status = HealthStatus.WARNING
                else:
                    self.current_health.health_status = HealthStatus.CRITICAL
                
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                time.sleep(self.health_check_interval)
    
    def _report_generation_loop(self) -> None:
        """Performance report generation loop."""
        while self._monitoring and not self._stop_event.is_set():
            try:
                # Generate hourly performance report
                self.generate_performance_report("last_1h")
                
                time.sleep(self.performance_report_interval)
                
            except Exception as e:
                self.logger.error(f"Error in report generation loop: {e}")
                time.sleep(self.performance_report_interval)
    
    def _update_system_metrics(self) -> None:
        """Update system-level metrics."""
        try:
            if PSUTIL_AVAILABLE:
                # CPU usage
                self.current_health.system_load = psutil.cpu_percent(interval=None)
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.current_health.memory_usage = memory.percent
            else:
                # Fallback values when psutil is not available
                self.current_health.system_load = 0.0
                self.current_health.memory_usage = 0.0
            
            # Update timestamp
            self.current_health.timestamp = datetime.now()
            
            # Update connection uptime if connected
            if (self.current_health.connection_state == ConnectionState.CONNECTED and 
                self._connection_start_time):
                uptime = (datetime.now() - self._connection_start_time).total_seconds()
                self.current_connection_metrics.connection_uptime = uptime
                
        except Exception as e:
            self.logger.error(f"Error updating system metrics: {e}")
    
    def _update_health_status(self) -> None:
        """Update overall health status based on current conditions."""
        try:
            # Check for critical conditions
            if (self.current_health.connection_state == ConnectionState.FAILED or
                self.current_health.error_count > 10):
                self.current_health.health_status = HealthStatus.CRITICAL
                return
            
            # Check for warning conditions
            if (self.current_health.connection_state == ConnectionState.RECONNECTING or
                self.current_connection_metrics.message_success_rate < 90 or
                self.current_health.network_latency > self.latency_threshold):
                self.current_health.health_status = HealthStatus.WARNING
                return
            
            # Check for healthy conditions
            if (self.current_health.connection_state == ConnectionState.CONNECTED and
                self.current_connection_metrics.message_success_rate >= 95):
                self.current_health.health_status = HealthStatus.HEALTHY
                return
            
            # Default to unknown if we can't determine
            self.current_health.health_status = HealthStatus.UNKNOWN
            
        except Exception as e:
            self.logger.error(f"Error updating health status: {e}")
            self.current_health.health_status = HealthStatus.UNKNOWN
    
    def _calculate_stability_score(self) -> float:
        """Calculate connection stability score (0-100)."""
        try:
            # Base score starts at 100
            score = 100.0
            
            # Penalize for reconnections
            if self.current_connection_metrics.reconnection_count > 0:
                # Each reconnection reduces score by 10, minimum 20
                penalty = min(self.current_connection_metrics.reconnection_count * 10, 80)
                score -= penalty
            
            # Penalize for recent errors
            recent_errors = sum(1 for event in self.connection_events 
                              if (event.event_type == "error" and 
                                  (datetime.now() - event.timestamp).total_seconds() < 3600))
            if recent_errors > 0:
                error_penalty = min(recent_errors * 5, 30)
                score -= error_penalty
            
            return max(score, 0.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating stability score: {e}")
            return 0.0
    
    def _calculate_performance_score(self) -> float:
        """Calculate performance score based on latency and system metrics (0-100)."""
        try:
            score = 100.0
            
            # Latency penalty
            if self.current_health.network_latency > 100:
                latency_penalty = min((self.current_health.network_latency - 100) / 10, 50)
                score -= latency_penalty
            
            # System load penalty
            if self.current_health.system_load > 80:
                load_penalty = (self.current_health.system_load - 80) / 2
                score -= load_penalty
            
            # Memory usage penalty
            if self.current_health.memory_usage > 90:
                memory_penalty = (self.current_health.memory_usage - 90)
                score -= memory_penalty
            
            return max(score, 0.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating performance score: {e}")
            return 0.0
    
    def _detect_quality_issues(self) -> List[str]:
        """Detect current quality issues."""
        issues = []
        
        try:
            # Connection issues
            if self.current_health.connection_state != ConnectionState.CONNECTED:
                issues.append(f"连接状态异常: {self.current_health.connection_state.value}")
            
            # Performance issues
            if self.current_health.network_latency > self.latency_threshold:
                issues.append(f"网络延迟过高: {self.current_health.network_latency:.2f}ms")
            
            # Message reliability issues
            if self.current_connection_metrics.message_success_rate < 95:
                issues.append(f"消息成功率偏低: {self.current_connection_metrics.message_success_rate:.1f}%")
            
            # System resource issues
            if self.current_health.system_load > 90:
                issues.append(f"系统负载过高: {self.current_health.system_load:.1f}%")
            
            if self.current_health.memory_usage > 95:
                issues.append(f"内存使用率过高: {self.current_health.memory_usage:.1f}%")
            
            # Reconnection issues
            if self.current_connection_metrics.reconnection_count > 5:
                issues.append(f"重连次数过多: {self.current_connection_metrics.reconnection_count}")
                
        except Exception as e:
            self.logger.error(f"Error detecting quality issues: {e}")
            issues.append("检测质量问题时发生错误")
        
        return issues
    
    def _generate_quality_recommendations(self, issues: List[str]) -> List[str]:
        """Generate recommendations based on detected issues."""
        recommendations = []
        
        try:
            for issue in issues:
                if "连接状态异常" in issue:
                    recommendations.append("检查网络连接和MQTT代理配置")
                elif "网络延迟过高" in issue:
                    recommendations.append("检查网络质量，考虑更换网络或代理服务器")
                elif "消息成功率偏低" in issue:
                    recommendations.append("检查MQTT配置，增加重试机制")
                elif "系统负载过高" in issue:
                    recommendations.append("检查系统资源使用，关闭不必要的进程")
                elif "内存使用率过高" in issue:
                    recommendations.append("检查内存泄漏，重启应用程序")
                elif "重连次数过多" in issue:
                    recommendations.append("检查网络稳定性，调整重连策略")
            
            # General recommendations if no specific issues
            if not issues:
                recommendations.append("系统运行良好，继续监控")
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            recommendations.append("生成建议时发生错误")
        
        return recommendations
    
    def _analyze_performance_trends(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Analyze performance trends over time period."""
        try:
            # Filter history data by time range
            relevant_history = [
                h for h in self.health_history 
                if start_time <= h.timestamp <= end_time
            ]
            
            if not relevant_history:
                return {"error": "No data available for the specified time period"}
            
            # Calculate trends
            latencies = [h.network_latency for h in relevant_history if h.network_latency > 0]
            cpu_loads = [h.system_load for h in relevant_history if h.system_load > 0]
            memory_usages = [h.memory_usage for h in relevant_history if h.memory_usage > 0]
            
            trends = {
                "time_period": f"{start_time.isoformat()} to {end_time.isoformat()}",
                "data_points": len(relevant_history),
                "connection_events": len([e for e in self.connection_events 
                                        if start_time <= e.timestamp <= end_time]),
                "average_latency": statistics.mean(latencies) if latencies else 0,
                "max_latency": max(latencies) if latencies else 0,
                "min_latency": min(latencies) if latencies else 0,
                "average_cpu_load": statistics.mean(cpu_loads) if cpu_loads else 0,
                "max_cpu_load": max(cpu_loads) if cpu_loads else 0,
                "average_memory_usage": statistics.mean(memory_usages) if memory_usages else 0,
                "max_memory_usage": max(memory_usages) if memory_usages else 0,
                "connection_uptime_percentage": self._calculate_uptime_percentage(
                    relevant_history, start_time, end_time
                )
            }
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Error analyzing performance trends: {e}")
            return {"error": f"Failed to analyze trends: {str(e)}"}
    
    def _calculate_uptime_percentage(self, history: List[HealthMetrics], 
                                   start_time: datetime, end_time: datetime) -> float:
        """Calculate connection uptime percentage for the given period."""
        try:
            total_time = (end_time - start_time).total_seconds()
            if total_time <= 0:
                return 0.0
            
            connected_time = 0.0
            last_timestamp = start_time
            last_connected = False
            
            for metrics in history:
                time_diff = (metrics.timestamp - last_timestamp).total_seconds()
                
                if last_connected:
                    connected_time += time_diff
                
                last_connected = metrics.connection_state == ConnectionState.CONNECTED
                last_timestamp = metrics.timestamp
            
            # Handle the final period
            if last_connected:
                connected_time += (end_time - last_timestamp).total_seconds()
            
            return (connected_time / total_time) * 100.0
            
        except Exception as e:
            self.logger.error(f"Error calculating uptime percentage: {e}")
            return 0.0
    
    def _generate_performance_recommendations(self, trend_analysis: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on trend analysis."""
        recommendations = []
        
        try:
            # Check for performance issues in trends
            if "average_latency" in trend_analysis:
                avg_latency = trend_analysis["average_latency"]
                if avg_latency > 500:
                    recommendations.append("平均延迟较高，建议优化网络配置")
                elif avg_latency > 200:
                    recommendations.append("延迟有改善空间，监控网络质量")
            
            if "average_cpu_load" in trend_analysis:
                avg_cpu = trend_analysis["average_cpu_load"]
                if avg_cpu > 80:
                    recommendations.append("CPU负载持续较高，考虑优化应用程序")
                elif avg_cpu > 60:
                    recommendations.append("CPU使用率偏高，监控系统性能")
            
            if "connection_uptime_percentage" in trend_analysis:
                uptime = trend_analysis["connection_uptime_percentage"]
                if uptime < 95:
                    recommendations.append("连接稳定性需要改善，检查网络和配置")
                elif uptime < 99:
                    recommendations.append("连接稳定性良好，继续监控")
            
            if "connection_events" in trend_analysis:
                events = trend_analysis["connection_events"]
                if events > 10:
                    recommendations.append("连接事件频繁，检查网络稳定性")
            
            # General recommendations
            if not recommendations:
                recommendations.append("系统性能表现良好")
            
        except Exception as e:
            self.logger.error(f"Error generating performance recommendations: {e}")
            recommendations.append("生成性能建议时发生错误")
        
        return recommendations