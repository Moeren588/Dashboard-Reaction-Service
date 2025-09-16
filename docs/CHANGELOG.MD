# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED]

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