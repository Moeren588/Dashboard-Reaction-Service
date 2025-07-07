# f1-data-project
A small project gathering real time data from F1 Races to send to Home Assistant automations using MQTT.
The project bases itself on the [FastF1](https://docs.fastf1.dev/index.html) Livetiming API to fetch the data real time.

# Current Status
[X] Service to run for Free Practice
[X] Properly tested during a Free Practice
[X] Service to run for Qualifying
[] Properly tested during a Qualifying
[X] Service to run for Race
[] Properly tested during a Race

Because I started this project right before the British Grand Prix I had to do a mix of testing and developing during the
sessions.

## Plans going forward
- Properly test the tool during actual events
- Refactor the code so the tool only needs one script to run all services
- Better handling of racing inshidents: Flags and Safety Cars

# My Use-case and setup
The project is meant for personal use, but if you see any value in it feel free to give it a try!

The idea is to trigger home events for my smart home devices such as hue lights depending on events on track
(such as Safety Car or Red Flags), or who is in the lead.

I have a homelab setup where the broker and python project is running in a container, while the Home Assistant OS
is running on a seperate VM. MQTT communication will hence only run within the confines of the local network.

# Requirements
On top of the external libraries of the project, there's also a need for some extra files that are expected,
but not included for security and setup reasons.

## mqtt_config.py
The script will look for a config file in the same directory as the python script. The config file holds all
your MQTT information. The template looks like this:

```python
MQTT_BROKER_IP = "0.0.0.0" 
MQTT_PORT = 1883 # For unsecure communication running over local network
MQTT_USERNAME = "service_user_name"
MQTT_PASSWORD = "your_strong_password" # MQTT password that's also present in your Home Assistant
```

## config.py
The config script is a simple script file that simply holds some key variables that allows for some easy customization
without having to edit multiple scripts. Currently it allows you to set
    - **Delay timer**: The delay between received live message and MQTT publishing (due to delays in the TV broadcast)
    - **Cache filename**: the name of the cache file you will listen to with the service scripts.

## Caching folder
The FastF1 API can load/save cache, and this is done in a sub directory named 'ff1_cache'.
This dir is included in gitnore to not spam the repo with old/wasted cache, so this has to be made manually!

# Connecting to the Live timing client
Run the following command where {cache_file.txt} is the file the live timing will write to
> python -m fastf1.livetiming save --append cache_file.txt

>[!NOTE]
>    The livetiming starts broadcasting around 5 min before event start. The connection times out after
>    60s of no broadcasts. So be aware and not start the livetiming too early as it will cut your connection.

>[!WARNING]
>    The connection to the Live timing client gets disconnected after 2 hours! Read more about this
>    And possible workrounds on the [FastF1 documentation](https://docs.fastf1.dev/livetiming.html)
