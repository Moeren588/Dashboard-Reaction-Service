import time
import os
import json
import logging
from datetime import timedelta
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
def process_line(line, state, mqtt_handler):
    try:
        data_list = eval(line)
        category, payload = data_list[0], data_list[1]
        
        leader_topic = "f1/race/leader"
        flag_topic = "f1/race/flag_status"

        if category == 'TimingData' and 'Lines' in payload:
            for num, data in payload['Lines'].items():
                if 'Abbreviation' in data: state['driver_abbreviations'][num] = data['Abbreviation']

        if category == 'TimingData' and 'Lines' in payload:
            for num, data in payload['Lines'].items():
                if 'LastLapTime' in data and isinstance(data['LastLapTime'], dict):
                    lap_time_str = data['LastLapTime'].get('Value')
                    if lap_time_str and (lap_time := pd.to_timedelta(f"00:{lap_time_str}")) and lap_time < state['fastest_lap_info']['Time']:
                        driver_name = state['driver_abbreviations'].get(num, num)
                        state['fastest_lap_info'].update(Time=lap_time, Driver=driver_name)
                        
                        team_name = get_team_by_driver(num)
                        leader_payload = json.dumps({"driver": driver_name, "team": team_name, "lap_time": lap_time_str})
                        mqtt_handler.queue_message(leader_topic, leader_payload)

        if category == 'RaceControlMessages' and 'Messages' in payload:
            for msg_id, msg_data in payload['Messages'].items():
                if 'Flag' in msg_data and msg_data['Message'] != state.get('last_flag_message'):
                    state['last_flag_message'] = msg_data['Message']
                    flag_payload = json.dumps({"flag": msg_data['Flag'], "message": msg_data['Message']})
                    mqtt_handler.queue_message(flag_topic, flag_payload)
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
        delay=config.PUBLISH_DELAY # <-- Comes from the public config
    )

    session_state = {
        "fastest_lap_info": {"Driver": None, "Time": timedelta(days=1)},
        "driver_abbreviations": {},
        "last_flag_message": ""
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
                    continue
                process_line(line, session_state, mqtt)

    except KeyboardInterrupt:
        logging.info("Service stopped by user.")
    except FileNotFoundError:
        logging.error(f"[FATAL] Data file not found: {config.CACHE_FILENAME}")
    finally:
        mqtt.disconnect()
        logging.info("MQTT client disconnected.")