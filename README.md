# MQTT Camera Monitoring System

A Python-based application that integrates MQTT messaging with USB camera monitoring. The system connects to an MQTT broker to receive state change messages, processes JSON payloads to count specific values, and controls multiple USB cameras to monitor red light changes in real-time.

## Project Structure

```
mqtt-camera-monitoring/
├── mqtt_camera_monitoring/          # Main package
│   ├── __init__.py                 # Package initialization
│   ├── mqtt_client.py              # MQTT communication component
│   ├── camera_manager.py           # USB camera management
│   ├── light_detector.py           # Red light detection algorithm
│   ├── trigger_publisher.py        # MQTT trigger message publisher
│   ├── main_controller.py          # Main system controller
│   └── config.py                   # Configuration management
├── tests/                          # Test package
│   ├── __init__.py
│   ├── test_mqtt_client.py
│   ├── test_camera_manager.py
│   ├── test_light_detector.py
│   ├── test_trigger_publisher.py
│   └── test_main_controller.py
├── config.yaml                    # System configuration file
├── requirements.txt               # Python dependencies
├── setup.py                      # Package setup script
├── main.py                       # Application entry point
└── README.md                     # This file
```

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install the package in development mode:
```bash
pip install -e .
```

## Configuration

Edit `config.yaml` to configure:
- MQTT broker settings
- Camera parameters
- Red light detection settings
- Logging configuration

## Usage

Run the system:
```bash
python main.py
```

Or using the installed console script:
```bash
mqtt-camera-monitor
```

## Testing

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=mqtt_camera_monitoring
```

## Requirements

- Python 3.8+
- USB cameras (up to 6 supported)
- MQTT broker access
- OpenCV-compatible camera drivers