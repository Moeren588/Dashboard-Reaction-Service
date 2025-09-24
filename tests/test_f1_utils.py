import pytest
from freezegun import freeze_time
from unittest.mock import Mock, MagicMock
import json
from datetime import timedelta
import time

from src.drs.f1_utils import process_session_data_line, process_race_control_line, process_race_lead_line, process_lap_time_line, reset_for_next_session
from src.drs.mqtt_topics import MqttTopics

# --- Fixtures ---

@pytest.fixture
def state():
    """Provides a fresh state dict"""
    return {
        "session_type" : "race",
        "fastest_lap_info": {"Time": timedelta(days=1), "Driver": None, "Team": None},
        "driver_abbreviations": {},
        "current_session_lead": {"Driver": None, "Team": None},
        "current_leader_num": None,
        "cooldown_active": False,
        "session_end_time": None,
        "quali_session" : "Q1",
        "yellow_flags": set(), # Storing the Sectors of the Yellow flags
        "race_state": "GREEN", # Storing in what the race status is: Green is good
        # For calibration
        "true_session_start_time": None,
        "calibration_window_end_time": None,
    }

@pytest.fixture
def mock_mqtt():
    """Provides a fresh mock MQTT handler"""
    return Mock()

# --- Tests ---
## New fastest lap (quali and fp)
def test_process_new_fastest_lap_lead_change(mock_mqtt):
    """Tests that a new fastest lap and leader is correctly identified and an MQTT is queued"""
    # Setup
    initial_state = {
        "session_type" : "qualifying",
        "fastest_lap_info": {"Time": timedelta(days=1), "Driver": None, "Team": None},
        "current_session_lead": {"Driver": None, "Team": None},
        "teams_data": {'alpine' : {'name' : 'Alpine'}, 'williams' : {'name' : 'Williams'}},
        "drivers_data": {'10' : {'abbreviation' : 'GAS', 'team_key' : 'alpine'}, '55' : {'abbreviation' : 'SAI', 'team_key' : 'williams'}}
    }
    new_fastest_lap_line = "['TimingData', {'Lines': {'10': {'NumberOfLaps': 3, 'Sectors': {'2': {'Value': '24.386'}}, 'Speeds': {'FL': {'Value': '250'}}, 'BestLapTime': {'Value': '1:28.552', 'Lap': 2}, 'LastLapTime': {'Value': '1:28.552', 'OverallFastest': True, 'PersonalFastest': True}}}}, '2025-07-05T10:38:19.212Z']"

    # Execute
    process_lap_time_line(new_fastest_lap_line, initial_state, mock_mqtt)

    # Asserts
    ## States
    assert initial_state['fastest_lap_info']['Time'] == timedelta(minutes=1, seconds=28, microseconds=552000)
    assert initial_state['fastest_lap_info']['Driver'] == 'GAS'
    assert initial_state['fastest_lap_info']['Team'] == 'Alpine'
    ## MQTT
    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"driver": "GAS", "team": "Alpine"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.LEADER_TOPIC, expected_payload)

    # New Fastest Lap
    new_fastest_lap_line = "['TimingData', {'Lines': {'55': {'NumberOfLaps': 3, 'Sectors': {'2': {'Value': '24.386'}}, 'Speeds': {'FL': {'Value': '250'}}, 'BestLapTime': {'Value': '1:28.552', 'Lap': 2}, 'LastLapTime': {'Value': '1:26.552', 'OverallFastest': True, 'PersonalFastest': True}}}}, '2025-07-05T10:38:19.212Z']"

    process_lap_time_line(new_fastest_lap_line, initial_state, mock_mqtt)
    # Asserts
    ## States
    assert initial_state['fastest_lap_info']['Time'] == timedelta(minutes=1, seconds=26, microseconds=552000)
    assert initial_state['fastest_lap_info']['Driver'] == 'SAI'
    assert initial_state['fastest_lap_info']['Team'] == 'Williams'

    ## MQTT
    assert mock_mqtt.queue_message.call_count == 2
    expected_payload = json.dumps({"driver": "SAI", "team": "Williams"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.LEADER_TOPIC, expected_payload)

def test_slower_lap_registered_no_lead_change(mock_mqtt):
    """Tests that a slower lap do not trigger any changes in lead time"""
    initial_state = {
        "session_type" : "qualifying",
        "fastest_lap_info": {"Time": timedelta(minutes=1, seconds=20), "Driver": "VER", "Team": "Red Bull"},
        "current_session_lead": {"Driver": None, "Team": None},
    }
    new_fastest_lap_line = "['TimingData', {'Lines': {'10': {'NumberOfLaps': 3, 'Sectors': {'2': {'Value': '24.386'}}, 'Speeds': {'FL': {'Value': '250'}}, 'BestLapTime': {'Value': '1:28.552', 'Lap': 2}, 'LastLapTime': {'Value': '1:28.552', 'OverallFastest': True, 'PersonalFastest': True}}}}, '2025-07-05T10:38:19.212Z']"

    # Execute
    process_lap_time_line(new_fastest_lap_line, initial_state, mock_mqtt)
    
    assert initial_state['fastest_lap_info']['Time'] == timedelta(minutes=1, seconds=20)
    assert initial_state['fastest_lap_info']['Driver'] == "VER"
    assert initial_state['fastest_lap_info']['Team'] == "Red Bull"
    mock_mqtt.queue_message.assert_not_called()

## Race Lead Change
def test_process_race_lead_line_new_leader(mock_mqtt):
    """Tests that a new leader is correctly identified and an MQTT is queued"""
    # Setup
    new_lead_line = "['TopThree', {'Lines': {'0': {'RacingNumber': '1', 'Tla': 'VER', 'BroadcastName': 'M VERSTAPPEN', 'FullName': 'Max VERSTAPPEN', 'FirstName': 'Max', 'LastName': 'Verstappen', 'Reference': 'MAXVER01', 'Team': 'Red Bull Racing', 'TeamColour': '4781D7', 'LapTime': '2:42.616'}, '1': {'RacingNumber': '81', 'Tla': 'PIA', 'BroadcastName': 'O PIASTRI', 'FullName': 'Oscar PIASTRI', 'FirstName': 'Oscar', 'LastName': 'Piastri', 'Reference': 'OSCPIA01', 'Team': 'McLaren', 'TeamColour': 'F47600', 'LapTime': '2:43.087', 'DiffToAhead': '', 'DiffToLeader': ''}}}, '2025-07-06T14:49:09.888Z']"
    initial_state = {
        "current_leader_num": "16",
        "current_session_lead": {"Driver": "LEC", "Team": "Ferrari"},
        "teams_data": {'red_bull' : {'name' : 'Red Bull'}},
        "drivers_data": {'1' : {'abbreviation' : 'VER', 'team_key' : 'red_bull'}}
    }

    # Execute
    process_race_lead_line(new_lead_line, initial_state, mock_mqtt)

    # Asserts
    ## First state check
    assert initial_state["current_leader_num"] == "1", "Should be 1 for Verstappen"
    assert initial_state["current_session_lead"]["Driver"] == "VER", "Should be VER for Verstappen"
    assert initial_state["current_session_lead"]["Team"] == "Red Bull", "Should be Red Bull"

    ## Then check MQTT
    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"driver" : "VER", "team" : "Red Bull"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.LEADER_TOPIC, expected_payload)

