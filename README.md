# 🧭 SO(3) Resetability Control Suite

This project provides a comprehensive dashboard for analyzing the "resetability" of rotational systems based on SO(3) mathematics. It processes telemetry data from CSV files, live hardware streams, or simulations to calculate key metrics, provide domain-specific insights, and visualize system attitude.

![Screenshot of the App](assets/dashboard_screenshot.png) <!-- It's highly recommended to add a screenshot here -->

## Key Features

-   **Dual-Mode Operation:**
    -   **📡 Live Mode:** Processes data from a file being written in real-time.
    -   **🧪 Simulation Mode:** Replays historical telemetry from a CSV at variable speeds.
-   **Hardware Integration:** A built-in UI to connect to serial devices (like an Arduino or ESP32 with an IMU) for true live data logging.
-   **Core Metrics:** Autonomously computes **R** (resetability), **θ_net** (net rotation), and **Predicted Reset Benefit**.
-   **Rich Visualization:** Includes live-updating 2D metric plots and an interactive 3D attitude cube.
-   **Modular Domains:** Easily extensible for different applications (Robot, Spacecraft, Booster, etc.), with a quick-access switcher in the UI.
-   **Professional UX:** Remembers the user's last selected domain between visits and features an optional dark mode.
-   **Automated Reporting:** Automatically generates a PDF summary at the end of a simulation run.
-   **Advanced Analysis:** Dedicated tabs for post-mission event analysis (with replay) and robust Monte Carlo simulations.

## Project Structure

The application is built with a clean, modular architecture:

-   `app_resetability_live.py`: The main entry point for the Streamlit application.
-   `python/`: The core Python package containing all application logic.
-   `live_data_logger.py`: A standalone script (also used by the UI) to log data from serial ports.
-   `generate_telemetry_csv.py`: A utility to generate sample data for testing.
-   `tests/`: A `pytest` suite for ensuring the core mathematical functions are correct.
-   `.streamlit/config.toml`: Configuration file for the app's theme and behavior.

## Setup and Installation

This project uses a standard Python virtual environment (`venv`).

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/YourUsername/so3-resetability-suite.git
    cd so3-resetability-suite
    ```

2.  **Create and Activate the Virtual Environment:**
    ```bash
    # Create the venv
    python -m venv venv

    # Activate it (Windows PowerShell)
    .\venv\Scripts\Activate.ps1

    # Activate it (Linux/macOS)
    source venv/bin/activate
    ```

3.  **Install the Required Libraries:**
    ```bash
    pip install -r requirements.txt
    ```

## How to Use the Application

### Running the Dashboard
Ensure you are in the project's root directory and the virtual environment is activated. Run the application using the following command, which is the most robust method:
```bash
python -m streamlit run app_resetability_live.py
```

The dashboard will open in your web browser.

### Generating Sample Data
If you don't have a telemetry file, you can generate one using the provided script.
code
``` bash
python generate_telemetry_csv.py
```
This will create a new data/telemetry.csv file.

### Connecting Live Hardware
Connect your IMU device (e.g., Arduino, ESP32) that is programmed to send quaternion data over its serial port.
In the app's sidebar, go to the "Live Data Logger" section.
Click "Scan for Serial Ports."
Select your device from the dropdown and click "Start Logging."
Ensure the app is in "Live Mode," and it will begin processing the data from your device.