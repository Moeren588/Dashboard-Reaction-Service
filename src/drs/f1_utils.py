from datetime import timedelta, datetime
import json
import ast
import time
import logging

from .mqtt_handler import MQTTHandler
from .mqtt_topics import MqttTopics
from .session_state import SessionState

def rebroadcast_leader(state: SessionState, mqtt_handler: MQTTHandler) -> None:
    """Resends the current leader's info to MQTT.

    Useful after a flag or Safety Car event. This function was created 
    because Home Assistant had difficulty relying *only* on the 'GREEN' 
    flag event to correctly revert lights to the race leader's colors.

    The function will return early if no `current_session_lead.team` is 
    set in the state. This can happen if an event (e.g., double yellow)
    occurs before any fastest lap is set in Practice or Qualifying.

    Args:
        state: The current SessionState, used to read leader info.
        mqtt_handler: The MQTTHandler instance to queue the message.
    """
    if not state.current_session_lead.team: return #Early return if no leader has been set
    payload = json.dumps({"driver": state.current_session_lead.driver, "driver_number": state.current_session_lead.driver_number, "team": state.current_session_lead.team})
    mqtt_handler.queue_message(MqttTopics.LEADER_TOPIC, payload)

def return_to_green(state: SessionState, mqtt_handler: MQTTHandler, payload_message: str) -> None:
    """Sets the session to a GREEN flag status and notifies MQTT.

    This function performs several actions:
    1. Sets the `race_state` in the SessionState to "GREEN".
    2. Clears all active yellow flag sectors.
    3. Publishes the new GREEN flag status to the `FLAG_TOPIC`.
    4. Calls `rebroadcast_leader` to resend the current leader's info.

    Args:
        state: The current SessionState object to be modified.
        mqtt_handler: The MQTTHandler instance to queue messages.
        payload_message: The descriptive message (e.g., "ALL CLEAR") 
                         to send with the GREEN flag payload.
    """
    logging.info(f'Returning to GREEN flag status from {state.race_state}')
    state.set_race_state("GREEN")
    state.clear_yellow_flags()
    payload = json.dumps({"flag": "GREEN", "message": payload_message})
    mqtt_handler.queue_message(MqttTopics.FLAG_TOPIC, payload)
    rebroadcast_leader(state, mqtt_handler)

def parse_lap_time(time_str: str) -> timedelta | None:
    """Converts a "M:SS.fff" time string into a timedelta object.

    Args:
        time_str: The lap time string (e.g., "1:34.567").

    Returns:
        A timedelta object representing the lap time, or None if
        parsing fails (e.g., due to ValueError or invalid format).
    """
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
    """Processes a 'TimingData' line to find a new fastest lap.

    This function is used in Practice and Qualifying to determine the
    session leader based on the fastest lap time.

    The process is as follows:
    1. Checks if the line `category` is 'TimingData'.
    2. Parses the lap time string and compares it to the current 
       fastest lap in `state.fastest_lap_info`.
    3. If a new fastest lap is set:
       a. Extracts driver and team info using the driver number.
       b. Sets 'UNK' (UNKNOWN) if driver/team data is missing.
       c. Updates the `SessionState` with the new fastest lap and
          sets the new `current_session_lead`.
       d. Queues a message to the `LEADER_TOPIC` with the new leader's info.

    Args:
        line: The raw data line (as a string) from the cache file.
        state: The current SessionState object to be modified.
        mqtt_handler: The MQTTHandler instance to queue messages.
    """
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
                        team_color = state.teams_data[team_key]['color_hex']
                    except KeyError:
                        logging.warning(f"Could not find driver or team for {num}, setting unknown")
                        driver_abbreviation = "UNK"
                        team_name = "UNKNOWN"
                        team_color = None
                    state.set_fastest_lap(lap_time, driver_abbreviation, team_name)
                    state.set_session_lead(driver=driver_abbreviation, driver_number=num, team=team_name)
                    payload = json.dumps({"driver": driver_abbreviation, "driver_number": num, "team": team_name, "team_color": team_color})
                    mqtt_handler.queue_message(MqttTopics.LEADER_TOPIC, payload)

def process_race_lead_line(line: str, state: SessionState, mqtt_handler: MQTTHandler) -> None:
    """Processes a 'TopThree' line to find a new leader.

    This function is used in Race to determine the race lead.

    The process is as follows:
    1. Checks if the line `category` is 'TopThree' AND it involves
       the first place ('0').
    2. Extracts driver and team info using the driver number.
        a. Sets 'UNK' (UNKNOWN) if driver/team data is missing.
    3. Updates the `SessionState` with the new `current_session_lead`.
    4. Queues a message to the `LEADER_TOPIC` with the new leader's info.

    Args:
        line: The raw data line (as a string) from the cache file.
        state: The current SessionState object to be modified.
        mqtt_handler: The MQTTHandler instance to queue messages.
    """
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
                team_color = state.teams_data[team_key]['color_hex']
            except KeyError:
                logging.warning(f"Could not find driver or team for {new_leader_num}")
                driver_abbreviation = "UNK"
                team_name = "UNKNOWN"
                team_color = None
            state.set_session_lead(driver=driver_abbreviation, driver_number=new_leader_num, team=team_name)
            payload = json.dumps({"driver": driver_abbreviation, "driver_number": new_leader_num, "team": team_name, "team_color": team_color})

            mqtt_handler.queue_message(MqttTopics.LEADER_TOPIC, payload)

