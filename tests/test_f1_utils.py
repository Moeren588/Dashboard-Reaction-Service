import dataclasses
import pytest
from freezegun import freeze_time
from unittest.mock import Mock, MagicMock
import json
from datetime import timedelta
import time

from src.drs.f1_utils import process_session_data_line, process_race_control_line, process_race_lead_line, process_lap_time_line
from src.drs.mqtt_topics import MqttTopics
from src.drs.session_state import SessionState

# --- Fixtures ---

MOCK_DRS_DATA = {
    "drivers": {
        "1" : {'abbreviation' : 'VER', 'team_key' : 'red_bull'},
        "10" : {'abbreviation' : 'GAS', 'team_key' : 'alpine'},
        "16" : {'abbreviation' : 'LEC', 'team_key' : 'ferrari'},
        "55" : {'abbreviation' : 'SAI', 'team_key' : 'williams'}
    },
    "teams" : {
        'red_bull' : {'name' : 'Red Bull', "color_hex": "4781D7"},
        'ferrari' : {'name' : 'Ferrari', "color_hex": "ED1131"},
        'alpine' : {'name' : 'Alpine', "color_hex": "00A1E8"},
        'williams' : {'name' : 'Williams', "color_hex": "1868DB"}
    }
}

@pytest.fixture
def state():
    """Provides a fresh state dict"""
    return SessionState(session_type='race', drivers_data=MOCK_DRS_DATA["drivers"], teams_data=MOCK_DRS_DATA["teams"])

@pytest.fixture
def mock_mqtt():
    """Provides a fresh mock MQTT handler"""
    return Mock()

# --- Tests ---

