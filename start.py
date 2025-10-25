import subprocess
import sys
import os
import time
import atexit
import logging
import signal

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

p1 = None
p2 = None

if __name__ == "__main__":
    try:
        python_exe = sys.executable

        logging.info("Starting FastF1 livetiming")
        cmd1 = [python_exe, "-m", "fastf1.livetiming", "save", "--append", CACHE_FILENAME]
        p1 = subprocess.Popen(cmd1, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        processes.append(p1)

        time.sleep(3)

        main_py_args = sys.argv[1:]
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

        # while p2.poll is None:
        #     if p1.poll() is not None:
        #         # FastF1 died (or most likely broke connection)
        #         logging.error(f"FastF1 livetiming has cut off!")
        #         _, stderr_output = p1.communicate()
        #         if stderr_output:
        #             logging.error(f"FastF1 stderr:\n{stderr_output.decode()}")
        #         break

        #     time.sleep(0.5)

        # logging.info(f"main.py process exited with code {p2.poll()}.")
    
    except KeyboardInterrupt:
        logging.info("\nKeyboard interrupt received. Initiating shutdown...")

        if p1 and p1.poll() is None:
            try:
                p1.terminate()
            except Exception as e:
                logging.warning(f"Could not terminate p1: {e}")

        if p2 and p2.poll() is None:
            try:
                if os.name == 'nt':
                    p2.send_signal(signal.CTRL_C_EVENT)
                else:
                    p2.send_signal(signal.SIGINT)

                p2.wait()
                logging.info('main.py has exited.')
            except Exception as e:
                logging.warning(f'Error signaling main.py: {e}. Falling back to cleanup.')
                    
    except Exception as e:
        logging.error(f"An unexpected error occured in start.py: {e}")
    finally:
        logging.info("Exiting starter script.")
