from datetime import timedelta, datetime
import json
import ast
import time
import logging

from .mqtt_handler import MQTTHandler
from .mqtt_topics import MqttTopics
from .session_state import SessionState

def rebroadcast_leader(state: SessionState, mqtt_handler: MQTTHandler) -> None:
    """Resends the lead, usefull after flag or Safety Car events"""
    if not state.current_session_lead.team: return #Early return if no leader has been set
    payload = json.dumps({"driver": state.current_session_lead.driver, "team": state.current_session_lead.team})
    mqtt_handler.queue_message(MqttTopics.LEADER_TOPIC, payload)

def return_to_green(state: SessionState, mqtt_handler: MQTTHandler, payload_message: str) -> None:
    """Returns the session to GREEN flag status"""
    logging.info(f'Returning to GREEN flag status from {state.race_state}')
    state.set_race_state("GREEN")
    payload = json.dumps({"flag": "GREEN", "message": payload_message})
    mqtt_handler.queue_message(MqttTopics.FLAG_TOPIC, payload)
    rebroadcast_leader(state, mqtt_handler)

def parse_lap_time(time_str: str) -> timedelta | None:
    """Converts a time string to a timedelta object"""
    if not (isinstance(time_str, str) or ':' not in time_str):
        return None
    try:
        datetime_object = datetime.strptime(time_str, '%M:%S.%f')
        return timedelta(
            minutes = datetime_object.minute,
            seconds = datetime_object.second,
            microseconds = datetime_object.microsecond
        )
    except ValueError:
        return None

def process_lap_time_line(line: str, state: SessionState, mqtt_handler: MQTTHandler) -> None:
    category, payload, _ = ast.literal_eval(line)

    if category == 'TimingData' and 'Lines' in payload:
        for num, data in payload['Lines'].items():
            if 'LastLapTime' in data and isinstance(data['LastLapTime'], dict):
                lap_time_str = data['LastLapTime'].get('Value')
                if lap_time_str and (lap_time := parse_lap_time(lap_time_str)) and lap_time < state.fastest_lap_info.time:
                    try:
                        driver_info = state.drivers_data[num]
                        driver_abbreviation = driver_info['abbreviation']
                        team_key = driver_info['team_key']
                        team_name = state.teams_data[team_key]['name']
                    except KeyError:
                        logging.warning(f"Could not find driver or team for {num}, setting unknown")
                        driver_abbreviation = "UNK"
                        team_name = "UNKNOWN"
                    state.set_fastest_lap(lap_time, driver_abbreviation, team_name)
                    state.set_session_lead(driver=driver_abbreviation, driver_number=num, team=team_name)
                    payload = json.dumps({"driver": driver_abbreviation, "driver_number": num, "team": team_name})
                    mqtt_handler.queue_message(MqttTopics.LEADER_TOPIC, payload)

def process_race_lead_line(line: str, state: SessionState, mqtt_handler: MQTTHandler) -> None:
    category, payload, _ = ast.literal_eval(line)
    if category == 'TopThree' and 'Lines' in payload and '0' in payload['Lines']:
        p1_data = payload['Lines']['0']
        new_leader_num = p1_data.get('RacingNumber')
        if new_leader_num and new_leader_num != state.current_session_lead.driver_number:
            # state['current_leader_num'] = new_leader_num
            try:
                driver_info = state.drivers_data[new_leader_num]
                driver_abbreviation = driver_info['abbreviation']
                team_key = driver_info['team_key']

                team_name = state.teams_data[team_key]['name']
            except KeyError:
                logging.warning(f"Could not find driver or team for {new_leader_num}")
                driver_abbreviation = "UNK"
                team_name = "UNKNOWN"
            state.set_session_lead(driver=driver_abbreviation, driver_number=new_leader_num, team=team_name)
            payload = json.dumps({"driver": driver_abbreviation, "driver_number": new_leader_num, "team": team_name})
            mqtt_handler.queue_message(MqttTopics.LEADER_TOPIC, payload)

