import dataclasses
import pytest
from freezegun import freeze_time
from unittest.mock import Mock, MagicMock
import json
from datetime import timedelta
import time

from src.drs.session_state import SessionState

# --- Fixtures ---

MOCK_DRS_DATA = {
    "drivers": {
        "3" : {'abbreviation' : 'VER', 'team_key' : 'red_bull'},
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

# --- Tests ---
def test_set_race_state(state: SessionState):
    """Tests setting the race state"""
    state.set_race_state('YELLOW')
    assert state.race_state == 'YELLOW'

def test_set_cooldown_active(state: SessionState):
    """Tests setting the cooldown active"""
    state.set_cooldown_active(True)
    assert state.cooldown_active == True

def test_set_session_end_time(state: SessionState):
    """Tests setting the session end time"""
    end_time = time.monotonic()
    state.set_session_end_time(end_time)
    assert state.session_end_time == end_time

def test_add_yellow_flag(state: SessionState):
    """Tests adding a yellow flag"""
    state.add_sector_to_yellow_flags(2)
    assert state.yellow_flags == {2}

def test_add_yellow_flag_already_exists(state: SessionState):
    """Tests adding a yellow flag that already exists"""
    state.yellow_flags = {2}
    state.add_sector_to_yellow_flags(2)
    assert state.yellow_flags == {2}

def test_remove_yellow_flags(state: SessionState):
    """Tests removing yellow flags"""
    state.yellow_flags = {2, 3, 4}
    state.remove_sector_from_yellow_flags(2)
    assert state.yellow_flags == {3, 4}

def test_remove_yellow_flag_not_in_set(state: SessionState):
    """Tests removing a yellow flag that doesn't exist"""
    state.yellow_flags = {2, 3, 4}
    state.remove_sector_from_yellow_flags(8)
    assert state.yellow_flags == {2, 3, 4}

def test_clear_yellow_flags(state: SessionState):
    """Tests clearing yellow flags"""
    state.yellow_flags = {2, 3, 4}
    state.clear_yellow_flags()
    assert state.yellow_flags == set()

def test_clear_yellow_flags_empty_set(state: SessionState):
    """Tests clearing yellow flags when the set is empty"""
    state.clear_yellow_flags()
    assert state.yellow_flags == set()

def test_set_session_lead(state: SessionState):
    """Tests setting the session lead"""
    state.set_session_lead(driver='VER', driver_number='3', team='Red Bull')
    assert state.current_session_lead.driver == 'VER'
    assert state.current_session_lead.driver_number == '3'
    assert state.current_session_lead.team == 'Red Bull'

def test_set_fasest_lap(state: SessionState):
    """Tests setting the fastest lap"""
    state.set_fastest_lap(lap_time=timedelta(minutes=1, seconds=28, microseconds=552000), driver='VER', team='Red Bull')
    assert state.fastest_lap_info.time == timedelta(minutes=1, seconds=28, microseconds=552000)
    assert state.fastest_lap_info.driver == 'VER'
    assert state.fastest_lap_info.team == 'Red Bull'

def test_reset_for_Q2_quali_segment(state: SessionState):
    """Tests resetting for the next Q2 segment"""
    state.session_type = 'qualifying'
    state.quali_session = 'Q1'
    state.cooldown_active = True
    state.session_end_time = time.monotonic()
    state.fastest_lap_info.time = timedelta(minutes=1, seconds=28, microseconds=552000)
    state.fastest_lap_info.driver = 'VER'
    state.fastest_lap_info.team = 'Red Bull'

    state.reset_for_next_quali_segment()

    assert state.quali_session == 'Q2'
    assert state.fastest_lap_info.time == timedelta(minutes=5)
    assert state.fastest_lap_info.driver is None
    assert state.fastest_lap_info.team is None
    assert state.cooldown_active is False
    assert state.session_end_time is None

def test_reset_for_Q3_quali_segment(state: SessionState):
    """Tests resetting for the next Q3 segment"""
    state.session_type = 'qualifying'
    state.quali_session = 'Q2'
    state.cooldown_active = True
    state.session_end_time = time.monotonic()
    state.fastest_lap_info.time = timedelta(minutes=1, seconds=28, microseconds=552000)
    state.fastest_lap_info.driver = 'VER'
    state.fastest_lap_info.team = 'Red Bull'

    state.reset_for_next_quali_segment()

    assert state.quali_session == 'Q3'
    assert state.fastest_lap_info.time == timedelta(minutes=5)
    assert state.fastest_lap_info.driver is None
    assert state.fastest_lap_info.team is None
    assert state.cooldown_active is False
    assert state.session_end_time is None

def test_set_true_session_start_time(state: SessionState):
    """Tests setting the true session start time"""
    start_time = time.monotonic()
    state.set_true_session_start_time(start_time)
    assert state.true_session_start_time == start_time




    



