import time
import os
import json
from datetime import timedelta
import paho.mqtt.client as mqtt
import logging

import mqtt_config

# The path to the file being saved by the other terminal
LIVETIMING_DATA_FILE = 'cache.txt'

MQTT_BROKER_IP = mqtt_config.MQTT_BROKER
MQTT_PORT = mqtt_config.MQTT_PORT
MQTT_USERNAME = mqtt_config.MQTT_USERNAME
MQTT_PASSWORD = mqtt_config.MQTTT_PASSWORD

MQTT_LEADER_TOPIC = "f1/race/leader"
MQTT_FLAG_TOPIC = "f1/race/flag"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- MQTT Client Setup ---
def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the broker."""
    if rc == 0:
        logging.info("MQTT Connection Successful!")
    else:
        logging.error(f"Failed to connect to MQTT, return code {rc}\n")

client = mqtt.Client(client_id="f1_live_data_service")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.connect(MQTT_BROKER_IP, MQTT_PORT)
client.loop_start() # Start a background thread to handle MQTT network traffic

print("--- F1 Live Data Parser (v3 - Laps & Flags) ---")
print(f"Reading new lines from '{LIVETIMING_DATA_FILE}'...")
print("Press CTRL+C to stop.")

def get_team_info(driver_number_str):
    """Converts a driver number string to a team name string."""
    # Driver numbers for the 2025 season (adjust if needed)
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
    return teams.get(driver_number_str, "Unknown")


# --- Function to parse lap time strings ---
def parse_lap_time(time_str):
    if not isinstance(time_str, str) or ':' not in time_str:
        return None
    full_time_str = f"00:{time_str}"
    return pd.to_timedelta(full_time_str)


def process_line(line, state):
    """Processes a single line of data from the stream."""
    try:
        data_list = eval(line)
        category = data_list[0]
        payload = data_list[1]
        
        # --- Learn Driver Abbreviations ---
        if category == 'TimingData' and 'Lines' in payload:
            for driver_num, driver_data in payload['Lines'].items():
                if 'Abbreviation' in driver_data:
                    state['driver_abbreviations'][driver_num] = driver_data['Abbreviation']

        # --- Check for new lap times ---
        if category == 'TimingData' and 'Lines' in payload:
            for driver_num, driver_data in payload['Lines'].items():
                if 'LastLapTime' in driver_data and isinstance(driver_data['LastLapTime'], dict):
                    lap_time_value = driver_data['LastLapTime'].get('Value')
                    
                    if lap_time_value:
                        current_lap_time = parse_lap_time(lap_time_value)

                        if current_lap_time and current_lap_time < state['fastest_lap_info']['Time']:
                            driver_name = state['driver_abbreviations'].get(driver_num, driver_num)
                            state['fastest_lap_info']['Time'] = current_lap_time
                            state['fastest_lap_info']['Driver'] = driver_name

                            # --- Get Team Info and Publish to MQTT ---
                            team_name = get_team_info(driver_num)
                            leader_payload = json.dumps({"driver": driver_name, "team": team_name, "lap_time": lap_time_value})
                            client.publish(MQTT_LEADER_TOPIC, leader_payload, retain=True)
                            
                            print("\n" + "="*40)
                            print(f"*** 🚀 NEW FASTEST LAP! 🚀 ***")
                            print(f"Driver: {driver_name}")
                            print(f"Time: {lap_time_value}")
                            print("="*40 + "\n")
        
        # ==========================================================
        # --- NEW: Check for Race Control Messages ---
        # ==========================================================
        if category == 'RaceControlMessages' and 'Messages' in payload:
            for msg_id, msg_data in payload['Messages'].items():
                # Check if it's a flag message and if we haven't seen this exact message before
                if 'Flag' in msg_data and msg_data['Message'] != state.get('last_flag_message'):
                    flag = msg_data['Flag']
                    message = msg_data['Message']
                    state['last_flag_message'] = message # Store the message to prevent repeats

                    # --- Publish Flag Status to MQTT ---
                    flag_payload = json.dumps({"flag": flag, "message": message})
                    client.publish(MQTT_FLAG_TOPIC, flag_payload, retain=True)
                    
                    print("\n" + "~"*40)
                    print(f"*** 🏁 NEW RACE CONTROL MESSAGE 🏁 ***")
                    print(f"Flag: {flag}")
                    print(f"Message: {message}")
                    print("~"*40 + "\n")


    except Exception:
        pass



# We need pandas just for the timedelta conversion
try:
    import pandas as pd
except ImportError:
    print("[ERROR] pandas library is required. Please run 'pip install pandas'.")
    exit()

# --- Main loop to read the file ---
try:
    with open(LIVETIMING_DATA_FILE, 'r', encoding='utf-8') as f:
        f.seek(0, 2)
        
        session_state = {
            "fastest_lap_info": {"Driver": None, "Time": timedelta(days=1)},
            "driver_abbreviations": {},
            "last_flag_message": "" # Add this to track the last seen flag message
        }
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
            
            process_line(line, session_state)

except KeyboardInterrupt:
    print("\n--- Stopping parser ---")
except FileNotFoundError:
    print(f"[ERROR] Data file not found: {LIVETIMING_DATA_FILE}")
