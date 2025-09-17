# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED]

## ADDED
- mqtt_topics module
- Better flag handling

## FIXED
- Error with setting race lead in race mode
- Not reading Flag messages anymore

### CHANGED
- Moved all MQTT topics to its own file (mqtt_topics module)
  - Changed how topics were accessed in scripts
- How flags and inshidents are handled: Now more generalized session status rather than seperate "red flag" or "safety car"
- Changed state name for 'current_race_lead' to 'current_session_lead'

### REMOVED
- Generic logging line that was sent when MQTT received a message
- f1_service.py file from project
- live_fp_monitoring_test.py from project

### DEPRECATED
- f1_service module
- live_fp_monitor_test module

## [0.4.0] - 2025-09-16

### ADDED
- Functionality to receive MQTT messages as well
- Logic to set offsets to the delay_timer based on user input from HA

### CHANGED
- Minor change to initial logging line for starting

### FIXED
- Errors with service shutting down due to non utf-8 codec

## [0.3.0] - 2025-07-19

### ADDED
- Safety Car message handling
- 'immediate' optional arg for mqtt.qeue_message, letting you bypass the delay

### CHANGED
- Refactored the code to avoid the three different scripts
  - Now has one main.py point of enter, mandatory arguments are required now.

### REMOVED
- The individual service module (now replaced by a combined main and utils)

### DEPRECATED
- 'free_practice_service', 'qualifying_service' and 'race_service'

## [0.2.0] - 2025.07.06

### ADDED
- Qualifying service
- Racing service
- Debug lines text file that can be pasted into the cache for testing (fetching from Brittish Grand Prix)

### CHANGED
- Changed the MQTT queueing logic

## [0.1.0] - 2025.07.05

### ADDED
- Initial project setup
  - MQTT service
  - config setup
  - gitnore setup
  - FastF1 livetiming listening structure:
    - Functioning for Free Practice
  - Changelog, Readme updates and HA setup