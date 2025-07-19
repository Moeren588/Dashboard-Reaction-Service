from datetime import timedelta, datetime
import json
try:
    import pandas as pd
except ImportError:
    raise

LEADER_TOPIC = "f1/race/leader"
FLAG_TOPIC = "f1/race/flag_status"

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

def parse_lap_time(time_str: str) -> timedelta | None:
    """Converts a time string to a timedelta object"""
    if not (isinstance(time_str, str) or ':' not in time_str):
        return None
    return pd.to_timedelta(f"00:{time_str}")

def process_lap_time_line(line: str, state: dict[str, any], mqtt_handler) -> None:
    category, payload, _ = eval(line)

    if category == 'TimingData' and 'Lines' in payload:
        for num, data in payload['Lines'].items():
            if 'Abbreviation' in data: state['driver_abbreviations'][num] = data['Abbreviation']
            if 'LastLapTime' in data and isinstance(data['LastLapTime'], dict):
                lap_time_str = data['LastLapTime'].get('Value')
                if lap_time_str and (lap_time := parse_lap_time(lap_time_str)) and lap_time < state['fastest_lap_info']['Time']:
                    driver_name = state['driver_abbreviations'].get(num, num)
                    team_name = get_team_by_driver(num)
                    state['fastest_lap_info'].update(Time=lap_time, Driver=driver_name, Team=team_name)
                    payload = json.dumps({"driver": driver_name, "team": team_name, "lap_time": lap_time_str})
                    mqtt_handler.queue_message(LEADER_TOPIC, payload)

def process_race_lead_line(line: str, state: dict[str, any], mqtt_handler) -> None:
    category, payload, _ = eval(line)
    if category == 'TopThree' and 'Lines' in payload and '0' in payload['Lines']:
        p1_data = payload['Lines']['0']
        new_leader_num = p1_data.get('RacingNumber')
        if new_leader_num and new_leader_num != state.get('current_leader_num'):
            state['current_leader_num'] = new_leader_num
            team_name = get_team_by_driver(new_leader_num)
            state['lead_driver'].update(Driver=p1_data.get('Tla', new_leader_num), Team=team_name)
            payload = json.dumps({"driver": p1_data.get('Tla', new_leader_num), "team": team_name})
            mqtt_handler.queue_message(LEADER_TOPIC, payload)

def process_race_control_line(line: str, state: dict[str, any], mqtt_handler) -> None:
    category, payload, _ = eval(line)
    
    if category == 'RaceControlMessages' and 'Messages' in payload:
        for msg_id, msg_data in payload['Messages'].items():
            ## --- FLAGS ---
            if 'Flag' in msg_data and msg_data['Message'] != state.get('last_flag_message'):
                state['last_flag_message'] = msg_data['Message']
                payload = json.dumps({"flag": msg_data['Flag'], "message": msg_data['Message']})
                mqtt_handler.queue_message(FLAG_TOPIC, payload)
                # CHEQUERED flag, important for quali
                if msg_data['Flag'] == 'CHEQUERED' and state['session_type'] == 'qualifying' and not state['cooldown_active']:
                    state['cooldown_active'] = True
                    state['session_end_time'] = datetime.now()
            ## --- SAFETY CAR ---
            elif msg_data['Category'] == 'SafetyCar':
                if msg_data['Status'] == 'DEPLOYED' and not state['safety_car']:
                    state['safety_car'] = True
                    payload = json.dumps({"flag": "SAFETY CAR", "message": msg_data['Mode']})
                    mqtt_handler.queue_message(FLAG_TOPIC, payload)
                elif msg_data['Status'] == 'ENDING' or msg_data['Status'] == 'IN THIS LAP':
                    state['safety_car'] = False
                    payload = json.dumps({"flag": "CLEAR", "message" : "SAFETY CAR ENDING"})
                    mqtt_handler.queue_message(FLAG_TOPIC, payload)

def reset_for_next_session(state):
    """Resets the state for the next qualifying segment."""

    next_segment = "Q2" if state['current_segment'] == "Q1" else "Q3"

    # Reset fastest lap info
    state['current_segment'] = next_segment
    state['fastest_lap_info'] = {"Driver": None, "Time": timedelta(days=1)}
    state['cooldown_active'] = False
    state['session_end_time'] = None

                