class TestProcessLapTimeLine:
    ## New fastest lap (quali and fp)
    def test_process_new_fastest_lap_lead_change_initial(self, state:SessionState, mock_mqtt: Mock):
        """Tests that a new fastest lap and leader is correctly identified with initial state value (1 day fastest lap)"""
        # Setup
        state.session_type = 'qualifying'
        new_fastest_lap_line = "['TimingData', {'Lines': {'10': {'NumberOfLaps': 3, 'Sectors': {'2': {'Value': '24.386'}}, 'Speeds': {'FL': {'Value': '250'}}, 'BestLapTime': {'Value': '1:28.552', 'Lap': 2}, 'LastLapTime': {'Value': '1:28.552', 'OverallFastest': True, 'PersonalFastest': True}}}}, '2025-07-05T10:38:19.212Z']"

        # Execute
        process_lap_time_line(new_fastest_lap_line, state, mock_mqtt)

        # Asserts
        ## States
        assert state.fastest_lap_info.time == timedelta(minutes=1, seconds=28, microseconds=552000)
        assert state.fastest_lap_info.driver == 'GAS'
        assert state.fastest_lap_info.team == 'Alpine'
        ## MQTT
        mock_mqtt.queue_message.assert_called_once()
        expected_payload = json.dumps({"driver": "GAS", "driver_number": "10", "team": "Alpine", "team_color": "00A1E8"})
        mock_mqtt.queue_message.assert_called_with(MqttTopics.LEADER_TOPIC, expected_payload)

    def test_process_new_fastest_lap_lead_change(self, state:SessionState, mock_mqtt: Mock):
        """Tests that a new fastest lap and leader is correctly identified when a fast lap has been already set (smaller margines)"""
        # New Fastest Lap
        state.session_type = 'pracitce'
        state.set_fastest_lap(lap_time=timedelta(minutes=1, seconds=30), driver='GAS', team='Alpine')
        
        new_fastest_lap_line = "['TimingData', {'Lines': {'55': {'NumberOfLaps': 3, 'Sectors': {'2': {'Value': '24.386'}}, 'Speeds': {'FL': {'Value': '250'}}, 'BestLapTime': {'Value': '1:28.552', 'Lap': 2}, 'LastLapTime': {'Value': '1:26.552', 'OverallFastest': True, 'PersonalFastest': True}}}}, '2025-07-05T10:38:19.212Z']"

        process_lap_time_line(new_fastest_lap_line, state, mock_mqtt)
        # Asserts
        ## States
        assert state.fastest_lap_info.time == timedelta(minutes=1, seconds=26, microseconds=552000)
        assert state.fastest_lap_info.driver == 'SAI'
        assert state.fastest_lap_info.team == 'Williams'

        ## MQTT
        mock_mqtt.queue_message.assert_called_once()
        expected_payload = json.dumps({"driver": "SAI", "driver_number" : "55", "team": "Williams", "team_color": "1868DB"})
        mock_mqtt.queue_message.assert_called_with(MqttTopics.LEADER_TOPIC, expected_payload)

    def test_slower_lap_registered_no_lead_change(self, state:SessionState, mock_mqtt: Mock):
        """Tests that a slower lap do not trigger any changes in lead time"""
        state.session_type = 'qualifying'
        state.set_fastest_lap(lap_time=timedelta(minutes=1, seconds=20), driver='VER', team='Red Bull')
        state.set_session_lead(driver='VER', driver_number='1', team='Red Bull')
        new_fastest_lap_line = "['TimingData', {'Lines': {'10': {'NumberOfLaps': 3, 'Sectors': {'2': {'Value': '24.386'}}, 'Speeds': {'FL': {'Value': '250'}}, 'BestLapTime': {'Value': '1:28.552', 'Lap': 2}, 'LastLapTime': {'Value': '1:28.552', 'OverallFastest': True, 'PersonalFastest': True}}}}, '2025-07-05T10:38:19.212Z']"

        # Execute
        process_lap_time_line(new_fastest_lap_line, state, mock_mqtt)
        
        assert state.fastest_lap_info.time == timedelta(minutes=1, seconds=20)
        assert state.fastest_lap_info.driver == "VER"
        assert state.fastest_lap_info.team == "Red Bull"
        mock_mqtt.queue_message.assert_not_called()

    ## Test Qualifying transitions.
    def test_qualifying_transitions(self, state: SessionState, mock_mqtt: Mock, freezer):
        """Testing that Qualifying ends, transitions between states and resets inbetween"""
        # Setup
        def check_for_reset(state: SessionState): # mimics the if block in main.py's while loop
            if (state.session_type == 'qualifying' and 
                state.cooldown_active and 
                state.session_end_time and 
                state.quali_session != 'Q3'):
                if (time.monotonic() - state.session_end_time) > 180:
                    state.reset_for_next_quali_segment()

        fast_lap_time = timedelta(minutes=1, seconds=28, microseconds=552000)
        fast_lap_time_line = "['TimingData', {'Lines': {'10': {'NumberOfLaps': 3, 'Sectors': {'2': {'Value': '24.386'}}, 'Speeds': {'FL': {'Value': '250'}}, 'BestLapTime': {'Value': '1:28.552', 'Lap': 2}, 'LastLapTime': {'Value': '1:28.552', 'OverallFastest': True, 'PersonalFastest': True}}}}, '2025-07-05T10:38:19.212Z']"
        chequered_flag_line = "['RaceControlMessages', {'Messages': {'14': {'Utc': '2025-07-05T14:27:49', 'Category': 'Flag', 'Flag': 'CHEQUERED', 'Scope': 'Track', 'Message': 'CHEQUERED FLAG'}}}, '2025-07-05T14:27:49.153Z']"

        state.session_type = 'qualifying'
        process_lap_time_line(fast_lap_time_line, state, mock_mqtt)

        # Chequered flag Q1 check
        process_race_control_line(chequered_flag_line, state, mock_mqtt)

        assert state.cooldown_active == True
        assert state.session_end_time is not None
        print(f"DEBUG - Q1 should have ended: {state.session_end_time}")

        freezer.tick(timedelta(seconds=200))
        check_for_reset(state)
        assert state.cooldown_active == False
        assert state.session_end_time is None
        assert state.quali_session == 'Q2'
        assert state.fastest_lap_info.time > fast_lap_time

        # Set new fast lap right after chequered flag (check that it doesn't reset too quickly)
        process_race_control_line(chequered_flag_line, state, mock_mqtt)
        assert state.cooldown_active == True
        assert state.session_end_time is not None   
        freezer.tick(timedelta(seconds=30))
        process_lap_time_line(fast_lap_time_line, state, mock_mqtt)
        assert state.fastest_lap_info.time == fast_lap_time

        # Wait for Q3 to start
        freezer.tick(timedelta(seconds=170))
        check_for_reset(state)
        assert state.cooldown_active == False
        assert state.session_end_time is None
        assert state.quali_session == 'Q3'
        assert state.fastest_lap_info.time > fast_lap_time

