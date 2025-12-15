"""
Enhanced Log Manager Component

Comprehensive logging system with detailed event recording, error tracking,
log search and filtering, automatic rotation and compression, and user-friendly
log viewing interface.
"""

import os
import gzip
import json
import logging
import logging.handlers
import threading
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import re
from collections import deque
import uuid

from .data_models import LogEntry, LogLevel, LogCategory


class LogSearchFilter:
    """Filter criteria for log searching."""
    
    def __init__(self, 
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None,
                 log_level: Optional[LogLevel] = None,
                 category: Optional[LogCategory] = None,
                 message_pattern: Optional[str] = None,
                 component: Optional[str] = None,
                 max_results: int = 1000):
        """
        Initialize search filter.
        
        Args:
            start_time: Filter logs after this time
            end_time: Filter logs before this time
            log_level: Filter by log level
            category: Filter by log category
            message_pattern: Regex pattern to match in messages
            component: Filter by component name
            max_results: Maximum number of results to return
        """
        self.start_time = start_time
        self.end_time = end_time
        self.log_level = log_level
        self.category = category
        self.message_pattern = message_pattern
        self.component = component
        self.max_results = max_results


@dataclass
class LogSearchResult:
    """Result of log search operation."""
    entries: List[LogEntry]
    total_matches: int
    search_time_ms: float
    filter_applied: LogSearchFilter


