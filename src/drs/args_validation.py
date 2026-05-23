import argparse
import logging
from pathlib import Path
import json

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

def load_drs_data(filename : str = "drs_data.json") -> dict:
    """Loads the static F1 driver and team data from the JSON file"""
    data_path = Path(__file__).parents[2] / "data" / filename
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Data file not found at {data_path}")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Could not decode JSON from {data_path}. Check for syntax errors: {e}")
        return {}
    
def get_shared_parser() -> argparse.ArgumentParser:
    """Returns a parser pre-configured with core DRS application args."""
    parser = argparse.ArgumentParser(add_help=False)
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

    return parser

def validate_drs_args(session_type: str, force_lead: str | None) -> bool:
    """Validates the core application business rules before execution"""
    # SESSION TYPE
    normalized_session = SESSION_MAP.get(session_type.lower())
    if not normalized_session:
        logging.error(f"[VALIDATION ERROR]: Invalid session type '{session_type}'.")
        logging.error(f"Valid options are: {', '.join(SESSION_MAP.keys())}")
        return False
    
    drs_data = load_drs_data()
    if force_lead and drs_data:
        clean_team_key = force_lead.strip().lower().replace(' ', '_')
        if clean_team_key not in drs_data.get("teams", {}):
            logging.error(f"[VALIDATION ERROR] Unable to find a valid team name '{force_lead}' in data configuration")
            return False
        
    if normalized_session == 'race' and not force_lead:
        logging.error("="*60)
        logging.error("[VALIDATION ERROR] Starting a 'race' session with no leader set.")
        logging.error("Please provide the P1 team using the --force-lead (-fl) argument.")
        logging.error('Example: python main.py -fl "Red Bull"')
        logging.error("="*60)
        return False
    
    return True