## Test Qualifying transitions.
def test_qualifying_transitions(state, mock_mqtt, freezer):
    """Testing that Qualifying ends, transitions between states and resets inbetween"""
    # Setup
    def check_for_reset(state): # mimics the if block in main.py's while loop
        if (state['session_type'] == 'qualifying' and 
            state['cooldown_active'] and 
            state['session_end_time'] and 
            state['quali_session'] != 'Q3'):
            if (time.monotonic() - state['session_end_time']) > 180:
                reset_for_next_session(state)

    fast_lap_time = timedelta(minutes=1, seconds=28, microseconds=552000)
    fast_lap_time_line = "['TimingData', {'Lines': {'10': {'NumberOfLaps': 3, 'Sectors': {'2': {'Value': '24.386'}}, 'Speeds': {'FL': {'Value': '250'}}, 'BestLapTime': {'Value': '1:28.552', 'Lap': 2}, 'LastLapTime': {'Value': '1:28.552', 'OverallFastest': True, 'PersonalFastest': True}}}}, '2025-07-05T10:38:19.212Z']"
    chequered_flag_line = "['RaceControlMessages', {'Messages': {'14': {'Utc': '2025-07-05T14:27:49', 'Category': 'Flag', 'Flag': 'CHEQUERED', 'Scope': 'Track', 'Message': 'CHEQUERED FLAG'}}}, '2025-07-05T14:27:49.153Z']"

    state['session_type'] = 'qualifying'
    process_lap_time_line(fast_lap_time_line, state, mock_mqtt)

    # Chequered flag Q1 check
    process_race_control_line(chequered_flag_line, state, mock_mqtt)

    assert state['cooldown_active'] == True
    assert state['session_end_time'] is not None
    print(f"DEBUG - Q1 should have ended: {state['session_end_time']}")

    freezer.tick(timedelta(seconds=200))
    check_for_reset(state)
    assert state['cooldown_active'] == False
    assert state['session_end_time'] is None
    assert state['quali_session'] == 'Q2'
    assert state['fastest_lap_info']['Time'] > fast_lap_time

    # Set new fast lap right after chequered flag (check that it doesn't reset too quickly)
    process_race_control_line(chequered_flag_line, state, mock_mqtt)
    assert state['cooldown_active'] == True
    assert state['session_end_time'] is not None   
    freezer.tick(timedelta(seconds=30))
    process_lap_time_line(fast_lap_time_line, state, mock_mqtt)
    assert state["fastest_lap_info"]["Time"] == fast_lap_time

    # Wait for Q3 to start
    freezer.tick(timedelta(seconds=170))
    check_for_reset(state)
    assert state['cooldown_active'] == False
    assert state['session_end_time'] is None
    assert state['quali_session'] == 'Q3'
    assert state['fastest_lap_info']['Time'] > fast_lap_time

