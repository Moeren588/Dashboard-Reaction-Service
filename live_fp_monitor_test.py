import fastf1 as ff1
import time
import os
import pandas as pd
from datetime import datetime

pd.set_option('display.max_columns', None)

script_dir = os.path.dirname(os.path.realpath(__file__))
cache_path = os.path.join (script_dir, 'ff1_cache')
ff1.Cache.enable_cache(cache_path)

print(f"--- F1 Live Free Practice Monitor Testing ---")
print(f"Looking for British Grand Prix, FP1 ...")

try:
    session_year = 2025
    session_gp = 'British Grand Prix'
    session_type = 'FP1'

    schedule = ff1.get_event_schedule(session_year, include_testing=False)

    event = schedule[schedule['EventName'] == session_gp].iloc[0]

    session_start_time = event[f'Session{session_type[-1]}Date']

    print(f"[INFO]: Found session: {event['EventName']} - {session_type}")
    print(f"[INFO] Scheduled Start Time: {session_start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    now_utc = pd.to_datetime('now', utc=True)

    while now_utc < session_start_time:
        time_to_wait = (session_start_time - now_utc).total_seconds()
        print(f"[INFO] Session has not started yet. Waiting for {time_to_wait/60:.2f} minutes...")

        time.sleep(60)

        now_utc = pd.to_datetime('now', utc=True)

    # Load Live Session
    session = ff1.get_session(2025, "British Grand Prix", "FP1")
    session.load(laps=True, telemetry=False, weather=False, messages=False)
    print(f"[SUCCESS]: Session '{session.event['EventName']}' - {session.name} found!")
    print("Waiting for data ...")
    print("Press CTRL+C to stop.")

    # Tracking the laps we know
    known_laps = set()

    while True:
        #Reload the lap data
        # session.load_laps()
        laps = session.laps

        if not laps.empty:
            for index, lap in laps.iloc[::-1].iterrows():
                lap_id = f"{lap['Driver']}-{int(lap['LapNumber'])}"

                if lap_id not in known_laps:
                    print(f"New Lap: {lap['Driver']} | Lap {int(lap['LapNumber'])} | Time: {lap['LapTime']} | Compound: {lap['Compound']} | Stint: {int(lap['Stint'])}")
                    known_laps.add(lap_id)

        time.sleep(10)

except KeyboardInterrupt:
    print("--- Stopping ---")
except Exception as e:
    print(f'[ERROR] An error occured: {e}')