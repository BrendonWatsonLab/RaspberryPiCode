# RaspberryPiCode

## Introduction
This repository contains scripts for setting up and running a Raspberry Pi-based event scheduler that checks internet connections, synchronizes time using NTP servers, and controls GPIO devices based on scheduled events loaded from a JSON configuration file.

## How to Use

### 1. Setting Up Raspbian OS
- **Installation**: Use the RPi Imager to download and install the latest 64-bit version of Raspbian OS onto an SD card. Download the imager from the [Raspberry Pi website](https://www.raspberrypi.org/software/).

### 2. Version Control
- **Repository Setup**: This project is not currently set up with Git version control. Manually download the latest code files from this GitHub repository(Upload the latest code on the repo as well). Ensure that the synchronizer code file and the JSON configuration file are placed in the same directory.

### 3. Setting JSON Parameters
- **Configuration**: The provided JSON file contains default values. Modify these parameters if the output pins, pulse duration, event timings, or event types change. Events can be configured to occur every minute, hour, day, or at specific times.

### 4. Running the Code on Startup
- **Setup**: Follow the tutorial on [Instructables](https://www.instructables.com/Raspberry-Pi-Launch-Python-script-on-startup/) to configure your Raspberry Pi to run the script at startup. After setup, any changes to the code or JSON file will require a system reboot to reflect the changes.

### 5. Debugging
- **Logs**: Use the generated log file to troubleshoot any issues or to verify whether the program has started correctly.

## Code Overview

### Internet Connection Check
- **Function**: `wait_for_internet_connection()` continuously checks for an active internet connection using primary and fallback URLs, logging each attempt's status.

### NTP Time Synchronization
- **Usage**: The script employs `ntplib` to synchronize with NTP servers such as `time.nist.gov` and `pool.ntp.org`, ensuring accurate timekeeping.

### EventScheduler Class
- **Initialization**: Sets up the scheduler with a time offset and prepares for event and GPIO device management.
- **Methods**:
  - `update_offset()`: Asynchronously updates the time offset by querying NTP servers.
  - `load_events_from_json(file_path)`: Loads and processes event configurations from a JSON file, scheduling them according to their timing and repetition settings.
  - `calculate_initial_datetime()`: Determines the initial datetime for events based on current time settings.
  - `setup_device(pin, initial_value)`: Initializes `DigitalOutputDevice` instances for GPIO pin control.
  - `get_callback(callback_name, pin, duration)`: Maps callback names to corresponding functions for GPIO control.
  - `add_event(event_time, callback, description, repeat)`: Adds and sorts events in the scheduler.
  - `run()`: Main loop that continuously monitors and executes due events, rescheduling as needed.

### GPIO Control
- **Functions**: Include `turn_on_starter()`, `turn_off_starter()`, and `give_pulse()` for interacting with GPIO pins and controlling devices based on event configurations.