## Yellow Flag and Clear
def test_yellow_flag_and_clear_scenario(state, mock_mqtt):
    """Testing when yellow flags are raised and then cleared"""
    # Set yellow flag in sector 2
    yellow_flag_line = "['RaceControlMessages', {'Messages': {'56': {'Utc': '2025-07-05T11:39:56', 'Category': 'Flag', 'Flag': 'YELLOW', 'Scope': 'Sector', 'Sector': 2, 'Message': 'YELLOW IN TRACK SECTOR 2'}}}, '2025-07-05T11:39:56.262Z']"

    process_race_control_line(yellow_flag_line, state, mock_mqtt)

    # Assert
    ## States
    assert state['race_state'] == 'YELLOW'
    assert 2 in state['yellow_flags']

    ## MQTT
    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"flag": "YELLOW", "message": "YELLOW IN TRACK SECTOR 2"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)

    # Clear yellow flag
    clear_flag_line = "['RaceControlMessages', {'Messages': {'13': {'Utc': '2025-09-06T14:22:44', 'Category': 'Flag', 'Flag': 'CLEAR', 'Scope': 'Sector', 'Sector': 2, 'Message': 'CLEAR IN TRACK SECTOR 8'}}}, '2025-09-06T14:22:43.772Z']"
    process_race_control_line(clear_flag_line, state, mock_mqtt)

    # ASSERT
    ## States
    assert state['race_state'] == 'GREEN'
    assert len(state['yellow_flags']) == 0

    ## MQTT
    assert mock_mqtt.queue_message.call_count == 2
    expected_payload = json.dumps({"flag": "GREEN", "message": "GREEN FLAG, ALL YELLOW CLEARED"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)

# Testing Full Safety Car Deployed
def test_safety_car_deployed_scenario(state, mock_mqtt):
    """Testing full safety car deployment"""
    # Setup
    safety_car_line = "['RaceControlMessages', {'Messages': {'97': {'Utc': '2025-07-06T14:29:14', 'Lap': 14, 'Category': 'SafetyCar', 'Status': 'DEPLOYED', 'Mode': 'SAFETY CAR', 'Message': 'SAFETY CAR DEPLOYED'}}}, '2025-07-06T14:29:14.267Z']"
    
    process_race_control_line(safety_car_line, state, mock_mqtt)

    # Asserting
    assert state['race_state'] == 'SAFETY CAR'

    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"flag": "SAFETY CAR", "message": "SAFETY CAR"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)
    
