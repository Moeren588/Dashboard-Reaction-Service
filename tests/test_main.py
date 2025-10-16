import dataclasses
import pytest
from freezegun import freeze_time
from unittest.mock import Mock, MagicMock
import json
from datetime import timedelta
import time

from main import apply_forced_lead
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

def test_force_team_lead_valid(state:SessionState, mock_mqtt: Mock):

    apply_forced_lead(state, mock_mqtt, 'alpine')
    assert state.current_session_lead.driver == 'FORCE'
    assert state.current_session_lead.driver_number == '0'
    assert state.current_session_lead.team == 'Alpine'

    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"driver": "FORCE", "driver_number" : "0", "team": "Alpine", "team_color": "00A1E8"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.LEADER_TOPIC, expected_payload, immediate=True)

def test_force_team_lead_valid_random_capitalized(state:SessionState, mock_mqtt: Mock):

    apply_forced_lead(state, mock_mqtt, 'aLpINe')
    assert state.current_session_lead.driver == 'FORCE'
    assert state.current_session_lead.driver_number == '0'
    assert state.current_session_lead.team == 'Alpine'

    mock_mqtt.queue_message.assert_called_once()
    expected_payload = json.dumps({"driver": "FORCE", "driver_number" : "0", "team": "Alpine", "team_color": "00A1E8"})
    mock_mqtt.queue_message.assert_called_with(MqttTopics.LEADER_TOPIC, expected_payload, immediate=True)

def test_force_team_lead_invalid(state:SessionState, mock_mqtt: Mock):
    
    apply_forced_lead(state, mock_mqtt, 'frarari')
    assert state.current_session_lead.driver == None
    assert state.current_session_lead.driver_number == None
    assert state.current_session_lead.team == None

    mock_mqtt.queue_message.assert_not_called()

def test_force_team_lead_empty(state:SessionState, mock_mqtt: Mock):
    
    apply_forced_lead(state, mock_mqtt, '')
    assert state.current_session_lead.driver == None
    assert state.current_session_lead.driver_number == None
    assert state.current_session_lead.team == None

    mock_mqtt.queue_message.assert_not_called()