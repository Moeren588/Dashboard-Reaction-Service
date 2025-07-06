import time
# import os
import json
import logging
from datetime import datetime, timedelta
try:
    import pandas as pd
except ImportError:
    logging.error("[FATAL] pandas library is required. Please run 'pip install pandas'.")
    exit()

import config
import mqtt_config

from mqtt_handler import MQTTHandler
from f1_teams import get_team_by_driver


# The process_line function remains exactly the same as before
def process_line(line: str, state: dict[str, any], mqtt_handler: MQTTHandler) -> None:
    """Processes the input line to see if it contains relevant information."""
    try:
        data_list = eval(line)
        category, payload = data_list[0], data_list[1]
        
        leader_topic = "f1/race/leader"
        flag_topic = "f1/race/flag_status"

        if category == 'TimingData' and 'Lines' in payload:
            for num, data in payload['Lines'].items():
                if 'Abbreviation' in data: state['driver_abbreviations'][num] = data['Abbreviation']

        if category == 'TopThree' and 'Lines' in payload:
            print(f'Top three detected')
            if '0' in payload['Lines']:
                p1_data = payload['Lines']['0']
                new_leader_num = p1_data.get('RacingNumber')

                print(f'0 in payload. Found {new_leader_num}')

                # If we found a leader and they are different from our stored leader
                if new_leader_num and new_leader_num != state.get('current_leader_num'):
                    
                    # --- LEAD CHANGE DETECTED ---
                    previous_leader_num = state['current_leader_num']
                    team_name = get_team_by_driver(new_leader_num)
                    

                    logging.warning("\n" + "#"*40)
                    logging.warning(f"*** 👑 NEW RACE LEADER (from TopThree)! 👑 ***")
                    logging.warning(f"Driver: {p1_data.get('Tla', new_leader_num)} ({team_name})")
                    logging.warning("#"*40 + "\n")

                    # Update the state with the new leader's number
                    state['current_leader_num'] = new_leader_num
                    
                    # Create and queue the MQTT message
                    leader_payload = json.dumps({"driver": p1_data.get('Tla', new_leader_num), "team": team_name})
                    mqtt_handler.queue_message(leader_topic, leader_payload)

        ## Check for race control flag messages 
        if category == 'RaceControlMessages' and 'Messages' in payload:
            for msg_id, msg_data in payload['Messages'].items():
                print(f'Found race control message: {msg_data}')
                if 'Flag' in msg_data and msg_data['Message'] != state.get('last_flag_message'):
                    state['last_flag_message'] = msg_data['Message']
                    # print(f"*** NEW RACE CONTROL MESSAGE:  flag: {msg_data['Flag']}, message: {msg_data['Message']} ***")
                    flag_payload = json.dumps({"flag": msg_data['Flag'], "message": msg_data['Message']})
                    mqtt_handler.queue_message(flag_topic, flag_payload)

                    if msg_data['Flag'] == 'CHEQUERED' and not state['cooldown_active']:
                        logging.warning(f"Chequered Flag for {state['current_segment']}. Starting 2-minute cooldown.")
                        state['cooldown_active'] = True
                        state['session_end_time'] = datetime.now()
    
    except Exception:
        pass

# --- Main Execution Block ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Initialize our MQTT handler by passing it the settings from both config files
    mqtt = MQTTHandler(
        broker_ip=mqtt_config.MQTT_BROKER_IP,
        port=mqtt_config.MQTT_PORT,
        username=mqtt_config.MQTT_USERNAME,
        password=mqtt_config.MQTT_PASSWORD,
        delay=config.PUBLISH_DELAY
    )

    session_state = {
        # "fastest_lap_info": {"Driver": None, "Time": timedelta(days=1)},
        "driver_abbreviations": {},
        "last_flag_message": "",
        "current_leader_num": None,
    }

    try:
        # Get the cache filename from the public config
        cache_file = config.CACHE_FILENAME
        with open(cache_file, 'r', encoding='utf-8') as f:
            logging.info(f"Service started. Reading live data from '{cache_file}'...")
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                else:
                    process_line(line, session_state, mqtt)

    except KeyboardInterrupt:
        logging.info("Service stopped by user.")
    except FileNotFoundError:
        logging.error(f"[FATAL] Data file not found: {config.CACHE_FILENAME}")
    finally:
        mqtt.disconnect()
        logging.info("MQTT client disconnected.")