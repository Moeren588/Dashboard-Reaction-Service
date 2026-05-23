"""A combined starter script that runs both livetiming and the DRS"""
import subprocess
import sys
import os
import time
import atexit
import logging
import argparse
from datetime import datetime, timedelta

from src.drs.args_validation import get_shared_parser, validate_drs_args

try:
 from config import CACHE_FILENAME
except ImportError:
    logging.warning(f'Could not import CACHE_FILENAME from config.py. Defulting to "cache.txt"')
    CACHE_FILENAME = 'cache.txt'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

processes = []

def cleanup_process():
    """Terminates all child processes gracefully"""
    logging.info("Shutting down child processes...")
    for p in processes:
        if p.poll() is None:
            try:
                p.terminate()
                logging.info(f"Terminated process")
            except Exception as e:
                logging.warning(f"Could not terminate {p.pid}: {e}")

    # Wait for a sec for graceful shutdown
    time.sleep(1)

    for p in processes:
        if p.poll() is None: # Time to keep more heavy handed
            try:
                p.kill()
                logging.warning(f"Killed process {p.pid}")
            except Exception as e:
                logging.error(f"Could not kill {p.pid}: {e}")

atexit.register(cleanup_process)

def stall_until_session(start_time_str: str, buffer_minutes: int):
    """Stalls service initialization until the calculated window opens."""
    now = datetime.now()
    session_time = None

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%H:%M"):
        try:
            parsed = datetime.strptime(start_time_str, fmt)
            if fmt == "%H:%M":
                session_time = now.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)
                if session_time < now:
                    session_time += timedelta(days=1)
            else:
                session_time = parsed
            break
        except ValueError:
            continue

    if not session_time:
        logging.error(f"Could not parse start time '{start_time_str}'. Skipping stall phase.")
        return
    
    target_boot_time = session_time - timedelta(minutes=buffer_minutes)
    wait_seconds = (target_boot_time - now).total_seconds()

    if wait_seconds <= 0:
        logging.info(f"Inside the execution window. Bypassing stall.")
        return
    
    logging.info(f"Session targeted: {session_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"System countdown active until: {target_boot_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        while wait_seconds > 0:
            mins, secs = divmod(int(wait_seconds), 60)
            hours, mins = divmod(mins, 60)
            countdown = f"{hours:02d}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins:02d}:{secs:02d}"

            sys.stdout.write(f"\r[*] Service on standby. Booting in: {countdown} ... ")
            sys.stdout.flush()
            time.sleep(1)
            wait_seconds = (target_boot_time - datetime.now()).total_seconds()
        print("\n")
        logging.info("Target window reached! Activating services.")
    except KeyboardInterrupt:
        print("\n")
        logging.info("Standy manual override. Exiting wrapper")
        sys.exit(0)
    

p1 = None
p2 = None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        parents=[get_shared_parser()],
        description="F1 Pitwall DRS Wrapper Service"
    )
    parser.add_argument("-st", "--start-time", type=str, default=None, help="Session start time (HH:MM or YYYY-MM-DD HH:MM)")
    parser.add_argument("-b", "--buffer", type=int, default=2, help="Minutes before start time to wake up.")

    args = parser.parse_args()
    if not validate_drs_args(args.session_type, args.force_lead):
        logging.error(f"Pre-flight argument validation failed. Aborting starutp.")
        sys.exit(1)

    if args.start_time:
        stall_until_session(args.start_time, args.buffer)

    main_py_args = [args.session_type]
    if args.force_lead:
        main_py_args += ["-fl", args.force_lead]

    try:
        python_exe = sys.executable

        logging.info("Starting FastF1 livetiming")
        cmd1 = [python_exe, "-m", "fastf1.livetiming", "save", "--append", CACHE_FILENAME]
        p1 = subprocess.Popen(cmd1, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        processes.append(p1)

        time.sleep(3)
        logging.info(f"Starting main.py with args: {' '.join(main_py_args)}")
        cmd2 = [python_exe, "main.py"] + main_py_args
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        p2 = subprocess.Popen(cmd2)
        processes.append(p2)

        while p1.poll() is None and p2.poll() is None:
            time.sleep(0.5)

        if p1.poll() is not None:
            p1_code = p1.poll()
            logging.error(f"FastF1 livetiming terminated with code {p1_code}")
            stderr_output = p1.stderr.read()
            if stderr_output:
                logging.error(f"FastF1 stderr:\n{stderr_output.decode().strip()}")

            if p2.poll() is None:
                logging.info(f"Terminating main.py due to livetiming shutdown")
                p2.terminate()
                p2.wait()

        elif p2.poll() is not None:
            p2_code = p2.poll()
            logging.error(f"main.py terminated with code {p2_code}")

            if p1.poll() is None:
                logging.info(f"Terminating Livetiming due to main.py shutdown")
                p1.terminate()
                p1.wait()
    
    except KeyboardInterrupt:
        logging.info("\nKeyboard interrupt received. Initiating shutdown...")

        if p1 and p1.poll() is None:
            try:
                p1.terminate()
            except Exception as e:
                logging.warning(f"Could not terminate p1: {e}")

        if p2 and p2.poll() is None:
            try:
                p2.wait() # Wait for the user input on caching
                logging.info('main.py has exited.')
            except Exception as e:
                logging.warning(f'Error signaling main.py: {e}. Falling back to cleanup.')
                    
    except Exception as e:
        logging.error(f"An unexpected error occured in pitwall.py: {e}")
    finally:
        logging.info("Exiting starter script.")
