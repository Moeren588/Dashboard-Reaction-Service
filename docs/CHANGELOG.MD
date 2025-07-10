# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED]

### ADDED
- Safety Car message handling

### CHANGED
- Refactored the code to avoid the three different scripts
  - Now has one main.py point of enter, mandatory arguments are required now.

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