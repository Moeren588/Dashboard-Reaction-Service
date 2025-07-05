"""MQTT Handler - Handles publishing queue and background publishing to the Broker"""
import paho.mqtt.client as mqtt
import logging
import queue
import threading
import time

class MQTTHandler:
    def __init__(self, broker_ip, port, username, password, delay):
        self.client = mqtt.Client(client_id="f1_data_service_publisher")
        self.client.username_pw_set(username, password)
        self.client.on_connect = self._on_connect
        
        self.event_queue = queue.Queue()
        self.publish_delay = delay
        
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

    def _publisher_loop(self):
        while True:
            topic, payload = self.event_queue.get()
            logging.info(f"Event received for topic '{topic}'. Holding for {self.publish_delay} seconds...")
            time.sleep(self.publish_delay)
            self.client.publish(topic, payload, retain=True)
            logging.info(f"Published to {topic} : {payload}")
            self.event_queue.task_done()

    def queue_message(self, topic, payload):
        """Adds a message to the Publishing Queue"""
        self.event_queue.put((topic, payload))

    def disconnect(self):
        self.client.disconnect()
        self.client.loop_stop()