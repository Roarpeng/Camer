#!/usr/bin/env python3
"""
MQTT Camera Monitoring System - Main Entry Point

This script initializes and runs the MQTT camera monitoring system.
"""

import sys
import signal
import logging
from mqtt_camera_monitoring.config import ConfigManager
from mqtt_camera_monitoring.main_controller import MainController


def setup_logging(config):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        format=config.logging.format,
        handlers=[
            logging.FileHandler(config.logging.file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def main():
    """Main application entry point"""
    try:
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # Setup logging
        setup_logging(config)
        logger = logging.getLogger(__name__)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Starting MQTT Camera Monitoring System")
        logger.info(f"MQTT Broker: {config.mqtt.broker_host}:{config.mqtt.broker_port}")
        logger.info(f"Camera Count: {config.cameras.count}")
        
        # Initialize and run main controller
        controller = MainController(config)
        controller.run()
        
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()