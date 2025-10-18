import pickle
import logging
from pathlib import Path
from typing import Optional

from .session_state import SessionState

SESSION_CACHE_FILE = Path('session_cache.pkl')

def save_state(state: SessionState):
    """Serializes and saves the SessionState object to a file"""
    try:
        with open(SESSION_CACHE_FILE, 'wb') as f:
            pickle.dump(state, f)
    except Exception as e:
        logging.error(f"Failed to save session state: {e}")

def delete_state_cache():
    """Deletes the session cache file"""
    if SESSION_CACHE_FILE.exists():
        try:
            SESSION_CACHE_FILE.unlink()
        except Exception as e:
            logging.error(f"Failed to delete session state cache: {e}")


def load_state() -> Optional[SessionState]:
    """Loads and deserializes a SessionState object from a file if it exists."""
    if not SESSION_CACHE_FILE.exists():
        return None
    try:
        with open(SESSION_CACHE_FILE, 'rb') as f:
            state = pickle.load(f)
            return state
    except Exception as e:
        logging.error(f"Failed to load session state: {e}")
        return None            