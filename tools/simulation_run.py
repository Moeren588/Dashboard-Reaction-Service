import os
import sys
import time
import logging

try:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(PROJECT_ROOT)
    from config import CACHE_FILENAME
except ImportError:
    logging.error("Could not import CACHE_FILENAME from config.py.\n Please ensure this script is in a subdirectory (e.g. 'tools/') of your main project")
    sys.exit(1)


 # --- Configuration ---
 # The delay between each event being written to the cache
DELAY_SECONDS = 10

SIMULATION_EVENTS = [
    {
        "description": "YELLOW FLAG IN SECTOR",
        "line" : "['RaceControlMessages', {'Messages': {'56': {'Utc': '2025-07-05T11:39:56', 'Category': 'Flag', 'Flag': 'YELLOW', 'Scope': 'Sector', 'Sector': 2, 'Message': 'YELLOW IN TRACK SECTOR 2'}}}, '2025-07-05T11:39:56.262Z']",
    },
    {
        "description": "CLEAR YELLOW FLAG IN SECTOR",
        "line" : "['RaceControlMessages', {'Messages': {'13': {'Utc': '2025-09-06T14:22:44', 'Category': 'Flag', 'Flag': 'CLEAR', 'Scope': 'Sector', 'Sector': 2, 'Message': 'CLEAR IN TRACK SECTOR 8'}}}, '2025-09-06T14:22:43.772Z']",
    },
    {
        "description": "SAFETY CAR OUT",
        "line" : "['RaceControlMessages', {'Messages': {'97': {'Utc': '2025-07-06T14:29:14', 'Lap': 14, 'Category': 'SafetyCar', 'Status': 'DEPLOYED', 'Mode': 'SAFETY CAR', 'Message': 'SAFETY CAR DEPLOYED'}}}, '2025-07-06T14:29:14.267Z']",
    },
    {
        "description": "SAFETY CAR IN",
        "line" : "['RaceControlMessages', {'Messages': {'99': {'Utc': '2025-07-06T14:38:36', 'Lap': 17, 'Category': 'SafetyCar', 'Status': 'IN THIS LAP', 'Mode': 'SAFETY CAR', 'Message': 'SAFETY CAR IN THIS LAP'}}}, '2025-07-06T14:38:36.526Z']",
    },
    {
        "description": "RED FLAG",
        "line" : "['RaceControlMessages', {'Messages': {'50': {'Utc': '2025-07-05T11:33:58', 'Category': 'Flag', 'Flag': 'RED', 'Scope': 'Track', 'Message': 'RED FLAG'}}}, '2025-07-05T11:33:58.102Z']",
    },
    {
        "description": "BACK TO RACING",
        "line" : "['SessionData', {'StatusSeries': {'4': {'Utc': '2025-09-07T13:03:34.805Z', 'SessionStatus': 'Started'}}}, '2025-09-07T13:03:34.805Z']",
    },
]

def run_simulation(mode: str) -> None:
    """ Simulates a session, writing to the cache file """
    cache_file = os.path.join(PROJECT_ROOT, CACHE_FILENAME)
    logging.info(f"Starting simulation run in {mode} mode. Will write to '{cache_file}' every {DELAY_SECONDS}s")

    try:
        with open(cache_file, 'a', encoding='utf-8') as f:
            logging.info(f"SIMULATING: STARTING THE {mode.upper()}")
            line_to_write = "['SessionData', {'StatusSeries': {'4': {'Utc': '2025-09-07T13:03:34.805Z', 'SessionStatus': 'Started'}}}, '2025-09-07T13:03:34.805Z']"

            f.write(line_to_write + '\n')
            f.flush()

            time.sleep(DELAY_SECONDS)
            # set lead to Red Bull
            logging.info(f"SIMULATING: SETTING LEAD TO VERSTAPPEN, RED BULL")
            if mode == 'race':
                line_to_write = "['TopThree', {'Lines': {'0': {'RacingNumber': '1', 'Tla': 'VER', 'BroadcastName': 'M VERSTAPPEN', 'FullName': 'Max VERSTAPPEN', 'FirstName': 'Max', 'LastName': 'Verstappen', 'Reference': 'MAXVER01', 'Team': 'Red Bull Racing', 'TeamColour': '4781D7', 'LapTime': '2:42.616'}, '1': {'RacingNumber': '81', 'Tla': 'PIA', 'BroadcastName': 'O PIASTRI', 'FullName': 'Oscar PIASTRI', 'FirstName': 'Oscar', 'LastName': 'Piastri', 'Reference': 'OSCPIA01', 'Team': 'McLaren', 'TeamColour': 'F47600', 'LapTime': '2:43.087', 'DiffToAhead': '', 'DiffToLeader': ''}}}, '2025-07-06T14:49:09.888Z']"
            else:
                line_to_write = "['TimingData', {'Lines': {'1': {'NumberOfLaps': 3, 'Sectors': {'2': {'Value': '24.386'}}, 'Speeds': {'FL': {'Value': '250'}}, 'BestLapTime': {'Value': '1:28.552', 'Lap': 2}, 'LastLapTime': {'Value': '1:27.552', 'OverallFastest': True, 'PersonalFastest': True}}}}, '2025-07-05T10:38:19.212Z']"
            f.write(line_to_write + '\n')
            f.flush()


            for event in SIMULATION_EVENTS:
                time.sleep(DELAY_SECONDS)

                description = event['description']
                line_to_write = event['line']

                logging.info(f"SIMULATING: {description}")

                f.write(line_to_write + '\n')
                f.flush()

    except FileNotFoundError:
        logging.error(f"[FATAL] Data file not found: {CACHE_FILENAME}")
    except KeyboardInterrupt:
        logging.info("Simulation stopped by user.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

    logging.info("Simulation run completed.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    mode = input("What mode do you want to simulate? (race/qualifying/fp): ").lower()
    run_simulation(mode)
            