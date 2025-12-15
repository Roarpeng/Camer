"""
Log Viewer Interface Component

User-friendly log viewing interface with search, filtering, and display capabilities.
Provides both programmatic and GUI-ready interfaces for log management.
"""

import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
import json

from .data_models import LogEntry, LogLevel, LogCategory
from .log_manager import EnhancedLogManager, LogSearchFilter, LogSearchResult


@dataclass
class LogViewConfig:
    """Configuration for log viewer display"""
    max_display_entries: int = 500
    auto_refresh_interval: float = 5.0  # seconds
    show_timestamps: bool = True
    show_components: bool = True
    show_categories: bool = True
    show_details: bool = False
    color_coding: bool = True
    date_format: str = "%Y-%m-%d %H:%M:%S"


@dataclass
class LogDisplayEntry:
    """Formatted log entry for display"""
    entry_id: str
    formatted_timestamp: str
    level_display: str
    category_display: str
    component_display: str
    message_display: str
    details_display: str
    color_class: str
    raw_entry: LogEntry


class LogViewerInterface:
    """
    User-friendly log viewing interface with search, filtering, and real-time updates.
    
    Provides methods for displaying logs in various formats and managing log views.
    """
    
    def __init__(self, log_manager: EnhancedLogManager, config: Optional[LogViewConfig] = None):
        """
        Initialize log viewer interface.
        
        Args:
            log_manager: Enhanced log manager instance
            config: Display configuration
        """
        self.log_manager = log_manager
        self.config = config or LogViewConfig()
        
        # Current view state
        self.current_filter: Optional[LogSearchFilter] = None
        self.current_results: Optional[LogSearchResult] = None
        self.display_entries: List[LogDisplayEntry] = []
        
        # Auto-refresh state
        self._auto_refresh_enabled = False
        self._refresh_thread: Optional[threading.Thread] = None
        self._stop_refresh = threading.Event()
        
        # View callbacks
        self.update_callbacks: List[Callable[[List[LogDisplayEntry]], None]] = []
        self.error_callbacks: List[Callable[[str], None]] = []
        
        # Level color mapping for display
        self.level_colors = {
            LogLevel.DEBUG: "gray",
            LogLevel.INFO: "blue", 
            LogLevel.WARNING: "orange",
            LogLevel.ERROR: "red",
            LogLevel.CRITICAL: "darkred"
        }
        
        # Category icons for display
        self.category_icons = {
            LogCategory.SYSTEM: "⚙️",
            LogCategory.CONNECTION: "🔗",
            LogCategory.PERFORMANCE: "📊",
            LogCategory.CONFIGURATION: "⚙️",
            LogCategory.ERROR: "❌",
            LogCategory.DIAGNOSTIC: "🔍"
        }
    
    def search_and_display(self, 
                          search_text: Optional[str] = None,
                          level_filter: Optional[LogLevel] = None,
                          category_filter: Optional[LogCategory] = None,
                          component_filter: Optional[str] = None,
                          time_range_hours: Optional[int] = None,
                          max_results: int = 500) -> List[LogDisplayEntry]:
        """
        Search logs and prepare them for display.
        
        Args:
            search_text: Text to search in log messages
            level_filter: Filter by log level
            category_filter: Filter by category
            component_filter: Filter by component
            time_range_hours: Limit to last N hours
            max_results: Maximum results to return
            
        Returns:
            List of formatted display entries
        """
        try:
            # Build search filter
            start_time = None
            if time_range_hours:
                start_time = datetime.now() - timedelta(hours=time_range_hours)
            
            filter_criteria = LogSearchFilter(
                start_time=start_time,
                end_time=None,
                log_level=level_filter,
                category=category_filter,
                message_pattern=search_text,
                component=component_filter,
                max_results=max_results
            )
            
            # Perform search
            search_result = self.log_manager.search_logs(filter_criteria)
            
            # Store current state
            self.current_filter = filter_criteria
            self.current_results = search_result
            
            # Format entries for display
            self.display_entries = self._format_entries_for_display(search_result.entries)
            
            # Notify callbacks
            self._notify_update_callbacks()
            
            return self.display_entries
            
        except Exception as e:
            error_msg = f"Error searching logs: {str(e)}"
            self._notify_error_callbacks(error_msg)
            return []
    
    def get_recent_logs(self, count: int = 100, 
                       component: Optional[str] = None) -> List[LogDisplayEntry]:
        """
        Get recent log entries formatted for display.
        
        Args:
            count: Number of recent entries
            component: Filter by component
            
        Returns:
            List of formatted display entries
        """
        try:
            recent_entries = self.log_manager.get_recent_logs(count, component)
            self.display_entries = self._format_entries_for_display(recent_entries)
            
            # Clear current filter since this is a direct query
            self.current_filter = None
            self.current_results = None
            
            self._notify_update_callbacks()
            return self.display_entries
            
        except Exception as e:
            error_msg = f"Error getting recent logs: {str(e)}"
            self._notify_error_callbacks(error_msg)
            return []
    
    def get_error_summary_display(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get formatted error summary for display.
        
        Args:
            hours: Time period in hours
            
        Returns:
            Formatted error summary
        """
        try:
            time_period = timedelta(hours=hours)
            summary = self.log_manager.get_error_summary(time_period)
            
            # Format for display
            formatted_summary = {
                "time_period": f"过去 {hours} 小时",
                "total_errors": summary["total_errors"],
                "error_rate": f"{summary['error_rate_per_hour']:.1f} 错误/小时",
                "most_recent": summary["most_recent_error"].strftime(self.config.date_format) if summary["most_recent_error"] else "无",
                "by_component": self._format_component_errors(summary["errors_by_component"]),
                "by_type": self._format_error_types(summary["errors_by_type"])
            }
            
            return formatted_summary
            
        except Exception as e:
            return {"error": f"获取错误摘要失败: {str(e)}"}
    
    def export_current_view(self, format_type: str = "json", 
                           filename: Optional[str] = None) -> str:
        """
        Export currently displayed logs.
        
        Args:
            format_type: Export format (json, csv, txt)
            filename: Output filename
            
        Returns:
            Path to exported file
        """
        try:
            if not self.current_results:
                raise ValueError("No search results to export")
            
            return self.log_manager.export_logs(
                self.current_filter,
                format_type,
                filename
            )
            
        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            self._notify_error_callbacks(error_msg)
            return ""
    
    def start_auto_refresh(self) -> None:
        """Start automatic refresh of log display."""
        if self._auto_refresh_enabled:
            return
        
        self._auto_refresh_enabled = True
        self._stop_refresh.clear()
        
        self._refresh_thread = threading.Thread(
            target=self._auto_refresh_loop,
            name="LogViewerRefresh",
            daemon=True
        )
        self._refresh_thread.start()
    
    def stop_auto_refresh(self) -> None:
        """Stop automatic refresh."""
        self._auto_refresh_enabled = False
        self._stop_refresh.set()
        
        if self._refresh_thread and self._refresh_thread.is_alive():
            self._refresh_thread.join(timeout=5.0)
    
    def refresh_current_view(self) -> List[LogDisplayEntry]:
        """
        Refresh the current view with latest data.
        
        Returns:
            Updated display entries
        """
        try:
            if self.current_filter:
                # Re-run the current search
                search_result = self.log_manager.search_logs(self.current_filter)
                self.current_results = search_result
                self.display_entries = self._format_entries_for_display(search_result.entries)
            else:
                # Refresh recent logs
                recent_entries = self.log_manager.get_recent_logs(self.config.max_display_entries)
                self.display_entries = self._format_entries_for_display(recent_entries)
            
            self._notify_update_callbacks()
            return self.display_entries
            
        except Exception as e:
            error_msg = f"Error refreshing view: {str(e)}"
            self._notify_error_callbacks(error_msg)
            return self.display_entries
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about current log view.
        
        Returns:
            Statistics dictionary
        """
        if not self.display_entries:
            return {"total_entries": 0}
        
        # Count by level
        level_counts = {}
        category_counts = {}
        component_counts = {}
        
        for entry in self.display_entries:
            level = entry.raw_entry.level
            category = entry.raw_entry.category
            component = entry.raw_entry.component
            
            level_counts[level.value] = level_counts.get(level.value, 0) + 1
            category_counts[category.value] = category_counts.get(category.value, 0) + 1
            component_counts[component] = component_counts.get(component, 0) + 1
        
        # Time range
        timestamps = [entry.raw_entry.timestamp for entry in self.display_entries]
        time_range = {
            "earliest": min(timestamps).strftime(self.config.date_format) if timestamps else None,
            "latest": max(timestamps).strftime(self.config.date_format) if timestamps else None
        }
        
        return {
            "total_entries": len(self.display_entries),
            "by_level": level_counts,
            "by_category": category_counts,
            "by_component": component_counts,
            "time_range": time_range,
            "search_time_ms": self.current_results.search_time_ms if self.current_results else 0
        }
    
    def add_update_callback(self, callback: Callable[[List[LogDisplayEntry]], None]) -> None:
        """Add callback for view updates."""
        self.update_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[str], None]) -> None:
        """Add callback for error notifications."""
        self.error_callbacks.append(callback)
    
    def _format_entries_for_display(self, entries: List[LogEntry]) -> List[LogDisplayEntry]:
        """Format log entries for display."""
        display_entries = []
        
        for entry in entries:
            # Format timestamp
            formatted_timestamp = entry.timestamp.strftime(self.config.date_format)
            
            # Format level with color
            level_display = entry.level.value
            color_class = self.level_colors.get(entry.level, "black")
            
            # Format category with icon
            category_icon = self.category_icons.get(entry.category, "📝")
            category_display = f"{category_icon} {entry.category.value}"
            
            # Format component
            component_display = entry.component.upper()
            
            # Format message (truncate if too long)
            message_display = entry.message
            if len(message_display) > 100:
                message_display = message_display[:97] + "..."
            
            # Format details
            details_display = ""
            if entry.details and self.config.show_details:
                details_list = [f"{k}: {v}" for k, v in entry.details.items()]
                details_display = " | ".join(details_list[:3])  # Show first 3 details
                if len(entry.details) > 3:
                    details_display += f" | ... (+{len(entry.details) - 3} more)"
            
            display_entry = LogDisplayEntry(
                entry_id=entry.entry_id,
                formatted_timestamp=formatted_timestamp,
                level_display=level_display,
                category_display=category_display,
                component_display=component_display,
                message_display=message_display,
                details_display=details_display,
                color_class=color_class,
                raw_entry=entry
            )
            
            display_entries.append(display_entry)
        
        return display_entries
    
    def _format_component_errors(self, component_errors: Dict[str, int]) -> List[Dict[str, Any]]:
        """Format component error counts for display."""
        formatted = []
        for component, count in sorted(component_errors.items(), key=lambda x: x[1], reverse=True):
            formatted.append({
                "component": component.upper(),
                "count": count,
                "percentage": f"{(count / sum(component_errors.values())) * 100:.1f}%"
            })
        return formatted
    
    def _format_error_types(self, error_types: Dict[str, int]) -> List[Dict[str, Any]]:
        """Format error type counts for display."""
        formatted = []
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            formatted.append({
                "type": error_type,
                "count": count,
                "percentage": f"{(count / sum(error_types.values())) * 100:.1f}%"
            })
        return formatted
    
    def _auto_refresh_loop(self) -> None:
        """Auto-refresh loop that runs in background thread."""
        while self._auto_refresh_enabled and not self._stop_refresh.is_set():
            try:
                self.refresh_current_view()
                
                # Wait for next refresh interval
                self._stop_refresh.wait(self.config.auto_refresh_interval)
                
            except Exception as e:
                error_msg = f"Error in auto-refresh: {str(e)}"
                self._notify_error_callbacks(error_msg)
                
                # Wait before retrying
                self._stop_refresh.wait(self.config.auto_refresh_interval)
    
    def _notify_update_callbacks(self) -> None:
        """Notify all update callbacks."""
        for callback in self.update_callbacks:
            try:
                callback(self.display_entries)
            except Exception as e:
                # Don't let callback errors break the viewer
                pass
    
    def _notify_error_callbacks(self, error_message: str) -> None:
        """Notify all error callbacks."""
        for callback in self.error_callbacks:
            try:
                callback(error_message)
            except Exception:
                # Don't let callback errors break the viewer
                pass


