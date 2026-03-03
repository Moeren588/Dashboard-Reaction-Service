# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED]

## [0.9.0] - 2026-03-03 (2026 Release)

### CHANGED
- Updated `drs_data` to reflect the new 2026 season (thank you to [staglech](https://github.com/staglech))
- Tests and debugs updated to reflect new driver numbers

## [0.8.0] - 2025-11-22 (PITWALL release)

### ADDED
- Processing of `TrackStatus`:
  - in `FP1` They changed yellow flags from `RaceControl` to `TrackStatus`
- Clearing of yellow flag sectors when returning to green (as a just in case missed)
- A combined starter script (starts both livetiming and DRS) called `pitwall.py`

### CHANGED
- Moved session retention on shutdown to its own function
- Updates to `README.md` as work on moving more in-depth info into the Github Wiki has started
- improved docstrings to following modules:
  - `f1_utils.py`

## [0.7.0] - 2025-10-18 (FREEDOM release)

### ADDED
- Team Color to drs_data
- Team Color to the MQTT message on leader
- Template files for the configs
- Session Caching (#10)
- Added tests for `main.py` and `session_state.py`
- Deleted lap time debug line (not used yet)

### CHANGED
- Moving business logic in `main.py` to dedicated functions (#16)
- `--force-lead` (`-fl`) is now **required** to provide for Races (Austin SR T1 is a great example for why the service needs to know how to reset after a Safety Car)

### REMOVED
- `config.py` from being tracked in the git repo

### FIXED
- `--force-lead` being very fragile in the accepted inputs.

## [0.6.2] - 2025-10-11

### FIXED
- Error when using --force-lead

## [0.6.1] - 2025-10-04

### FIXED
- Error when reseting to new Qualifying Session.

## [0.6.0] - 2025-10-02 (SINGAPORE release)

### ADDED
- Testing suite (using pytest)
- (#12) team and drivers data as a seperate json: "data/drs_data.json"
- (#11) load_drs_data() in `main.py` to fetch the teams and drivers data, temporarily stored in session_data (until this is moved to its own Class)
- Session simulation tool (tools/simulation_run.py) as an end-to-end test
- "driver_num" to MQTT LEADER_TOPIC broadcast

### CHANGED
- Set up a folder structure to organize the project: Code has now been played under `src/drs`!
- how it sets the parsing function for incomming lines: now it is if race, else the rest (no need to specifically check for qualifying)
- Moved session_state into its own Class.
- `requirements.txt` is now as minimal as possible (use `requirements_dev.txt` for development)

### FIXED
- Not setting session leader when forcing lead

### REMOVED
- (#8) Removed the use of pandas in `f1_utils`, however the `FastF1` API still requires it, so it cannot be removed from the project.
- Laptime when sending leader change over MQTT durin fp and quali (this was never sent during races, so it unifies the expected payload)

### DEPRECATED
- (#12) `f1_utils.get_team_by_driver()`
- (#11) session_state as a Dict object

## [0.5.2] - 2025-09-20

### ADDED
- return_to_green function to avoid code repetition.
- Broadcasting GREEN flag to MQTT
- Added process_session_data_line function

### CHANGED
- How start of session is read for *all* sessions, should make Calibration more reliable

### FIXED
- Not rebroadcasting lead when there is no lead recorded
- RED FLAG status never clearing (thanks to @Gtwizzy for finding the solution)

### REMOVED
- The dedicated "look for start of session" function, merged into a neater session data line processor

## [0.5.1] - 2025-09-19

### FIXED
- Trying to access LEADER_TOPIC from `f1_utils` in `main.py`

## [0.5.0] - 2025-09-17

### ADDED
- mqtt_topics module
- Better flag handling

### FIXED
- Error with setting race lead in race mode
- Not reading Flag messages anymore

### CHANGED
- Moved all MQTT topics to its own file (mqtt_topics module)
  - Changed how topics were accessed in scripts
- How flags and inshidents are handled: Now more generalized session status rather than seperate "red flag" or "safety car"
- Changed state name for 'current_race_lead' to 'current_session_lead'
- all `eval()` to `ast.literal_eval()`
- using `time.monotonic()` instead of `datetime.now()` for qualifying session monitoring
- Rewrote the README

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