class EnhancedLogManager:
    """
    Enhanced logging system with comprehensive event recording, search capabilities,
    automatic rotation, and user-friendly interfaces.
    """
    
    def __init__(self, 
                 log_directory: str = "logs",
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5,
                 compression_enabled: bool = True,
                 memory_buffer_size: int = 1000):
        """
        Initialize enhanced log manager.
        
        Args:
            log_directory: Directory to store log files
            max_file_size: Maximum size of each log file before rotation
            backup_count: Number of backup files to keep
            compression_enabled: Whether to compress rotated logs
            memory_buffer_size: Size of in-memory log buffer for fast searching
        """
        self.log_directory = Path(log_directory)
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.compression_enabled = compression_enabled
        self.memory_buffer_size = memory_buffer_size
        
        # Create log directory if it doesn't exist
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # In-memory log buffer for fast searching
        self.memory_buffer: deque = deque(maxlen=memory_buffer_size)
        self.buffer_lock = threading.RLock()
        
        # Log file handlers
        self.handlers: Dict[str, logging.Handler] = {}
        self.loggers: Dict[str, logging.Logger] = {}
        
        # Search callbacks
        self.search_callbacks: List[Callable[[LogSearchResult], None]] = []
        
        # Initialize main application logger
        self._setup_main_logger()
        
        # Initialize component-specific loggers
        self._setup_component_loggers()
        
        # Start log management thread
        self._management_thread = threading.Thread(
            target=self._log_management_loop,
            name="LogManager",
            daemon=True
        )
        self._running = True
        self._management_thread.start()
        
        self.main_logger = logging.getLogger("mqtt_camera_monitoring")
        self.main_logger.info("Enhanced Log Manager initialized")
    
    def _setup_main_logger(self) -> None:
        """Set up the main application logger with rotation."""
        logger_name = "mqtt_camera_monitoring"
        log_file = self.log_directory / "application.log"
        
        # Create rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        
        # Custom formatter with detailed information
        formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Set up logger
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        
        # Add custom handler to capture logs in memory
        memory_handler = MemoryLogHandler(self)
        logger.addHandler(memory_handler)
        
        self.handlers[logger_name] = handler
        self.loggers[logger_name] = logger
    
    def _setup_component_loggers(self) -> None:
        """Set up component-specific loggers."""
        components = [
            "connection_manager",
            "mqtt_client", 
            "diagnostic_tool",
            "config_validator",
            "health_monitor",
            "gui_system"
        ]
        
        for component in components:
            log_file = self.log_directory / f"{component}.log"
            
            # Create rotating file handler
            handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            
            # Component-specific formatter
            formatter = logging.Formatter(
                f'%(asctime)s.%(msecs)03d | %(levelname)-8s | {component.upper()} | %(funcName)-15s:%(lineno)-4d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            
            # Set up logger
            logger_name = f"mqtt_camera_monitoring.{component}"
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            
            # Add memory handler
            memory_handler = MemoryLogHandler(self)
            logger.addHandler(memory_handler)
            
            self.handlers[component] = handler
            self.loggers[component] = logger
    
    def log_event(self, 
                  level: LogLevel,
                  category: LogCategory,
                  component: str,
                  message: str,
                  details: Optional[Dict[str, Any]] = None,
                  error_info: Optional[Exception] = None) -> str:
        """
        Log an event with detailed information.
        
        Args:
            level: Log level
            category: Log category
            component: Component name
            message: Log message
            details: Additional details dictionary
            error_info: Exception information if applicable
            
        Returns:
            Unique log entry ID
        """
        entry_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Prepare error information
        error_details = None
        stack_trace = None
        
        if error_info:
            error_details = {
                "type": type(error_info).__name__,
                "message": str(error_info),
                "args": error_info.args
            }
            stack_trace = traceback.format_exc()
        
        # Create log entry
        log_entry = LogEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            level=level,
            category=category,
            component=component,
            message=message,
            details=details or {},
            error_details=error_details,
            stack_trace=stack_trace
        )
        
        # Add to memory buffer
        with self.buffer_lock:
            self.memory_buffer.append(log_entry)
        
        # Log to appropriate logger
        logger = self._get_component_logger(component)
        log_message = self._format_log_message(log_entry)
        
        # Map log level to logging level
        logging_level = self._map_log_level(level)
        logger.log(logging_level, log_message)
        
        return entry_id
    
    def log_connection_event(self, 
                           event_type: str,
                           connection_state: str,
                           details: Optional[Dict[str, Any]] = None,
                           error_message: Optional[str] = None) -> str:
        """
        Log MQTT connection event.
        
        Args:
            event_type: Type of connection event
            connection_state: Current connection state
            details: Additional event details
            error_message: Error message if applicable
            
        Returns:
            Log entry ID
        """
        level = LogLevel.ERROR if error_message else LogLevel.INFO
        message = f"Connection {event_type}: {connection_state}"
        
        event_details = {
            "event_type": event_type,
            "connection_state": connection_state,
            **(details or {})
        }
        
        if error_message:
            event_details["error_message"] = error_message
        
        return self.log_event(
            level=level,
            category=LogCategory.CONNECTION,
            component="connection_manager",
            message=message,
            details=event_details
        )
    
    def log_performance_event(self,
                            metric_name: str,
                            metric_value: float,
                            threshold: Optional[float] = None,
                            details: Optional[Dict[str, Any]] = None) -> str:
        """
        Log performance-related event.
        
        Args:
            metric_name: Name of the performance metric
            metric_value: Current value of the metric
            threshold: Threshold value if applicable
            details: Additional performance details
            
        Returns:
            Log entry ID
        """
        # Determine log level based on threshold
        level = LogLevel.INFO
        if threshold and metric_value > threshold:
            level = LogLevel.WARNING
        
        message = f"Performance metric {metric_name}: {metric_value}"
        if threshold:
            message += f" (threshold: {threshold})"
        
        perf_details = {
            "metric_name": metric_name,
            "metric_value": metric_value,
            "threshold": threshold,
            **(details or {})
        }
        
        return self.log_event(
            level=level,
            category=LogCategory.PERFORMANCE,
            component="health_monitor",
            message=message,
            details=perf_details
        )
    
    def log_error_with_context(self,
                             component: str,
                             error: Exception,
                             context: Optional[Dict[str, Any]] = None,
                             user_action: Optional[str] = None) -> str:
        """
        Log error with full context and stack trace.
        
        Args:
            component: Component where error occurred
            error: Exception object
            context: Additional context information
            user_action: User action that triggered the error
            
        Returns:
            Log entry ID
        """
        message = f"Error in {component}: {str(error)}"
        
        error_context = {
            "user_action": user_action,
            "error_type": type(error).__name__,
            **(context or {})
        }
        
        return self.log_event(
            level=LogLevel.ERROR,
            category=LogCategory.ERROR,
            component=component,
            message=message,
            details=error_context,
            error_info=error
        )
    
    def search_logs(self, filter_criteria: LogSearchFilter) -> LogSearchResult:
        """
        Search logs based on filter criteria.
        
        Args:
            filter_criteria: Search filter criteria
            
        Returns:
            Search results with matching log entries
        """
        start_time = datetime.now()
        matching_entries = []
        
        # Search in memory buffer first (fastest)
        with self.buffer_lock:
            buffer_matches = self._search_in_buffer(filter_criteria)
            matching_entries.extend(buffer_matches)
        
        # If we need more results, search in log files
        if len(matching_entries) < filter_criteria.max_results:
            remaining_needed = filter_criteria.max_results - len(matching_entries)
            file_matches = self._search_in_files(filter_criteria, remaining_needed)
            matching_entries.extend(file_matches)
        
        # Sort by timestamp (newest first)
        matching_entries.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Limit results
        if len(matching_entries) > filter_criteria.max_results:
            matching_entries = matching_entries[:filter_criteria.max_results]
        
        # Calculate search time
        search_time = (datetime.now() - start_time).total_seconds() * 1000
        
        result = LogSearchResult(
            entries=matching_entries,
            total_matches=len(matching_entries),
            search_time_ms=search_time,
            filter_applied=filter_criteria
        )
        
        # Notify search callbacks
        for callback in self.search_callbacks:
            try:
                callback(result)
            except Exception as e:
                self.main_logger.error(f"Error in search callback: {e}")
        
        return result
    
    def get_recent_logs(self, count: int = 100, 
                       component: Optional[str] = None) -> List[LogEntry]:
        """
        Get recent log entries.
        
        Args:
            count: Number of recent entries to return
            component: Filter by component (optional)
            
        Returns:
            List of recent log entries
        """
        with self.buffer_lock:
            entries = list(self.memory_buffer)
        
        # Filter by component if specified
        if component:
            entries = [e for e in entries if e.component == component]
        
        # Sort by timestamp (newest first) and limit
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        return entries[:count]
    
    def get_error_summary(self, time_period: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """
        Get summary of errors in the specified time period.
        
        Args:
            time_period: Time period to analyze
            
        Returns:
            Error summary statistics
        """
        cutoff_time = datetime.now() - time_period
        
        # Get error entries from memory buffer
        with self.buffer_lock:
            error_entries = [
                e for e in self.memory_buffer 
                if e.level == LogLevel.ERROR and e.timestamp >= cutoff_time
            ]
        
        # Analyze errors
        error_by_component = {}
        error_by_type = {}
        total_errors = len(error_entries)
        
        for entry in error_entries:
            # Count by component
            component = entry.component
            error_by_component[component] = error_by_component.get(component, 0) + 1
            
            # Count by error type
            if entry.error_details:
                error_type = entry.error_details.get("type", "Unknown")
                error_by_type[error_type] = error_by_type.get(error_type, 0) + 1
        
        return {
            "time_period_hours": time_period.total_seconds() / 3600,
            "total_errors": total_errors,
            "errors_by_component": error_by_component,
            "errors_by_type": error_by_type,
            "most_recent_error": error_entries[0].timestamp if error_entries else None,
            "error_rate_per_hour": total_errors / (time_period.total_seconds() / 3600)
        }
    
    def export_logs(self, 
                   filter_criteria: LogSearchFilter,
                   export_format: str = "json",
                   output_file: Optional[str] = None) -> str:
        """
        Export logs matching filter criteria.
        
        Args:
            filter_criteria: Filter criteria for export
            export_format: Export format ("json", "csv", "txt")
            output_file: Output file path (optional)
            
        Returns:
            Path to exported file
        """
        # Search for matching logs
        search_result = self.search_logs(filter_criteria)
        
        # Generate output filename if not provided
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.log_directory / f"export_{timestamp}.{export_format}"
        else:
            output_file = Path(output_file)
        
        # Export based on format
        if export_format.lower() == "json":
            self._export_json(search_result.entries, output_file)
        elif export_format.lower() == "csv":
            self._export_csv(search_result.entries, output_file)
        elif export_format.lower() == "txt":
            self._export_txt(search_result.entries, output_file)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
        
        self.main_logger.info(f"Exported {len(search_result.entries)} log entries to {output_file}")
        return str(output_file)
    
    def add_search_callback(self, callback: Callable[[LogSearchResult], None]) -> None:
        """Add callback for search results."""
        self.search_callbacks.append(callback)
    
    def cleanup_old_logs(self, retention_days: int = 30) -> int:
        """
        Clean up log files older than retention period.
        
        Args:
            retention_days: Number of days to retain logs
            
        Returns:
            Number of files cleaned up
        """
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cleaned_count = 0
        
        try:
            for log_file in self.log_directory.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    cleaned_count += 1
                    self.main_logger.info(f"Cleaned up old log file: {log_file}")
        
        except Exception as e:
            self.main_logger.error(f"Error during log cleanup: {e}")
        
        return cleaned_count
    
    def compress_rotated_logs(self) -> int:
        """
        Compress rotated log files to save space.
        
        Returns:
            Number of files compressed
        """
        if not self.compression_enabled:
            return 0
        
        compressed_count = 0
        
        try:
            # Find uncompressed rotated log files
            for log_file in self.log_directory.glob("*.log.*"):
                if not log_file.name.endswith('.gz'):
                    # Compress the file
                    compressed_file = log_file.with_suffix(log_file.suffix + '.gz')
                    
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(compressed_file, 'wb') as f_out:
                            f_out.writelines(f_in)
                    
                    # Remove original file
                    log_file.unlink()
                    compressed_count += 1
                    self.main_logger.info(f"Compressed log file: {log_file} -> {compressed_file}")
        
        except Exception as e:
            self.main_logger.error(f"Error during log compression: {e}")
        
        return compressed_count
    
    def shutdown(self) -> None:
        """Shutdown the log manager."""
        self._running = False
        
        # Close all handlers
        for handler in self.handlers.values():
            handler.close()
        
        self.main_logger.info("Enhanced Log Manager shutdown complete")
    
    def _get_component_logger(self, component: str) -> logging.Logger:
        """Get logger for specific component."""
        logger_name = f"mqtt_camera_monitoring.{component}"
        return logging.getLogger(logger_name)
    
    def _format_log_message(self, entry: LogEntry) -> str:
        """Format log entry for file output."""
        message = entry.message
        
        if entry.details:
            details_str = " | ".join([f"{k}={v}" for k, v in entry.details.items()])
            message += f" | Details: {details_str}"
        
        if entry.error_details:
            message += f" | Error: {entry.error_details['type']} - {entry.error_details['message']}"
        
        return message
    
    def _map_log_level(self, level: LogLevel) -> int:
        """Map custom log level to Python logging level."""
        mapping = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL
        }
        return mapping.get(level, logging.INFO)
    
    def _search_in_buffer(self, filter_criteria: LogSearchFilter) -> List[LogEntry]:
        """Search for matching entries in memory buffer."""
        matches = []
        
        for entry in self.memory_buffer:
            if self._matches_filter(entry, filter_criteria):
                matches.append(entry)
                if len(matches) >= filter_criteria.max_results:
                    break
        
        return matches
    
    def _search_in_files(self, filter_criteria: LogSearchFilter, max_results: int) -> List[LogEntry]:
        """Search for matching entries in log files."""
        # This is a simplified implementation
        # In a production system, you might want to use a more sophisticated
        # log parsing and indexing system
        matches = []
        
        try:
            # Search in recent log files
            log_files = sorted(self.log_directory.glob("*.log*"), 
                             key=lambda x: x.stat().st_mtime, reverse=True)
            
            for log_file in log_files[:5]:  # Limit to 5 most recent files
                if len(matches) >= max_results:
                    break
                
                # Parse log file and extract matching entries
                file_matches = self._parse_log_file(log_file, filter_criteria, 
                                                  max_results - len(matches))
                matches.extend(file_matches)
        
        except Exception as e:
            self.main_logger.error(f"Error searching log files: {e}")
        
        return matches
    
    def _parse_log_file(self, log_file: Path, filter_criteria: LogSearchFilter, 
                       max_results: int) -> List[LogEntry]:
        """Parse log file and extract matching entries."""
        matches = []
        
        try:
            # This is a simplified parser - in production you might want
            # a more robust log parsing system
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if len(matches) >= max_results:
                        break
                    
                    # Simple pattern matching for now
                    if filter_criteria.message_pattern:
                        if not re.search(filter_criteria.message_pattern, line, re.IGNORECASE):
                            continue
                    
                    # Create a basic log entry from the line
                    # This is simplified - you'd want more sophisticated parsing
                    entry = self._parse_log_line(line)
                    if entry and self._matches_filter(entry, filter_criteria):
                        matches.append(entry)
        
        except Exception as e:
            self.main_logger.error(f"Error parsing log file {log_file}: {e}")
        
        return matches
    
    def _parse_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single log line into LogEntry (simplified implementation)."""
        try:
            # This is a very basic parser - in production you'd want more robust parsing
            parts = line.strip().split(' | ')
            if len(parts) < 4:
                return None
            
            # Extract timestamp
            timestamp_str = parts[0].split('.')[0]
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            
            # Extract level
            level_str = parts[1].strip()
            level = LogLevel.INFO  # Default
            for log_level in LogLevel:
                if log_level.value.upper() in level_str.upper():
                    level = log_level
                    break
            
            # Extract component and message
            component = parts[2].strip() if len(parts) > 2 else "unknown"
            message = parts[-1] if parts else line.strip()
            
            return LogEntry(
                entry_id=str(uuid.uuid4()),
                timestamp=timestamp,
                level=level,
                category=LogCategory.SYSTEM,  # Default category
                component=component.lower(),
                message=message,
                details={},
                error_details=None,
                stack_trace=None
            )
        
        except Exception:
            return None
    
    def _matches_filter(self, entry: LogEntry, filter_criteria: LogSearchFilter) -> bool:
        """Check if log entry matches filter criteria."""
        # Time range filter
        if filter_criteria.start_time and entry.timestamp < filter_criteria.start_time:
            return False
        if filter_criteria.end_time and entry.timestamp > filter_criteria.end_time:
            return False
        
        # Log level filter
        if filter_criteria.log_level and entry.level != filter_criteria.log_level:
            return False
        
        # Category filter
        if filter_criteria.category and entry.category != filter_criteria.category:
            return False
        
        # Component filter
        if filter_criteria.component and entry.component != filter_criteria.component:
            return False
        
        # Message pattern filter
        if filter_criteria.message_pattern:
            if not re.search(filter_criteria.message_pattern, entry.message, re.IGNORECASE):
                return False
        
        return True
    
    def _export_json(self, entries: List[LogEntry], output_file: Path) -> None:
        """Export log entries to JSON format."""
        data = [asdict(entry) for entry in entries]
        
        # Convert datetime objects to ISO format strings
        for item in data:
            if 'timestamp' in item and item['timestamp']:
                item['timestamp'] = item['timestamp'].isoformat()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    def _export_csv(self, entries: List[LogEntry], output_file: Path) -> None:
        """Export log entries to CSV format."""
        import csv
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['Timestamp', 'Level', 'Category', 'Component', 'Message', 'Details'])
            
            # Write entries
            for entry in entries:
                writer.writerow([
                    entry.timestamp.isoformat(),
                    entry.level.value,
                    entry.category.value,
                    entry.component,
                    entry.message,
                    json.dumps(entry.details) if entry.details else ''
                ])
    
    def _export_txt(self, entries: List[LogEntry], output_file: Path) -> None:
        """Export log entries to text format."""
        with open(output_file, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(f"{entry.timestamp.isoformat()} | {entry.level.value} | "
                       f"{entry.category.value} | {entry.component} | {entry.message}\n")
                
                if entry.details:
                    f.write(f"  Details: {json.dumps(entry.details, ensure_ascii=False)}\n")
                
                if entry.error_details:
                    f.write(f"  Error: {entry.error_details}\n")
                
                if entry.stack_trace:
                    f.write(f"  Stack Trace:\n{entry.stack_trace}\n")
                
                f.write("\n")
    
    def _log_management_loop(self) -> None:
        """Background thread for log management tasks."""
        while self._running:
            try:
                # Compress rotated logs every hour
                self.compress_rotated_logs()
                
                # Clean up old logs daily
                if datetime.now().hour == 2:  # Run at 2 AM
                    self.cleanup_old_logs()
                
                # Sleep for an hour
                for _ in range(3600):  # 1 hour in seconds
                    if not self._running:
                        break
                    threading.Event().wait(1)
                
            except Exception as e:
                self.main_logger.error(f"Error in log management loop: {e}")


class MemoryLogHandler(logging.Handler):
    """Custom log handler that captures logs in memory buffer."""
    
    def __init__(self, log_manager: EnhancedLogManager):
        super().__init__()
        self.log_manager = log_manager
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit log record to memory buffer."""
        try:
            # Convert logging record to LogEntry
            level = self._map_logging_level(record.levelno)
            category = self._determine_category(record)
            component = self._extract_component(record.name)
            
            # Extract error information if present
            error_info = None
            if record.exc_info:
                error_info = record.exc_info[1]
            
            # Create log entry
            entry = LogEntry(
                entry_id=str(uuid.uuid4()),
                timestamp=datetime.fromtimestamp(record.created),
                level=level,
                category=category,
                component=component,
                message=record.getMessage(),
                details={
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                    "thread": record.thread,
                    "process": record.process
                },
                error_details=None,
                stack_trace=self.format(record) if record.exc_info else None
            )
            
            # Add to memory buffer
            with self.log_manager.buffer_lock:
                self.log_manager.memory_buffer.append(entry)
        
        except Exception:
            # Avoid recursive logging errors
            pass
    
    def _map_logging_level(self, levelno: int) -> LogLevel:
        """Map Python logging level to custom LogLevel."""
        if levelno >= logging.CRITICAL:
            return LogLevel.CRITICAL
        elif levelno >= logging.ERROR:
            return LogLevel.ERROR
        elif levelno >= logging.WARNING:
            return LogLevel.WARNING
        elif levelno >= logging.INFO:
            return LogLevel.INFO
        else:
            return LogLevel.DEBUG
    
    def _determine_category(self, record: logging.LogRecord) -> LogCategory:
        """Determine log category based on record content."""
        message = record.getMessage().lower()
        
        if any(word in message for word in ['connection', 'connect', 'disconnect', 'mqtt']):
            return LogCategory.CONNECTION
        elif any(word in message for word in ['performance', 'latency', 'metric', 'monitor']):
            return LogCategory.PERFORMANCE
        elif any(word in message for word in ['config', 'configuration', 'setting']):
            return LogCategory.CONFIGURATION
        elif any(word in message for word in ['error', 'exception', 'failed', 'failure']):
            return LogCategory.ERROR
        elif any(word in message for word in ['diagnostic', 'test', 'check', 'validation']):
            return LogCategory.DIAGNOSTIC
        else:
            return LogCategory.SYSTEM
    
    def _extract_component(self, logger_name: str) -> str:
        """Extract component name from logger name."""
        parts = logger_name.split('.')
        if len(parts) > 1:
            return parts[-1]  # Last part is usually the component
        return "system"