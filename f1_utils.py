from datetime import timedelta, datetime
import json
import ast
import time

from mqtt_topics import MqttTopics

try:
    import pandas as pd
except ImportError:
    raise


def get_team_by_driver(driver_number_string: str) -> str:
    """Returns the team name based on driver number"""
    teams = {
        '1': "Red Bull", '22': "Red Bull",
        '16': "Ferrari", '44': "Ferrari",
        '12': "Mercedes", '63': "Mercedes",
        '4': "McLaren", '81': "McLaren",
        '14': "Aston Martin", '18': "Aston Martin",
        '10': "Alpine", '43': "Alpine",
        '6': "RB", '30': "RB",
        '31': "Haas", '87': "Haas",
        '5': "Sauber", '27': "Sauber",
        '55': "Williams", '23': "Williams"
    }
    
    return teams.get(driver_number_string, "Unknown")

def rebroadcast_leader(state: dict[str, any], mqtt_handler):
    """Resends the lead, usefull after flag or Safety Car events"""
    payload = json.dumps({"driver": state["current_session_lead"]["Driver"], "team": state["current_session_lead"]["Team"]})
    mqtt_handler.queue_message(MqttTopics.LEADER_TOPIC, payload)

def parse_lap_time(time_str: str) -> timedelta | None:
    """Converts a time string to a timedelta object"""
    if not (isinstance(time_str, str) or ':' not in time_str):
        return None
    return pd.to_timedelta(f"00:{time_str}")

def process_lap_time_line(line: str, state: dict[str, any], mqtt_handler) -> None:
    category, payload, _ = ast.literal_eval(line)

    if category == 'TimingData' and 'Lines' in payload:
        for num, data in payload['Lines'].items():
            if 'Abbreviation' in data: state['driver_abbreviations'][num] = data['Abbreviation']
            if 'LastLapTime' in data and isinstance(data['LastLapTime'], dict):
                lap_time_str = data['LastLapTime'].get('Value')
                if lap_time_str and (lap_time := parse_lap_time(lap_time_str)) and lap_time < state['fastest_lap_info']['Time']:
                    driver_name = state['driver_abbreviations'].get(num, num)
                    team_name = get_team_by_driver(num)
                    state['fastest_lap_info'].update(Time=lap_time, Driver=driver_name, Team=team_name)
                    state['current_session_lead'].update(Driver=driver_name, Team=team_name)
                    payload = json.dumps({"driver": driver_name, "team": team_name, "lap_time": lap_time_str})
                    mqtt_handler.queue_message(MqttTopics.LEADER_TOPIC, payload)

def process_race_lead_line(line: str, state: dict[str, any], mqtt_handler) -> None:
    category, payload, _ = ast.literal_eval(line)
    if category == 'TopThree' and 'Lines' in payload and '0' in payload['Lines']:
        p1_data = payload['Lines']['0']
        new_leader_num = p1_data.get('RacingNumber')
        if new_leader_num and new_leader_num != state.get('current_leader_num'):
            state['current_leader_num'] = new_leader_num
            team_name = get_team_by_driver(new_leader_num)
            state['current_session_lead'].update(Driver=p1_data.get('Tla', new_leader_num), Team=team_name)
            payload = json.dumps({"driver": p1_data.get('Tla', new_leader_num), "team": team_name})
            mqtt_handler.queue_message(MqttTopics.LEADER_TOPIC, payload)