# Testing Full safety car In This Lap
def test_safety_car_in_scenario(state, mock_mqtt):
    """Testing full safety car in this lap"""
    # Setup
    safety_car_ending_line = "['RaceControlMessages', {'Messages': {'99': {'Utc': '2025-07-06T14:38:36', 'Lap': 17, 'Category': 'SafetyCar', 'Status': 'IN THIS LAP', 'Mode': 'SAFETY CAR', 'Message': 'SAFETY CAR IN THIS LAP'}}}, '2025-07-06T14:38:36.526Z']"
    state['race_state'] = 'SAFETY CAR'

    process_race_control_line(safety_car_ending_line, state, mock_mqtt)

    # Asserting
    assert state['race_state'] == 'GREEN'

    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"flag": "GREEN", "message": "SAFETY CAR ENDING"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)

# Testing Virtual Safety Car Deployed
def test_vsc_deployed_scenario(state, mock_mqtt):
    """Testing virtual safety car deployment"""
    # Setup
    vsc_line = "['RaceControlMessages', {'Messages': {'67': {'Utc': '2025-07-06T14:05:48', 'Lap': 2, 'Category': 'SafetyCar', 'Status': 'DEPLOYED', 'Mode': 'VIRTUAL SAFETY CAR', 'Message': 'VIRTUAL SAFETY CAR DEPLOYED'}}}, '2025-07-06T14:05:47.647Z']"

    process_race_control_line(vsc_line, state, mock_mqtt)

    # Asserting
    assert state['race_state'] == 'SAFETY CAR'

    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"flag": "SAFETY CAR", "message": "VIRTUAL SAFETY CAR"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)

# Testing Virtual Safety Car Ending
def test_vsc_ending_scenario(state, mock_mqtt):
    """Testing full safety car in this lap"""
    # Setup
    vsc_ending_line = "['RaceControlMessages', {'Messages': {'72': {'Utc': '2025-07-06T14:10:18', 'Lap': 4, 'Category': 'SafetyCar', 'Status': 'ENDING', 'Mode': 'VIRTUAL SAFETY CAR', 'Message': 'VIRTUAL SAFETY CAR ENDING'}}}, '2025-07-06T14:10:17.861Z']"
    state['race_state'] = 'SAFETY CAR'

    process_race_control_line(vsc_ending_line, state, mock_mqtt)

    # Asserting
    assert state['race_state'] == 'GREEN'

    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"flag": "GREEN", "message": "SAFETY CAR ENDING"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)

# Test Red Flag
def test_red_flag_scenario(state, mock_mqtt):
    """Testing when red flags are raised and then cleared"""
    # Set red flag
    red_flag_line = "['RaceControlMessages', {'Messages': {'50': {'Utc': '2025-07-05T11:33:58', 'Category': 'Flag', 'Flag': 'RED', 'Scope': 'Track', 'Message': 'RED FLAG'}}}, '2025-07-05T11:33:58.102Z']"
    process_race_control_line(red_flag_line, state, mock_mqtt)

    # Assert
    ## States
    assert state['race_state'] == 'RED'
    ## MQTT
    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"flag": "RED", "message": "RED FLAG"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)
    
def test_red_flag_ending_scenario(state, mock_mqtt):
    """Testing that end of Red flag and back to Green conditions"""
    # Setup
    state['true_session_start_time'] = time.monotonic()
    state['race_state'] = 'RED'
    cleared_flag_line = "['SessionData', {'StatusSeries': {'4': {'Utc': '2025-09-07T13:03:34.805Z', 'SessionStatus': 'Started'}}}, '2025-09-07T13:03:34.805Z']"
    
    process_session_data_line(cleared_flag_line, state, mock_mqtt)

    # ASSERT
    ## States
    assert state['race_state'] == 'GREEN'
    ## MQTT
    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"flag": "GREEN", "message": "GREEN FLAG, RED flag cleared"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)