#!/usr/bin/env python3
"""
Main entry point for MQTT Camera Monitoring System
Supports both GUI and existing system modes with command-line options
"""

import sys
import os
import argparse
import logging
from typing import Optional

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging(log_level: str = "INFO") -> None:
    """Set up logging configuration"""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('mqtt_camera_monitoring_main.log', encoding='utf-8')
        ]
    )

def run_gui_mode(config_file: str, log_level: str) -> int:
    """Run the GUI application mode"""
    try:
        setup_logging(log_level)
        logger = logging.getLogger(__name__)
        logger.info("Starting MQTT Camera Monitoring GUI Application...")
        
        from mqtt_camera_monitoring.gui_main_application import MqttCameraMonitoringApp
        
        # Create and initialize application with configuration file
        app = MqttCameraMonitoringApp(config_file)
        
        if not app.initialize():
            logger.error("GUI application initialization failed")
            return 1
        
        logger.info("GUI application initialized successfully with configuration persistence")
        
        # Run application
        return app.run()
        
    except ImportError as e:
        print(f"GUI dependencies not available: {e}")
        print("Please install PySide6: pip install PySide6")
        return 1
    except Exception as e:
        print(f"GUI application failed: {e}")
        return 1

def run_existing_system_mode(config_file: str, mask_file: str, enable_view: bool, log_level: str) -> int:
    """Run the existing production system mode"""
    try:
        setup_logging(log_level)
        logger = logging.getLogger(__name__)
        logger.info("Starting MQTT Camera Monitoring Production System...")
        
        from final_production_system import main as production_main
        
        # Override sys.argv to pass arguments to the existing system
        original_argv = sys.argv.copy()
        sys.argv = ['final_production_system.py']
        
        if config_file != "config.yaml":
            sys.argv.extend(['--config', config_file])
        if mask_file != "fmask.png":
            sys.argv.extend(['--mask', mask_file])
        if enable_view:
            sys.argv.append('--view')
        if log_level != "INFO":
            sys.argv.extend(['--log-level', log_level])
        
        try:
            result = production_main()
            return result
        finally:
            # Restore original argv
            sys.argv = original_argv
            
    except Exception as e:
        print(f"Production system failed: {e}")
        return 1

def create_argument_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser"""
    parser = argparse.ArgumentParser(
        description="MQTT Camera Monitoring System - Main Entry Point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run GUI mode (default)
  python main.py
  
  # Run GUI mode with custom config
  python main.py --gui --config custom_config.yaml
  
  # Run existing production system mode
  python main.py --system --mask custom_mask.png
  
  # Run existing system with visual display
  python main.py --system --view
  
  # Run with debug logging
  python main.py --log-level DEBUG
        """
    )
    
    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--gui', 
        action='store_true', 
        default=True,
        help='Run GUI application mode (default)'
    )
    mode_group.add_argument(
        '--system', 
        action='store_true',
        help='Run existing production system mode'
    )
    
    # Configuration options
    parser.add_argument(
        '--config', 
        type=str, 
        default='config.yaml',
        help='Configuration file path (default: config.yaml)'
    )
    
    # System mode specific options
    parser.add_argument(
        '--mask', 
        type=str, 
        default='fmask.png',
        help='Mask file path for system mode (default: fmask.png)'
    )
    parser.add_argument(
        '--view', 
        action='store_true',
        help='Enable visual display in system mode'
    )
    
    # Logging options
    parser.add_argument(
        '--log-level', 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    # Version information
    parser.add_argument(
        '--version', 
        action='version', 
        version='MQTT Camera Monitoring System v1.0.0'
    )
    
    return parser

def validate_arguments(args: argparse.Namespace) -> bool:
    """Validate command-line arguments"""
    # Check if config file exists
    if not os.path.exists(args.config):
        print(f"Error: Configuration file not found: {args.config}")
        return False
    
    # Check mask file for system mode
    if args.system and not os.path.exists(args.mask):
        print(f"Error: Mask file not found: {args.mask}")
        return False
    
    return True

def handle_shutdown_signal(signum, frame):
    """Handle shutdown signals for proper application cleanup"""
    logger = logging.getLogger(__name__)
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

def main() -> int:
    """Main entry point with command-line argument parsing"""
    try:
        # Parse command-line arguments
        parser = create_argument_parser()
        args = parser.parse_args()
        
        # If --system is specified, set gui to False
        if args.system:
            args.gui = False
        
        # Validate arguments
        if not validate_arguments(args):
            return 1
        
        # Set up signal handlers for graceful shutdown
        import signal
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        signal.signal(signal.SIGTERM, handle_shutdown_signal)
        
        # Run appropriate mode
        if args.gui:
            print("Starting GUI mode...")
            return run_gui_mode(args.config, args.log_level)
        else:
            print("Starting production system mode...")
            return run_existing_system_mode(args.config, args.mask, args.view, args.log_level)
            
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 0
    except Exception as e:
        print(f"Application failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())