## Yellow Flag and Clear
def test_yellow_flag_and_clear_scenario(state: SessionState, mock_mqtt: Mock):
    """Testing when yellow flags are raised and then cleared"""
    # Set yellow flag in sector 2
    yellow_flag_line = "['RaceControlMessages', {'Messages': {'56': {'Utc': '2025-07-05T11:39:56', 'Category': 'Flag', 'Flag': 'YELLOW', 'Scope': 'Sector', 'Sector': 2, 'Message': 'YELLOW IN TRACK SECTOR 2'}}}, '2025-07-05T11:39:56.262Z']"

    process_race_control_line(yellow_flag_line, state, mock_mqtt)

    # Assert
    ## States
    assert state.race_state == 'YELLOW'
    assert 2 in state.yellow_flags

    ## MQTT
    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"flag": "YELLOW", "message": "YELLOW IN TRACK SECTOR 2"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)

    # Clear yellow flag
    clear_flag_line = "['RaceControlMessages', {'Messages': {'13': {'Utc': '2025-09-06T14:22:44', 'Category': 'Flag', 'Flag': 'CLEAR', 'Scope': 'Sector', 'Sector': 2, 'Message': 'CLEAR IN TRACK SECTOR 8'}}}, '2025-09-06T14:22:43.772Z']"
    process_race_control_line(clear_flag_line, state, mock_mqtt)

    # ASSERT
    ## States
    assert state.race_state == 'GREEN'
    assert len(state.yellow_flags) == 0

    ## MQTT
    assert mock_mqtt.queue_message.call_count == 2
    expected_payload = json.dumps({"flag": "GREEN", "message": "GREEN FLAG, ALL YELLOW CLEARED"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)

# Testing Full Safety Car Deployed
def test_safety_car_deployed_scenario(state: SessionState, mock_mqtt: Mock):
    """Testing full safety car deployment"""
    # Setup
    safety_car_line = "['RaceControlMessages', {'Messages': {'97': {'Utc': '2025-07-06T14:29:14', 'Lap': 14, 'Category': 'SafetyCar', 'Status': 'DEPLOYED', 'Mode': 'SAFETY CAR', 'Message': 'SAFETY CAR DEPLOYED'}}}, '2025-07-06T14:29:14.267Z']"
    
    process_race_control_line(safety_car_line, state, mock_mqtt)

    # Asserting
    assert state.race_state == 'SAFETY CAR'

    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"flag": "SAFETY CAR", "message": "SAFETY CAR"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)
    
# Testing Full safety car In This Lap
def test_safety_car_in_scenario(state: SessionState, mock_mqtt: Mock):
    """Testing full safety car in this lap"""
    # Setup
    safety_car_ending_line = "['RaceControlMessages', {'Messages': {'99': {'Utc': '2025-07-06T14:38:36', 'Lap': 17, 'Category': 'SafetyCar', 'Status': 'IN THIS LAP', 'Mode': 'SAFETY CAR', 'Message': 'SAFETY CAR IN THIS LAP'}}}, '2025-07-06T14:38:36.526Z']"
    state.set_race_state('SAFETY CAR')

    process_race_control_line(safety_car_ending_line, state, mock_mqtt)

    # Asserting
    assert state.race_state == 'GREEN'

    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"flag": "GREEN", "message": "SAFETY CAR ENDING"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)