def process_race_control_line(line: str, state: dict[str, any], mqtt_handler) -> None:
    """Evaluates Race Control Lines, these include Flags and Safety Cars"""
    category, payload, _ = ast.literal_eval(line)

    
    if category == 'RaceControlMessages' and 'Messages' in payload:
        for msg_data in payload.get('Messages', {}).values():
            if not isinstance(msg_data, dict): continue

            ## --- FLAGS ---
            if 'Flag' in msg_data and msg_data['Message']:
                # state['last_flag_message'] = msg_data['Message']
                # Ignoring green flag for Pit Exit Open
                if msg_data['Flag'] == 'GREEN' and 'PIT EXIT OPEN' in msg_data['Message']:
                    continue
                
                flag = msg_data['Flag']
                payload = json.dumps({"flag": msg_data['Flag'], "message": msg_data['Message']})
                # mqtt_handler.queue_message(MqttTopics.FLAG_TOPIC, payload)
                # 🚩 RED FLAGS 🚩
                if flag == "RED" and state['race_state'] != "RED":
                    state['race_state'] = "RED"
                    state['yellow_flags'].clear()
                    mqtt_handler.queue_message(MqttTopics.FLAG_TOPIC, payload)
                # 🟡 YELLOW FLAGS 🟡
                elif (flag == "YELLOW" or flag == "DOUBLE YELLOW") and (state['race_state'] != "RED" and state['race_state'] != "SAFETY CAR"):
                    sector = msg_data.get('Sector')
                    state['yellow_flags'].add(sector)
                    if state['race_state'] != "YELLOW":
                        state['race_state'] = "YELLOW"
                        mqtt_handler.queue_message(MqttTopics.FLAG_TOPIC, payload)
                # 👍 CLEAR Flags 👍
                elif flag == "CLEAR":
                    if state['race_state'] == "YELLOW":
                        sector = msg_data.get('Sector')
                        state['yellow_flags'].discard(sector)
                        if len(state['yellow_flags']) == 0:
                            state['race_state'] = "GREEN"
                            rebroadcast_leader(state, mqtt_handler)
                # 🏁 CHEQUERED flag, important for quali
                elif flag == 'CHEQUERED' and state['session_type'] == 'qualifying' and not state['cooldown_active']:
                    state['cooldown_active'] = True
                    state['session_end_time'] = time.monotonic()
            ## --- SAFETY CAR ---
            elif msg_data['Category'] == 'SafetyCar':
                if msg_data['Status'] == 'DEPLOYED' and state['race_state'] != "SAFETY CAR":
                    state['race_state'] = "SAFETY CAR"
                    state['yellow_flags'].clear()
                    payload = json.dumps({"flag": "SAFETY CAR", "message": msg_data['Mode']})
                    mqtt_handler.queue_message(MqttTopics.FLAG_TOPIC, payload)
                elif msg_data['Status'] == 'ENDING' or msg_data['Status'] == 'IN THIS LAP':
                    state['race_state'] = "GREEN"
                    payload = json.dumps({"flag": "CLEAR", "message" : "SAFETY CAR ENDING"})
                    mqtt_handler.queue_message(MqttTopics.FLAG_TOPIC, payload)
                    rebroadcast_leader(state, mqtt_handler)

def process_session_start_line(line: str, state: dict[str, any]) -> None:
    """Detects the official start of a session and records the timestamp."""
    # Don't bother parsing if we've already found the start, could be repeats in Quali
    if state.get("true_session_start_time"):
        return
    
    try:
        category, payload, _ = ast.literal_eval(line)
    except (ValueError, SyntaxError):
        return
    
    session_type = state["session_type"]
    start_detected = False

    # Logic for FP and Quali (Pit Exit Open)
    if session_type in ('practice', 'qualifying'):
        if category == 'RaceControlMessages':
            for msg in payload.get('Messages', []):
                if isinstance(msg, dict) and msg.get('Message') == 'GREEN LIGHT - PIT EXIT OPEN':
                    start_detected = True
                    break
    # Logic for races <- This needs calibration as I am sceptic to Gemini's implementation
    elif session_type == 'race':
        if category == 'SessionData':
            for series_data in payload.get('StatusSeries', {}).values():
                if isinstance(series_data, dict) and series_data.get('SessionStatus') == 'Started':
                    start_detected = True
                    break

    if start_detected:
        state["true_session_start_time"] = time.monotonic()
        # Sets a 5 min cutoff timer for "bothering" to deal with MQTT incomming messags for "session start"
        state["calibration_window_end_time"] = time.monotonic() + 300


def reset_for_next_session(state):
    """Resets the state for the next qualifying segment."""

    next_segment = "Q2" if state['quali_session'] == "Q1" else "Q3"

    # Reset fastest lap info
    state['quali_session'] = next_segment
    state['fastest_lap_info'] = {"Driver": None, "Time": timedelta(minutes=3)} # Thinking that 3 minues will stop the random sudden fastest laps at the beginning of the session
    state['cooldown_active'] = False
    state['session_end_time'] = None

                


