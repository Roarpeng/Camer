import logging
from PySide6.QtCore import QObject, Signal

class SignallingLogHandler(logging.Handler, QObject):
    """
    Custom Logging Handler that emits a signal for every log record.
    Connect this signal to a GUI text area.
    """
    log_signal = Signal(str)

    def __init__(self):
        super().__init__()
        QObject.__init__(self)

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_signal.emit(msg)
        except Exception:
            self.handleError(record)

def setup_logger():
    """Configures a logger with a default format."""
    logger = logging.getLogger("CamerApp")
    logger.setLevel(logging.INFO)
    
    # Console Handler for debugging
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    return logger

# Global logger instance
app_logger = setup_logger()