def process_race_control_line(line: str, state: SessionState, mqtt_handler: MQTTHandler) -> None:
    """Processes 'RaceControlMessage' lines for flags and safety cars.

    This function parses messages from the 'RaceControlMessages' category,
    which can be sent during any session type. It is responsible for
    updating the session state based on on-track events.

    The function first checks for a valid 'RaceControlMessages' payload.
    It then dispatches logic based on the message category, primarily
    handling Flag and Safety Car events.

    **Flag Events:**
    - **RED:** Sets the `race_state` to "RED", clears all yellow flags, 
      and broadcasts the new RED flag state.
    - **YELLOW:** Adds the specified sector to the `yellow_flags` set.
      If the state was not already 'YELLOW', it updates the `race_state` 
      and broadcasts the YELLOW flag.
    - **CLEAR:** Removes the specified sector from the `yellow_flags` set.
      If the `yellow_flags` set is now empty, it calls 
      `return_to_green()`.
    - **CHEQUERED:** In Qualifying sessions, this activates the 
      `cooldown_active` flag and records the `session_end_time` to
      manage the break between quali segments.

    **Safety Car Events:**
    - **DEPLOYED:** (Used for both VSC and full Safety Car)
      Sets the `race_state` to "SAFETY CAR", clears all yellow flags,
      and broadcasts the SAFETY CAR status.
    - **ENDING / IN THIS LAP:** (Used for VSC Ending or SC In)
      Calls `return_to_green()` to return the session to normal 
      racing conditions.

    Args:
        line: The raw data line (as a string) from the cache file.
        state: The current SessionState object to be modified.
        mqtt_handler: The MQTTHandler instance to queue messages.
    """
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
    """Processing the 'SessionData' Lines for starts/restarts. 
    
    Both session starts and restarts from a red flag is broadcasted similarly.'
    This function operates in two ways:

    A: If the SessionState has not discovered a 'true start time' this will trigger
       the timer for this, and set the true_session_start_time. This is used for the
       calibration feedback the user can use.
    B: Or if the a true start *has* been discovered and we're in a 'RED' race_state
       it is used to call the return_to_green function.

    There is a chance that yellow flags are done similarly, but this needs a lot
    more testing/checking in the data to figure out, but if so could greatly simplify
    the way yellow flags are handled.
    
    Args:
        line: The raw data line (as a string) from the cache file.
        state: The current SessionState object to be modified.
        mqtt_handler: The MQTTHandler instance to queue messages.
    """
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

def process_track_status_line(line: str, state: SessionState, mqtt_handler: MQTTHandler) -> None:
    """Processing 'TrackStatus' lines for track events.

    This popped up during the FP1 session of the 2025 Mexico Grand Prix
    and seemed to be a simpler form of the 'RaceControlMessages'

    **YELLOW**: Sets the race state to YELLOW if we're in green conidition
                and broadcasts the 'YELLOW' flag. No info about sectors.
    **RED**: Sets the race state to RED, clears any yellow flags and 
             broadcasts the 'RED' flag. There were no red flags during the
             session so I am just guessing this is how red flags are 
             communicated.
    **CLEAR**: Returns the sesssion to green if it isn't so already
    
    Args:
        line: The raw data line (as a string) from the cache file.
        state: The current SessionState object to be modified.
        mqtt_handler: The MQTTHandler instance to queue messages.
    """
    try:
        category, payload, _ = ast.literal_eval(line)
    except (ValueError, SyntaxError):
        return
    
    if category == 'TrackStatus':
        logging.info(f'Found track status line!')
        msg = payload.get('Message', None)
        # 🟡 YELLOW FLAGS 🟡
        if msg == 'Yellow' and state.race_state == 'GREEN':
            state.set_race_state('YELLOW')
            mqtt_payload = json.dumps({"flag": 'YELLOW', "message": 'YELLOW FLAG ON TRACK!'})
            mqtt_handler.queue_message(MqttTopics.FLAG_TOPIC, mqtt_payload)
        # 🚩 RED FLAGS 🚩
        elif msg == 'Red':
            state.set_race_state('RED')
            state.clear_yellow_flags()
            mqtt_payload = json.dumps({"flag": 'RED', "message": 'RED FLAG ON TRACK!'})
            mqtt_handler.queue_message(MqttTopics.FLAG_TOPIC, mqtt_payload)
        # 👍 CLEAR Flags 👍
        elif msg == 'AllClear' and state.race_state != 'GREEN':
            return_to_green(state, mqtt_handler, 'TRACK CLEAR RETURN TO GREEN!')

