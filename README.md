# AI-Driven Self-Healing Campus Network

An SDN-based framework for autonomous fault detection and recovery in a simulated campus network.

## Overview

This project uses Mininet, Open vSwitch, and the OS-Ken SDN controller to simulate a campus network with redundant paths. Machine learning detects abnormal network conditions, while the recovery workflow identifies likely link failures and requests rerouting through backup paths.

The project also includes port-level congestion monitoring and optional, explicitly targeted routing-cost mitigation.

## Key Features

- Campus topology with five switches and four end hosts.
- SDN routing using OpenFlow.
- Fault injection for link failures and congestion.
- Isolation Forest for anomaly detection.
- Random Forest for fault classification.
- Automated fault localization and recovery.
- Congestion monitoring and targeted mitigation.
- Dataset generation, evaluation scripts, and automated tests.

## Technology Stack

Python, Mininet, Open vSwitch, OS-Ken, OpenFlow, scikit-learn, pandas, joblib, and Ubuntu Linux.

## Network Hosts

| Building | Host | IP address |
|---|---|---|
| Library | h_lib | 10.0.0.1 |
| Computer Science | h_cs | 10.0.0.2 |
| Administration | h_admin | 10.0.0.3 |
| Hostel | h_hos | 10.0.0.4 |

## Project Files

- `topology.py` — builds the campus topology.
- `controller_app.py` — SDN controller and routing logic.
- `controller_client.py` — communicates with the controller.
- `fault_injector.py` — injects and restores faults.
- `generate_dataset.py` — generates network telemetry data.
- `train_model.py` — trains the machine learning models.
- `healer.py` — coordinates fault localization and recovery experiments.
- `congestion_detector.py` — detects sustained high link utilization.
- `congestion_monitor.py` — monitors congestion.
- `congestion_healer.py` — performs optional targeted congestion mitigation.
- `decision_engine.py` — maps fault evidence to recovery decisions.
- `test_*.py` — automated test scripts.
- `evaluate_*.py` — model evaluation scripts.

## Evaluation

Recorded simulation experiments achieved approximately 99.5% Random Forest accuracy on one held-out split and approximately 98.7% mean accuracy in five-fold grouped evaluation for normal-versus-congestion classification.

These are results from generated simulation data, not an independent real-world campus network. Different evaluation protocols measure different tasks and should not be treated as directly interchangeable.

## Setup

Install and configure Mininet, Open vSwitch, OS-Ken, and the required Python libraries in Ubuntu.

Train the models using:

    python3 train_model.py

Start the controller in the environment where OS-Ken is installed:

    ~/ctrl_venv/bin/python run_controller.py

Start the topology in a separate terminal:

    sudo mn -c
    sudo python3 start_campus.py

Check each script's prerequisites before running tests or fault-injection experiments.

## Limitations

- The network is simulated.
- Dataset labels are based on controlled fault scenarios.
- Performance on unseen production networks has not been established.
- Congestion thresholds and routing costs are experimental configuration values.

## Author

G Haritharan

## License

No license has been selected yet.