# Testing Virtual Safety Car Deployed
def test_vsc_deployed_scenario(state: SessionState, mock_mqtt: Mock):
    """Testing virtual safety car deployment"""
    # Setup
    vsc_line = "['RaceControlMessages', {'Messages': {'67': {'Utc': '2025-07-06T14:05:48', 'Lap': 2, 'Category': 'SafetyCar', 'Status': 'DEPLOYED', 'Mode': 'VIRTUAL SAFETY CAR', 'Message': 'VIRTUAL SAFETY CAR DEPLOYED'}}}, '2025-07-06T14:05:47.647Z']"

    process_race_control_line(vsc_line, state, mock_mqtt)

    # Asserting
    assert state.race_state == 'SAFETY CAR'

    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"flag": "SAFETY CAR", "message": "VIRTUAL SAFETY CAR"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)

# Testing Virtual Safety Car Ending
def test_vsc_ending_scenario(state:SessionState, mock_mqtt: Mock):
    """Testing full safety car in this lap"""
    # Setup
    vsc_ending_line = "['RaceControlMessages', {'Messages': {'72': {'Utc': '2025-07-06T14:10:18', 'Lap': 4, 'Category': 'SafetyCar', 'Status': 'ENDING', 'Mode': 'VIRTUAL SAFETY CAR', 'Message': 'VIRTUAL SAFETY CAR ENDING'}}}, '2025-07-06T14:10:17.861Z']"
    state.set_race_state('SAFETY CAR')

    process_race_control_line(vsc_ending_line, state, mock_mqtt)

    # Asserting
    assert state.race_state == 'GREEN'

    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"flag": "GREEN", "message": "SAFETY CAR ENDING"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)

# Test Red Flag
def test_red_flag_scenario(state: SessionState, mock_mqtt: Mock):
    """Testing when red flags are raised and then cleared"""
    # Set red flag
    red_flag_line = "['RaceControlMessages', {'Messages': {'50': {'Utc': '2025-07-05T11:33:58', 'Category': 'Flag', 'Flag': 'RED', 'Scope': 'Track', 'Message': 'RED FLAG'}}}, '2025-07-05T11:33:58.102Z']"
    process_race_control_line(red_flag_line, state, mock_mqtt)

    # Assert
    ## States
    assert state.race_state == 'RED'
    ## MQTT
    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"flag": "RED", "message": "RED FLAG"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)
    
def test_red_flag_ending_scenario(state: SessionState, mock_mqtt: Mock):
    """Testing that end of Red flag and back to Green conditions"""
    # Setup
    state.set_true_session_start_time(time.monotonic())
    state.set_race_state('RED')
    cleared_flag_line = "['SessionData', {'StatusSeries': {'4': {'Utc': '2025-09-07T13:03:34.805Z', 'SessionStatus': 'Started'}}}, '2025-09-07T13:03:34.805Z']"
    
    process_session_data_line(cleared_flag_line, state, mock_mqtt)

    # ASSERT
    ## States
    assert state.race_state == 'GREEN'
    ## MQTT
    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"flag": "GREEN", "message": "GREEN FLAG, RED flag cleared"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.FLAG_TOPIC, expected_payload)