class LogViewerGUI:
    """
    GUI-specific log viewer interface for integration with GUI applications.
    
    Provides methods specifically designed for GUI frameworks.
    """
    
    def __init__(self, log_viewer: LogViewerInterface):
        """
        Initialize GUI log viewer.
        
        Args:
            log_viewer: Log viewer interface instance
        """
        self.log_viewer = log_viewer
        self.gui_callbacks: Dict[str, Callable] = {}
    
    def get_display_data_for_table(self) -> List[List[str]]:
        """
        Get log data formatted for table display in GUI.
        
        Returns:
            List of rows, each row is a list of column values
        """
        rows = []
        
        for entry in self.log_viewer.display_entries:
            row = []
            
            if self.log_viewer.config.show_timestamps:
                row.append(entry.formatted_timestamp)
            
            row.append(entry.level_display)
            
            if self.log_viewer.config.show_categories:
                row.append(entry.category_display)
            
            if self.log_viewer.config.show_components:
                row.append(entry.component_display)
            
            row.append(entry.message_display)
            
            if self.log_viewer.config.show_details and entry.details_display:
                row.append(entry.details_display)
            
            rows.append(row)
        
        return rows
    
    def get_table_headers(self) -> List[str]:
        """
        Get table headers for GUI display.
        
        Returns:
            List of column headers
        """
        headers = []
        
        if self.log_viewer.config.show_timestamps:
            headers.append("时间")
        
        headers.append("级别")
        
        if self.log_viewer.config.show_categories:
            headers.append("类别")
        
        if self.log_viewer.config.show_components:
            headers.append("组件")
        
        headers.append("消息")
        
        if self.log_viewer.config.show_details:
            headers.append("详情")
        
        return headers
    
    def get_entry_details(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific log entry.
        
        Args:
            entry_id: Log entry ID
            
        Returns:
            Detailed entry information or None if not found
        """
        for display_entry in self.log_viewer.display_entries:
            if display_entry.entry_id == entry_id:
                entry = display_entry.raw_entry
                
                return {
                    "entry_id": entry.entry_id,
                    "timestamp": entry.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    "level": entry.level.value,
                    "category": entry.category.value,
                    "component": entry.component,
                    "message": entry.message,
                    "details": json.dumps(entry.details, indent=2, ensure_ascii=False) if entry.details else "无",
                    "error_details": json.dumps(entry.error_details, indent=2, ensure_ascii=False) if entry.error_details else "无",
                    "stack_trace": entry.stack_trace or "无"
                }
        
        return None
    
    def set_gui_callback(self, event_name: str, callback: Callable) -> None:
        """
        Set GUI-specific callback for events.
        
        Args:
            event_name: Name of the event (update, error, etc.)
            callback: Callback function
        """
        self.gui_callbacks[event_name] = callback
        
        # Wire up to log viewer callbacks
        if event_name == "update":
            self.log_viewer.add_update_callback(lambda entries: callback())
        elif event_name == "error":
            self.log_viewer.add_error_callback(callback)
    
    def create_search_interface_data(self) -> Dict[str, Any]:
        """
        Create data structure for GUI search interface.
        
        Returns:
            Search interface configuration data
        """
        return {
            "log_levels": [level.value for level in LogLevel],
            "categories": [category.value for category in LogCategory],
            "components": list(set(entry.raw_entry.component for entry in self.log_viewer.display_entries)),
            "time_ranges": [
                {"label": "过去1小时", "hours": 1},
                {"label": "过去6小时", "hours": 6},
                {"label": "过去24小时", "hours": 24},
                {"label": "过去7天", "hours": 168},
                {"label": "全部", "hours": None}
            ],
            "export_formats": [
                {"label": "JSON", "value": "json"},
                {"label": "CSV", "value": "csv"},
                {"label": "文本", "value": "txt"}
            ]
        }