def process_race_control_line(line: str, state: SessionState, mqtt_handler: MQTTHandler) -> None:
    """Evaluates Race Control Lines, these include Flags and Safety Cars"""
    category, payload, _ = ast.literal_eval(line)

    if category == 'RaceControlMessages' and 'Messages' in payload:
        for msg_data in payload.get('Messages', {}).values():
            if not isinstance(msg_data, dict): continue

            ## --- FLAGS ---
            if 'Flag' in msg_data and msg_data['Message']:
                # Ignoring green flag for Pit Exit Open
                if msg_data['Flag'] == 'GREEN' and 'PIT EXIT OPEN' in msg_data['Message']:
                    continue
                
                flag = msg_data['Flag']
                payload = json.dumps({"flag": msg_data['Flag'], "message": msg_data['Message']})
                # mqtt_handler.queue_message(MqttTopics.FLAG_TOPIC, payload)
                # 🚩 RED FLAGS 🚩
                if flag == "RED" and state.race_state != "RED":
                    state.set_race_state("RED")
                    state.clear_yellow_flags()
                    mqtt_handler.queue_message(MqttTopics.FLAG_TOPIC, payload)
                # 🟡 YELLOW FLAGS 🟡
                elif (flag == "YELLOW" or flag == "DOUBLE YELLOW") and (state.race_state != "RED" and state.race_state != "SAFETY CAR"):
                    sector = msg_data.get('Sector')
                    state.add_sector_to_yellow_flags(sector)
                    if state.race_state != "YELLOW":
                        state.set_race_state("YELLOW")
                        mqtt_handler.queue_message(MqttTopics.FLAG_TOPIC, payload)
                # 👍 CLEAR Flags 👍
                elif flag == "CLEAR":
                    if state.race_state == "YELLOW":
                        sector = msg_data.get('Sector')
                        state.remove_sector_from_yellow_flags(sector)
                        if len(state.yellow_flags) == 0:
                            return_to_green(state, mqtt_handler, "GREEN FLAG, ALL YELLOW CLEARED")
                # 🏁 CHEQUERED flag, important for quali
                elif flag == 'CHEQUERED' and state.session_type == 'qualifying' and not state.cooldown_active:
                    logging.info(f'CHEQUERED Flag for {state.quali_session}')
                    state.set_cooldown_active(True)
                    state.set_session_end_time(time.monotonic())
            ## --- SAFETY CAR ---
            elif msg_data['Category'] == 'SafetyCar':
                if msg_data['Status'] == 'DEPLOYED' and state.race_state != "SAFETY CAR":
                    state.set_race_state("SAFETY CAR")
                    state.clear_yellow_flags()
                    payload = json.dumps({"flag": "SAFETY CAR", "message": msg_data['Mode']})
                    mqtt_handler.queue_message(MqttTopics.FLAG_TOPIC, payload)
                elif msg_data['Status'] == 'ENDING' or msg_data['Status'] == 'IN THIS LAP':
                    return_to_green(state, mqtt_handler, "SAFETY CAR ENDING")

def process_session_data_line(line:str, state: SessionState, mqtt_handler: MQTTHandler) -> None:
    """Processing the Session Data Lines, like session start and red flag restarts"""
    try:
        category, payload, _ = ast.literal_eval(line)
    except (ValueError, SyntaxError):
        return

    if category == 'SessionData':
        for series_data in payload.get('StatusSeries', {}).values():
            if isinstance(series_data, dict) and series_data.get('SessionStatus') == 'Started':
                if not state.true_session_start_time:
                    logging.info(f'Start detected from livefeed at {datetime.now()}')
                    state.set_true_session_start_time(time.monotonic())
                    break
                elif state.race_state == 'RED':
                    return_to_green(state, mqtt_handler, "GREEN FLAG, RED flag cleared")
                    break
