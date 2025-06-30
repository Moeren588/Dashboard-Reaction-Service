# f1-data-project
A small project gathering real time data from F1 Races to send to Home Assistant automations using MQTT.
The project bases itself on the FastF1 Python API.

# My Use-case and setup
The project is meant for personal use, but if you see any value in it feel free to give it a try!

The idea is to trigger home events for my smart home devices such as hue lights depending on events on track
(such as Safety Car or Red Flags), or who is in the lead.

I have a homelab setup where the broker and python project is running in a container, while the Home Assistant OS
is running on a seperate VM. MQTT communication will hence only run within the confines of the local network.

# Requirements
On top of the external libraries of the project, there's also a need for some extra files that are expected,
but not included for security and setup reasons.

## config
The script will look for a config file in the same directory as the python script. The config file holds all
your MQTT information. The template looks like this:

```python
MQTT_BROKER_IP = "0.0.0.0" 
MQTT_PORT = 1883 # For unsecure communication running over local network
MQTT_USERNAME = "service_user_name"
MQTT_PASSWORD = "your_strong_password" # MQTT password that's also present in your Home Assistant
```
