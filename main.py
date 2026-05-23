import time
import logging
import sys
import copy
import json
import queue
from pathlib import Path

from config import CACHE_FILENAME, PUBLISH_DELAY, SESSION_CACHING_ENABLED, SESSION_CACHING_INTERVAL
import mqtt_config
from src.drs.session_state import SessionState
from src.drs.args_validation import get_shared_parser, validate_drs_args, SESSION_MAP
import src.drs.f1_utils as f1_utils
from src.drs.mqtt_handler import MQTTHandler
from src.drs.mqtt_topics import MqttTopics
import src.drs.session_caching as session_caching

DRS_VERSION = "0.9.0 2026"


# Main logic
def handle_periodic_caching(current_state: SessionState, last_cached_state: SessionState, last_cached_time: float) -> tuple[SessionState, float]:
    """Checks if the the state is dirty and caches it if it is"""
    current_time = time.monotonic()

    if (current_time - last_cached_time) > SESSION_CACHING_INTERVAL:

        if current_state != last_cached_state:
            session_caching.save_state(current_state)
            last_cached_state = copy.deepcopy(current_state)
            return copy.deepcopy(current_state), current_time
        
        return last_cached_state, current_time
    
    return last_cached_state, last_cached_time

def handle_shutdown_caching(session_sate: SessionState):
    """Handles KeyboardInterupt caching based on input"""
    try:
        session_caching.save_state(session_sate)

        retain_cache = input("Do you want to retain the session cache (do not keep if session is done)? (y/n): ").lower()

        if retain_cache != 'y':
            session_caching.delete_state_cache()

    except KeyboardInterrupt:
        logging.warning(f'Keyboard interrupt')

    except Exception as e:
        logging.error(f"Error during shutdown caching: {e}")

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
    
def setup(session_type: str) -> tuple[SessionState, MQTTHandler, queue.Queue]:
    """Handles all initial setup and object creation."""
    normalized_session = SESSION_MAP.get(session_type.lower())

    drs_data = load_drs_data()

    session_state = SessionState(session_type=normalized_session, teams_data=drs_data.get("teams", {}), drivers_data=drs_data.get("drivers", {}))

    command_queue = queue.Queue()

    mqtt_handler = MQTTHandler(
        broker_ip=mqtt_config.MQTT_BROKER_IP,
        port=mqtt_config.MQTT_PORT,
        username=mqtt_config.MQTT_USERNAME,
        password=mqtt_config.MQTT_PASSWORD,
        delay=PUBLISH_DELAY,
        command_queue=command_queue,
    )

    return session_state, mqtt_handler, command_queue

def main_loop(session_state:SessionState, mqtt: MQTTHandler, command_queue: queue.Queue):
    """Main logic for parsing the watching the cache file"""

    # Set how to discover the lead.
    if session_state.session_type == 'race':
        race_lead_process = f1_utils.process_race_lead_line
    else:
        race_lead_process = f1_utils.process_lap_time_line

    last_cached_state = copy.deepcopy(session_state)
    last_cache_time = time.monotonic()
    

    with open(CACHE_FILENAME, 'r', encoding='utf-8', errors='replace') as f:
        logging.info(f"DRS {DRS_VERSION} started {session_state.session_type} session. Reading live data from '{CACHE_FILENAME}'...")
        f.seek(0, 2)
        while True:
        # Try block to look for user input delay from HA-
            try:
                command = command_queue.get_nowait()
                if command == "CALIBRATE_START":

                    if session_state.true_session_start_time and (time.monotonic() - session_state.true_session_start_time) < 300:
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
                    f1_utils.process_track_status_line(line, session_state, mqtt)
                except Exception as e:
                    logging.error(f"Error processing line: {e}")

            # Check if we should try to cache
            if SESSION_CACHING_ENABLED:
                last_cached_state, last_cache_time = handle_periodic_caching(session_state, last_cached_state, last_cache_time)

            # Check if we're in qualifying, and that we're in-between sessions
            if (session_state.session_type == 'qualifying' and 
                session_state.cooldown_active and 
                session_state.session_end_time and 
                session_state.quali_session != 'Q3'):
                if (time.monotonic() - session_state.session_end_time) > 180:
                    logging.info("Resetting for next Qualifying session")
                    session_state.reset_for_next_quali_segment()

def apply_forced_lead(session_state: SessionState, mqtt: MQTTHandler, team_key: str | None):
    """Force sets the lead on start if one is provided"""
    if not team_key: 
        return

    logging.info(f"Setting initial leading team as {team_key}")
    try:
        clean_team_key = team_key.strip().lower().replace(' ', '_')
        forced_lead_team = session_state.teams_data.get(clean_team_key, None)
        if not forced_lead_team:
            logging.warning(f"Unable to find a team named {team_key}, skipping.")
            return
        session_state.set_session_lead(driver='FORCE', driver_number='0', team=forced_lead_team['name'])
        forced_lead_payload = json.dumps({"driver": "FORCE", "driver_number": "0","team": forced_lead_team['name'], "team_color": forced_lead_team.get('color_hex', 'FFFFFF')})
        mqtt.queue_message(MqttTopics.LEADER_TOPIC, forced_lead_payload, immediate=True)
    except Exception as e:
        logging.warning(f"Was unable to force set leading team to {team_key}. Error: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Parser
    parser = get_shared_parser()
    args = parser.parse_args()

    if not validate_drs_args(args.session_type, args.force_lead):
        sys.exit(1)

    session_state, mqtt, command_queue = setup(args.session_type)
    resumed_state = session_caching.load_state()

    if resumed_state:
        use_prev_state = input(f"Found state cache, resume from this? (y/n:)").lower()
        if use_prev_state == 'y':
            session_state = resumed_state

    apply_forced_lead(session_state, mqtt, args.force_lead)

    try:
        main_loop(session_state, mqtt, command_queue)
    except KeyboardInterrupt:
        handle_shutdown_caching(session_state)
        logging.info("Service stopped by user.")
        logging.shutdown()
    except FileNotFoundError:
        logging.error(f"[FATAL] Data file not found: {CACHE_FILENAME}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        session_caching.save_state(session_state)
    finally:
        mqtt.disconnect()
        logging.info("MQTT client disconnected.")