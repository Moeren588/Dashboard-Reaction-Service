"""MQTT Handler - Handles publishing queue and background publishing to the Broker"""
import paho.mqtt.client as mqtt
import logging
import threading
import time
from datetime import datetime, timedelta
from queue import Queue

# APP_CONTROL_DELTA_DELAY_TOPIC = "f1/service/delta_delay"
CONTROL_TOPIC = "f1/service/control"

class MQTTHandler:
    def __init__(self, broker_ip, port, username, password, delay, command_queue: Queue):
        self.client = mqtt.Client(client_id="f1_data_service_publisher")
        self.client.username_pw_set(username, password)
        self.client.on_message = self._on_message
        self.command_queue = command_queue
        self.client.on_connect = self._on_connect
        # self.client.on_message = self._on_message
        
        self.publish_delay = timedelta(seconds=delay)
        self._pending_messages = []
        self._lock = threading.Lock()
        
        logging.info(f"Connecting to MQTT Broker at {broker_ip}...")
        self.client.connect(broker_ip, port)
        self.client.loop_start()

        # Start the background publisher thread
        self.publisher_thread = threading.Thread(target=self._publisher_loop, daemon=True)
        self.publisher_thread.start()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("MQTT Connection Succseful!")
        else:
            logging.error(f"Failed to connect to MQTT, return code {rc}")

    def _on_message(self, client, userdata, msg):
        """Handles incoming MQTT messages. Mainly for DRS CONTROL"""
        if msg.topic != CONTROL_TOPIC:
            return
        
        try:
            command = msg.payload.decode('utf-8')
            logging.info(f"Received command on control topic: '{command}")

            if command == "CALIBRATION_START":
                self.command_queue.put("CALIBRATION_START")

            elif command.startswith("ADJUST:"):
                _, value_str = command.split(":")
                adjustment = float(value_str)
                current_delay_sec = self.publish_delay.total_seconds()
                self.set_delay(current_delay_sec + adjustment)

        except Exception as e:
            logging.warning(f"Could not process command from paylod '{msg.payload}' : {e}")

    def set_delay(self, new_delay_seconds: float):
        if new_delay_seconds < 0:
            new_delay_seconds = 0

        self.publish_delay = timedelta(seconds=new_delay_seconds)

    def _publisher_loop(self):
        while True:
            messages_to_publish = []

            with self._lock:
                for i in range(len(self._pending_messages) - 1, -1, -1):
                    publish_time, topic, payload = self._pending_messages[i]
                    
                    if datetime.now() >= publish_time:
                        messages_to_publish.append((topic, payload))
                        self._pending_messages.pop(i)

            for topic, payload in messages_to_publish:
                self.client.publish(topic, payload, retain=True)
                logging.info(f"Published to {topic} : {payload}")

            time.sleep(0.5)

    def queue_message(self, topic: str, payload: str, immediate : bool = False) -> None:
        """Adds a message to the Publishing Queue"""
        if immediate:
            publish_time = datetime.now()
        else:
            publish_time = datetime.now() + self.publish_delay
        
        with self._lock:
            self._pending_messages.append((publish_time, topic, payload))
        logging.info(f"Event queued for topic '{topic}' with payload '{payload}'. Will be sent at {publish_time.strftime('%H:%M:%S')}")

    def disconnect(self):
        self.client.disconnect()
        self.client.loop_stop()