TOP_THREE_LINE_VER_LEAD = "['TopThree', {'Lines': {'0': {'RacingNumber': '1', 'Tla': 'VER', 'BroadcastName': 'M VERSTAPPEN', 'FullName': 'Max VERSTAPPEN', 'FirstName': 'Max', 'LastName': 'Verstappen', 'Reference': 'MAXVER01', 'Team': 'Red Bull Racing', 'TeamColour': '4781D7', 'LapTime': '2:42.616'}, '1': {'RacingNumber': '81', 'Tla': 'PIA', 'BroadcastName': 'O PIASTRI', 'FullName': 'Oscar PIASTRI', 'FirstName': 'Oscar', 'LastName': 'Piastri', 'Reference': 'OSCPIA01', 'Team': 'McLaren', 'TeamColour': 'F47600', 'LapTime': '2:43.087', 'DiffToAhead': '', 'DiffToLeader': ''}}}, '2025-07-06T14:49:09.888Z']"


class TestProcessRaceLeadLine:
    ## Race Lead Change
    def test_process_race_lead_line_new_leader(self, state: SessionState, mock_mqtt: Mock):
        """Tests that a new leader is correctly identified and an MQTT is queued"""
        # Setup
        state.session_type = 'race'
        state.set_session_lead(driver='LEC', driver_number='16', team='Ferrari')

        # Execute
        process_race_lead_line(TOP_THREE_LINE_VER_LEAD, state, mock_mqtt)

        # Asserts
        ## First state check
        assert state.current_session_lead.driver_number == "1", "Should be 1 for Verstappen"
        assert state.current_session_lead.driver == "VER", "Should be VER for Verstappen"
        assert state.current_session_lead.team == "Red Bull", "Should be Red Bull"

        ## Then check MQTT
        mock_mqtt.queue_message.assert_called_once()
        expected_payload = json.dumps({"driver" : "VER", "driver_number" : "1", "team" : "Red Bull", "team_color" : "4781D7"})
        mock_mqtt.queue_message.assert_called_with(MqttTopics.LEADER_TOPIC, expected_payload)


    def test_process_race_lead_line_same_leader(self, mock_mqtt: Mock, state: SessionState):
        """
        Test that no action is taken if the leader has not changed.
        """
        state.set_session_lead(driver="VER", driver_number="1", team="Red Bull")

        process_race_lead_line(TOP_THREE_LINE_VER_LEAD, state, mock_mqtt)

        # State should be unchanged from the pre-configured state
        assert state.current_session_lead.driver_number == "1", "Should be 1 for Verstappen"
        assert state.current_session_lead.driver == "VER", "Should be VER for Verstappen"
        assert state.current_session_lead.team == "Red Bull", "Should be Red Bull"
        mock_mqtt.queue_message.assert_not_called()


    def test_process_race_lead_line_irrelevant_category(self, mock_mqtt: Mock, state: SessionState):
        """
        Test that lines with categories other than 'TopThree' are ignored.
        """
        line = "['TimingData', {'Lines': {'23': {'Sectors': {'0': {'Segments': {'7': {'Status': 2051}}}}}}}, '2025-09-20T12:00:44.123Z']"
        state_before = dataclasses.replace(state)

        process_race_lead_line(line, state_before, mock_mqtt)

        assert state_before == state
        mock_mqtt.queue_message.assert_not_called()


    def test_process_race_lead_line_no_p1_data(self, mock_mqtt, state):
        """
        Test that the function handles 'TopThree' data that is missing the P1 ('0') key.
        """
        line = "['TopThree', {'Lines': {'1': {'RacingNumber': '6', 'Tla': 'HAD', 'BroadcastName': 'I HADJAR', 'FullName': 'Isack HADJAR', 'FirstName': 'Isack', 'LastName': 'Hadjar', 'Reference': 'ISAHAD01', 'Team': 'Racing Bulls', 'TeamColour': '6C98FF', 'LapState': 33}}}, '2025-09-20T12:00:46.302Z']"
        state_before = dataclasses.replace(state)

        process_race_lead_line(line, state_before, mock_mqtt)

        assert state_before == state
        mock_mqtt.queue_message.assert_not_called()


