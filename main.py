import time
import logging
import argparse
from datetime import timedelta, datetime
import json
import queue
from pathlib import Path

import config
import mqtt_config
from src.drs.session_state import SessionState
import src.drs.f1_utils as f1_utils
from src.drs.mqtt_handler import MQTTHandler
from src.drs.mqtt_topics import MqttTopics

DRS_VERSION = "0.6.0"

SESSION_MAP = {
    'p' : 'practice',
    'fp' : 'practice',
    'practice' : 'practice',
    'q' : 'qualifying',
    'sq' : 'qualifying',
    'qualifying' : 'qualifying',
    'sprint qualifying' : 'qualifying',  
    'r' : 'race',
    'sr' : 'race',
    'race' : 'race',
    'sprint race' : 'race',
    }


parser = argparse.ArgumentParser(description="F1 Dahsboard Reaction Service")
parser.add_argument(
    "session_type",
    help="The type of session to monitor: practice, free practice, qualifying, sprint qualifying, race, sprint race"
)
parser.add_argument(
    '-fl', '--force-lead',
    metavar='TEAM_NAME',
    type=str,
    default=None,
    help="(Optional) Force an initial leader state on startup. E.g., --force-leader Ferrari",
)

args = parser.parse_args()

normalized_session = SESSION_MAP.get(args.session_type.lower())

if not normalized_session:
    logging.error(f"Error: Invalid session type '{args.session_type}'.")
    logging.error(f"Valid options are: {', '.join(SESSION_MAP.keys())}")
    exit(1)

def load_drs_data(filename : str = "drs_data.json") -> dict:
    """Loads the static F1 driver and team data from the JSON file"""
    data_path = Path(__file__).parent / "data" / filename
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Data file not found at {data_path}")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Could not decode JSON from {data_path}. Check for syntax errors: {e}")
        return {}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    drs_data = load_drs_data()
    if not drs_data:
        logging.error("Could not load DRS data. Exiting.")
        exit(1)

    session_state = SessionState(session_type=normalized_session, teams_data=drs_data.get("teams", {}), drivers_data=drs_data.get("drivers", {}))

    if session_state.session_type == 'race':
        race_lead_process = f1_utils.process_race_lead_line
    else:
        race_lead_process = f1_utils.process_lap_time_line

    command_queue = queue.Queue()

    mqtt = MQTTHandler(
        broker_ip=mqtt_config.MQTT_BROKER_IP,
        port=mqtt_config.MQTT_PORT,
        username=mqtt_config.MQTT_USERNAME,
        password=mqtt_config.MQTT_PASSWORD,
        delay=config.PUBLISH_DELAY,
        command_queue=command_queue,
    )

    if args.force_lead:
        logging.info(f"Setting initial leading team as {args.force_lead}")
        session_state.update_session_lead(driver='FORCE', driver_number='0', team=args.force_lead)
        forced_lead_payload = json.dumps({"driver": "FORCE", "drivcer_number": "0","team": args.force_lead})
        mqtt.queue_message(MqttTopics.LEADER_TOPIC, forced_lead_payload, immediate=True)

    try:
        cache_file = config.CACHE_FILENAME
        with open(cache_file, 'r', encoding='utf-8', errors='replace') as f:
            logging.info(f"DRS {DRS_VERSION} started {session_state.session_type} session. Reading live data from '{cache_file}'...")
            f.seek(0, 2)
            while True:
            # Try block to look for user input delay from HA-
                try:
                    command = command_queue.get_nowait()
                    if command == "CALIBRATE_START":

                        # Ignore calibration after time limit as to avoid any "accidental presses"
                        if session_state.true_session_start_time and (time.monotonic() - session_state.true_session_start_time) > 300:
                            continue

                        if session_state.true_session_start_time:
                            new_delay = time.monotonic() - session_state.true_session_start_time
                            mqtt.set_delay(new_delay)
                            logging.info(f"received 'CALIBRATE_START' command from HA and set it to {new_delay}s")
                except queue.Empty:
                    pass

                line = f.readline()
                if not line:
                    time.sleep(0.1)
                else:
                    try:
                        f1_utils.process_session_data_line(line, session_state, mqtt)
                        race_lead_process(line, session_state, mqtt)
                        f1_utils.process_race_control_line(line, session_state, mqtt)
                    except Exception as e:
                        logging.error(f"Error processing line: {e}")

                # Check if we're in qualifying, and that we're in-between sessions
                if (session_state.session_type == 'qualifying' and 
                    session_state.cooldown_active and 
                    session_state.session_end_time and 
                    session_state.quali_session != 'Q3'):
                    if (time.monotonic() - session_state.session_end_time) > 180:
                        logging.info("Resetting for next Qualifying session")
                        SessionState.reset_for_next_quali_segment()
    

    except KeyboardInterrupt:
        logging.info("Service stopped by user.")
    except FileNotFoundError:
        logging.error(f"[FATAL] Data file not found: {config.CACHE_FILENAME}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        mqtt.disconnect()
        logging.info("MQTT client disconnected.")