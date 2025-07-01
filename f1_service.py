import fastf1 as ff1
# MQTT import
import pandas as pd
import os
import time
import json
import logging
from datetime import datetime

pd.set_option('display.max_columns', None)


script_dir = os.path.dirname(os.path.realpath(__file__))
cache_path = os.path.join (script_dir, 'ff1_cache')
ff1.Cache.enable_cache(cache_path)

print(f'--- FastF1 Test ---')

try:
    print(f'[INFO] Loading session: 2025 Austrian Grand Prix...')
    session = ff1.get_session(2025, 'Austria', 'R')
    session.load()
    print(f"[SUCCESS] Session '{session.event['EventName']}' loaded successfully!")

    print(f'--- Testing F1 Schedule loader ---')

    print("\n[INFO] Fetching the official F1 schedule for 2025...")
    # Setting include_testing=False is a good practice unless you need testing data
    schedule = ff1.get_event_schedule(2025, include_testing=False)
    print("[SUCCESS] Schedule loaded.")
    
    # --------------------------------------------------------------------------
    # 2. Find the next upcoming event
    # --------------------------------------------------------------------------
    print("\n--- Finding the next upcoming race ---")
    
    # Get the current time. The '.replace(tzinfo=None)' is important
    # to compare it with the schedule's timezone-unaware dates.
    now = pd.to_datetime(datetime.now()).replace(tzinfo=None)

    # Filter the schedule to find events that are in the future
    upcoming_events = schedule[schedule['EventDate'] > now]
    
    # The first event in this filtered list is our target
    next_event = upcoming_events.iloc[0] if not upcoming_events.empty else None

    if next_event is not None:
        print(f"Next Event Found: Round {next_event['RoundNumber']} - {next_event['EventName']}")
        print(f"Location: {next_event['Location']}, {next_event['Country']}")
        print(f"Date: {next_event['EventDate'].strftime('%Y-%m-%d')}")
        
        # ----------------------------------------------------------------------
        # 3. Load the session for the upcoming event
        # We use the 'EventName' from the schedule to get the session
        # ----------------------------------------------------------------------
        print(f"\n[INFO] Attempting to load session for '{next_event['EventName']}'...")
        # Note: This will likely fail until data for the event is available,
        # which is the expected behavior for a future race.
        gp_name = next_event['EventName']
        session = ff1.get_session(2025, gp_name, 'R')
        session.load() # This line will raise an error until the race weekend starts
        print("[SUCCESS] Session loaded.")

    else:
        print("\n[INFO] No upcoming races found for the rest of the season.")

    # laps = session.laps

    # last_leader = None
    # lead_changes = []

    # for lap_num in range(1, int(laps['LapNumber'].max()) + 1):
    #     current_lap_data = laps[laps['LapNumber'] == lap_num]

    #     leader_of_lap = current_lap_data[current_lap_data['Position'] == 1].iloc[0] if not current_lap_data[current_lap_data['Position'] == 1].empty else None

    #     if leader_of_lap is not None:
    #         current_leader = leader_of_lap['Driver']

    #         if last_leader is None:
    #             print(f"Initial leader on Lap 1: {current_leader}")
    #             last_leader = current_leader
    #         elif current_leader != last_leader:
    #             print(f"LEAD CHANGE on Lap {lap_num}: {current_leader} takes the lead from {last_leader}")
    #             lead_changes.append({'Lap': lap_num, 'New Lead': current_leader, 'Previous Lead': last_leader})
    #             last_leader = current_leader

    # print(f"--- Summary of changes ---")
    # if not lead_changes:
    #     print(f"Somehow no lead changes")
    # else:
    #     for change in lead_changes:
    #         print(f"    - Lap {change['Lap']}: {change['New Lead']} took the lead from {change['Previous Lead']}")

except Exception as e:
    print(f'[ERROR] An error occured: {e}')