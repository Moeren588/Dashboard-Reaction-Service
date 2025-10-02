from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, Set, Optional, Any

@dataclass
class FastestLapInfo:
    """Stores information about the current fastest lap holder"""
    time: timedelta = timedelta(days=1)
    driver: Optional[str] = None
    team: Optional[str] = None

@dataclass
class SessionLeaderInfo:
    """Stores information about the current session lead"""
    driver: Optional[str] = None
    driver_number: Optional[str] = None
    team: Optional[str] = None

@dataclass
class SessionState:
    """Holds all the dynamic and static data for a session"""
    
    session_type: str       # Stores the current session type: free practice, qualifying or race

    teams_data: Dict[str, Dict[str, str]]       # Stores the team info fetched from data/drs_data.json
    drivers_data: Dict[str, Dict[str, str]]     # Stores the driver info fetched from data/drs_data.json

    race_state: str = "GREEN"       # String representing the current race state (GREEN, YELLOW, SAFETY CAR etc.)
    fastest_lap_info: FastestLapInfo = field(default_factory=FastestLapInfo)            # Holds the info about the current fastest lap set, determines the leader for practice and qualifying
    current_session_lead: SessionLeaderInfo = field(default_factory=SessionLeaderInfo)  # Holds the info about the current session lead
    yellow_flags: Set[int] = field(default_factory=set)     # Stores all the yellow flag sectors

    quali_session: str = "Q1"                   # What Qualifying session are we in? Q1, Q2 or Q3
    session_end_time: Optional[float] = None    # When the chequered flag is seen during the qualifying session
    cooldown_active: bool = False               # If we are inbetween two quali sessions, stops broadcasting a lot of the events as they are irrelevant for the session (e.g. random yellow flags)


    # Calibration
    true_session_start_time: Optional[float] = None         # When the session start time is detected by the service

    def set_race_state(self, state: str):
        """Sets the race state"""
        self.race_state = state

    def set_cooldown_active(self, state: bool):
        """Sets the cooldown state"""
        self.cooldown_active = state

    def set_session_end_time(self, end_time: float):
        """Sets the session end time"""
        self.session_end_time = end_time

    def add_sector_to_yellow_flags(self, sector: str):
        """Adds a sector to the yellow flags"""
        self.yellow_flags.add(sector)

    def remove_sector_from_yellow_flags(self, sector: str):
        """Removes a sector from the yellow flags"""
        self.yellow_flags.discard(sector)

    def clear_yellow_flags(self):
        """Clears all yellow flags"""
        self.yellow_flags.clear()

    def set_session_lead(self, driver: str, driver_number: str, team: str):
        """Updates the current session lead"""
        self.current_session_lead.driver = driver
        self.current_session_lead.driver_number = driver_number
        self.current_session_lead.team = team

    def set_fastest_lap(self, lap_time: timedelta, driver: str, team: str):
        """Updates the fastest lap information"""
        self.fastest_lap_info.time = lap_time
        self.fastest_lap_info.driver = driver
        self.fastest_lap_info.team = team

    def reset_for_next_quali_segment(self):
        """Resets the state for the next qualifying segment."""
        next_segment = "Q2" if self.quali_session == "Q1" else "Q3"

        self.quali_session = next_segment
        self.fastest_lap_info.time = timedelta(minutes=5)
        self.fastest_lap_info.driver = None
        self.fastest_lap_info.team = None
        self.cooldown_active = False
        self.session_end_time = None

    def set_true_session_start_time(self, start_time: float):
        """Sets the true session start time"""
        self.true_session_start_time = start_time