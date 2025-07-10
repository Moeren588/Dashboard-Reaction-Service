import time
import logging
import argparse
from datetime import timedelta, datetime
import os

import config
import mqtt_config
import f1_utils
from mqtt_handler import MQTTHandler

parser = argparse.ArgumentParser(description="F1 Live Data Service")
parser.add_argument(
    "session_type",
    choices=['practice', 'free practice', 'qualifying', 'sprint qualifying', 'race', 'sprint race'],
    help="The type of session to monitor: practice, free practice, qualifying, sprint qualifying, race, sprint race"
)
args = parser.parse_args()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    session_state = {
        "session_type" : None,
        "fastest_lap_info": {"Time": timedelta(days=1), "Driver": None, "Team": None},
        "driver_abbreviations": {},
        "current_race_lead": {"Driver": None, "Team": None},
        "current_leader_num": None,
        "cooldown_active": False,
        "session_end_time": None,
        "quali_session" : "Q1",
        "last_flag_message": "",
        "safety_car": False,
    }

    if args.session_type == 'race' or args.session_type == 'sprint race':
        session_state['session_type'] = 'race'
        race_lead_process = f1_utils.process_race_lead_line
    elif args.session_type == 'qualifying' or args.session_type == 'sprint qualifying':
        session_state['session_type'] = 'qualifying'
        race_lead_process = f1_utils.process_lap_time_line
    else:
        session_state['session_type'] = 'practice'
        race_lead_process = f1_utils.process_lap_time_line

    mqtt = MQTTHandler(
        broker_ip=mqtt_config.MQTT_BROKER_IP,
        port=mqtt_config.MQTT_PORT,
        username=mqtt_config.MQTT_USERNAME,
        password=mqtt_config.MQTT_PASSWORD,
        delay=config.PUBLISH_DELAY
    )

    try:
        cache_file = config.CACHE_FILENAME
        with open(cache_file, 'r', encoding='utf-8') as f:
            logging.info(f"Service started. Reading live data from '{cache_file}'...")
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                else:
                    try:
                        race_lead_process(line, session_state, mqtt)
                        f1_utils.process_race_control_line(line, session_state, mqtt)
                    except Exception as e:
                        logging.error(f"Error processing line: {e}")

                # Check if we're in qualifying, and that we're in-between sessions
                if (session_state['session_type'] == 'qualifying' and 
                    session_state['cooldown_active'] and 
                    session_state['session_end_time'] and 
                    session_state['quali_session'] != 'Q3'):
                    if (datetime.now() - session_state['session_end_time']).total_seconds() > 180:
                        f1_utils.reset_for_next_session(session_state)
    
    except KeyboardInterrupt:
        logging.info("Service stopped by user.")
    except FileNotFoundError:
        logging.error(f"[FATAL] Data file not found: {config.CACHE_FILENAME}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        mqtt.disconnect()
        logging.info("MQTT client disconnected.")