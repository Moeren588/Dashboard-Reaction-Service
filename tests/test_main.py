import dataclasses
import pytest
from freezegun import freeze_time
from unittest.mock import Mock, MagicMock
import json
from datetime import timedelta
import time

from main import apply_forced_lead, setup, SESSION_MAP
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

## FORCE TEAM LEAD
def test_force_team_lead_valid(state:SessionState, mock_mqtt: Mock):
    """Test that Force Team Lead is set correctly"""
    apply_forced_lead(state, mock_mqtt, 'alpine')
    assert state.current_session_lead.driver == 'FORCE'
    assert state.current_session_lead.driver_number == '0'
    assert state.current_session_lead.team == 'Alpine'

    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"driver": "FORCE", "driver_number" : "0", "team": "Alpine", "team_color": "00A1E8"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.LEADER_TOPIC, expected_payload, immediate=True)

def test_force_team_lead_valid_random_capitalized(state:SessionState, mock_mqtt: Mock):
    """Test that Force Team Lead is set correctly even with random capitalization"""
    apply_forced_lead(state, mock_mqtt, 'aLpINe')
    assert state.current_session_lead.driver == 'FORCE'
    assert state.current_session_lead.driver_number == '0'
    assert state.current_session_lead.team == 'Alpine'

    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"driver": "FORCE", "driver_number" : "0", "team": "Alpine", "team_color": "00A1E8"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.LEADER_TOPIC, expected_payload, immediate=True)

def test_force_team_lead_valid_with_spaced_name(state: SessionState, mock_mqtt: Mock):
    """Tests that Force Team Lead is set correctly even if the team name is used with space"""
    apply_forced_lead(state, mock_mqtt, '  Red Bull ')
    assert state.current_session_lead.driver == 'FORCE'
    assert state.current_session_lead.driver_number == '0'
    assert state.current_session_lead.team == 'Red Bull'

    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"driver": "FORCE", "driver_number" : "0", "team": "Red Bull", "team_color": "4781D7"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.LEADER_TOPIC, expected_payload, immediate=True)

def test_force_team_lead_invalid(state:SessionState, mock_mqtt: Mock):
    """Test that Force Team Lead is not set with unknown team input"""
    apply_forced_lead(state, mock_mqtt, 'frarari')
    assert state.current_session_lead.driver == None
    assert state.current_session_lead.driver_number == None
    assert state.current_session_lead.team == None

    mock_mqtt.queue_message.assert_not_called()

def test_force_team_lead_empty(state:SessionState, mock_mqtt: Mock):
    """Test that Force Team Lead is not set with empty input"""
    apply_forced_lead(state, mock_mqtt, '')
    assert state.current_session_lead.driver == None
    assert state.current_session_lead.driver_number == None
    assert state.current_session_lead.team == None

    mock_mqtt.queue_message.assert_not_called()

## SETUP
test_session_cases = list(SESSION_MAP.items())
@pytest.mark.parametrize("session_input, expected_session", test_session_cases)
def test_setup_valid_session_types(mocker, session_input, expected_session):
    """Tests that state is set to race from args"""
    mocker.patch('main.MQTTHandler')
    mocker.patch('main.load_drs_data', return_value={"teams": {}, "drivers": {}})

    state, _, _ = setup(session_input)

    assert state.session_type == expected_session
    
def test_setup_valid_session_random_capitalization(mocker):
    """Tests that setup will run correctly and state is set correctly with random capitalization"""
    mocker.patch('main.MQTTHandler')
    mocker.patch('main.load_drs_data', return_value={"teams": {}, "drivers": {}})

    state, _, _ = setup("SprINT rAcE")
    assert state.session_type == "race"
    
def test_setup_invalid_session_types(mocker):
    """Tests that setup fails on invalid session type"""
    mocker.patch('main.MQTTHandler')
    mocker.patch('main.load_drs_data', return_value={"teams": {}, "drivers": {}})

    with pytest.raises(SystemExit):
        setup("indy_car_session")

