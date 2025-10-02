# Dashboard Reaction Service

The Dashboard Reaction Service (or DRS for short) is a small project gathering real time data from F1 Races to send to 
Home Assistant automations using MQTT. The project bases itself on the [FastF1](https://github.com/theOehrly/Fast-F1) 
Livetiming API to fetch the data real time.

![HA-Automation_3](https://github.com/user-attachments/assets/1aa65c1d-8c3a-40bb-9d64-06335587a05e)


## Features
* Sync smart lights with the F1 broadcast leader, matching their team colors.
* Automate dynamic lighting scenes for Safety Car, VSC, and Red Flag events.
* Dynamically calibrate the broadcast delay using Home Assistant to perfectly sync on-track events with your screen.

## What it isn't
This is not a tool that will let you get a fancy map with all the car positions, or get you a full list of the current race standings. It will not give you nice graphs of car telemetry or advanced analytics.

To put it simply: it is a tool that I use to get an exact "here and now" picture of events that allows my smart devices around the TV to react to what is happening *right now* in the race. It is intended to enhance the F1/Sky-TV experience, not replace it.

## Requirements

### Prerequisites
* Python 3.9+
* A running Home Assistant instance.
* An MQTT Broker (the Mosquitto Broker add-on for Home Assistant is a great choice).
* Smart lights/devices configured in Home Assistant (e.g., Philips Hue to respond to the events).

### Project Files
Before running, you must create two configuration files:

1. `mqtt_config.py`: Holds your MQTT broker credentials. Create it in the root directory.
```python
MQTT_BROKER_IP = "0.0.0.0" 
MQTT_PORT = 1883 # For unsecure communication running over local network
MQTT_USERNAME = "service_user_name"
MQTT_PASSWORD = "your_strong_password" # MQTT password that's also present in your Home Assistant
```
2. `config.py`: Contains key variables for the service. You can edit the existing file to set your preferred initial broadcast delay and cache filename.

> [!NOTE]
> **A Note on the `PUBLISH_DELAY`**
> 
> You might wonder why there's a delay between the script receiving a message and publishing it to MQTT. This is the most important setting for syncing the service with what you see on screen.
>
> The official F1 timing data, which this tool uses via the FastF1 API, often arrives many seconds (some report up to a minute!) **before** you see the corresponding action on your F1TV or television broadcast. This is due to natural broadcast and streaming delays.
> 
>The `PUBLISH_DELAY` variable lets you add a buffer to compensate for this. By setting a delay, you ensure that when your lights change color for a new leader or a safety car, it happens at the exact moment you see it on your screen, not seconds beforehand.
>
> You'll need to fine-tune this value based on your specific broadcast: 
> - A good-guess starting point is often between **50 and 60 seconds.** (based on personal experience)
> - Remember, you can adjust this delay live using the **Delay Calibration** buttons in Home Assistant once the session has started.

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Moeren588/Dashboard-Reaction-Service
cd Dashboard-Reaction-Service
```

### 2. Create a Python Virtual Environment (Optional, but Recommended!)
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create Configuration Files
Create the mqtt_config.py file as described in the Requirements section above and review config.py.

## Usage
The service requires two separate processes running in two separate terminals.

### 1. Start the FastF1 Live Timing Client
In your first terminal, activate the virtual environment and run the following command. This will connect to the F1 servers and start saving live data to the cache file.

```bash
python -m fastf1.livetiming save --append cache.txt
```

>[!NOTE]
>    The livetiming starts broadcasting around 5 min before event start. The connection times out after
>    60s of no broadcasts. So be aware and not start the livetiming too early as it will cut your connection.

### 2. Start the DRS Service
In a second terminal, activate the virtual environment and run the `main.py` script. The command requires a session type argument and accepts optional flags. When running, the service will start reading from `cache.txt` (or file defined in `config.py`) and publishing events to your MQTT broker.

**Syntax**:
```bash
python main.py <session_type> [options]
```

**Example:**
```bash
python main.py qualifying --force-lead "Ferrari"
```

#### Arguments
* <session_type>**(Required)**: Specifies the type of session to monitor. Valid options are:
  * `practice`(or `p`, `fp`)
  * `qualifying`(or `q`, `"sprint qualifying"`, `sq`) 
  * `race`(or `p`, `"sprint race"`, `sr`) 
* `--force-lead <TEAM_NAME>`**(Optional)**: Sets an initial leader state on startup. This is useful for testing automations without waiting for a leader to be established.

# Home Assistant Configuration
Once the DRS service is running, you need to configure Home Assistant to listen to the MQTT topics. Below you fill find examples for setups and automations.

## 1. MQTT Sensors
The following is an example of you can write into your `configuration.yaml` file to create sensors for the flag status and current leader.
```yaml
# In your configuration.yaml
mqtt:
  sensor:
    - name: "F1 MQTT Flag Status"
      state_topic: "f1/race/flag_status"
      value_template: "{{ value_json.flag }}"
      json_attributes_topic: "f1/race/flag_status"
    
    - name: "F1 MQTT Leader Team"
      state_topic: "f1/race/leader"
      value_template: "{{ value_json.team }}"
      json_attributes_topic: "f1/race/leader"
```
Remember to restart your Home Assistant whenever you make changes to the `configuration.yaml` file.

## 2. Scripts for Lighnting Effects
Using scripts to define your lighting effects keeps your automations clean. This makes everything more seperated, and it makes it easier to make changes to certain aspects and effects, instead of having to dig through the entire automation. You can call these scripts from the main automation. Here are some examples.

### Team Example (Alpine)
```yaml
sequence:
  - target:
      entity_id:
        - light.tv_left
        - light.livingroom_spot
        - light.livingroom_spot_3
    data:
      rgb_color:
        - 0
        - 91
        - 169
      brightness_pct: 100
    action: light.turn_on
  - target:
      entity_id:
        - light.tv_right
        - light.livingroom_spot_1
        - light.livingroom_spot_4
    data:
      rgb_color:
        - 235
        - 75
        - 199
      brightness_pct: 100
    action: light.turn_on
alias: F1 Team Alpine
mode: single
description: ""
```

### Event Example (Safety Car)
```yaml
sequence:
  - target:
      entity_id: light.group_lights_living_room_tv
    data:
      color_name: gold
      brightness_pct: 100
    action: light.turn_on
  - target:
      entity_id: light.group_lights_living_room_tv
    data:
      flash: long
    action: light.turn_on
  - target:
      entity_id: light.living_room_ceiling_lights
    data:
      color_name: gold
      brightness_pct: 40
    action: light.turn_on
alias: F1 Safety Car
mode: single
icon: mdi:car-emergency
description: ""
```

## 3. Main Automation
This automation listens to the MQTT topics and calls the appropriate script based on the message payload. The `input_boolean.f1_mode` is a toggle you can create in Home Assistant to easily enable or disable the lighting effects.

```yaml
alias: F1 Race Lighting Control
description: Controls Hue lights based on F1 race status
triggers:
  - topic: f1/race/flag_status
    id: flag_update
    trigger: mqtt
  - topic: f1/race/leader
    id: leader_update
    trigger: mqtt
conditions:
  - condition: state
    entity_id: input_boolean.f1_mode
    state: "on"
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: >-
              {{ trigger.id == 'flag_update' and trigger.payload_json.flag ==
              'RED' }}
        sequence:
          - target:
              entity_id: script.f1_red_flag
            action: script.turn_on
            data: {}
      - conditions:
          - condition: template
            value_template: >-
              {{ trigger.id == 'flag_update' and trigger.payload_json.flag in
              ['SAFETY CAR', 'VSC'] }}
        sequence:
          - target:
              entity_id: script.f1_safety_car
            action: script.turn_on
            data: {}
      - conditions:
          - condition: template
            value_template: >-
              {{ trigger.id == 'flag_update' and trigger.payload_json.flag ==
              'YELLOW', 'DOUBLE YELLOW' }}
        sequence:
          - target:
              entity_id: script.f1_yellow_flag
            action: script.turn_on
            data: {}
    default:
      - choose:
          - conditions:
              - condition: template
                value_template: "{{ trigger.payload_json.team == 'Ferrari' }}"
            sequence:
              - target:
                  entity_id: script.f1_ferrari
                action: script.turn_on
                data: {}
          - conditions:
              - condition: template
                value_template: "{{ trigger.payload_json.team == 'Red Bull' }}"
            sequence:
              - target:
                  entity_id: script.f1_red_bull
                action: script.turn_on
                data: {}
          - conditions:
              - condition: template
                value_template: "{{ trigger.payload_json.team == 'McLaren' }}"
            sequence:
              - target:
                  entity_id: script.f1_mclaren
                action: script.turn_on
                data: {}
```

## 4. Delay Calibration
The time delay between when the python service receives messages, and when you see it on the broadcast
can be very hard to detect. That is why the service also listens in on channels that allows for adjustments
in the broadcasting delay. Currently it has two functions `calibrate start` and `Adjust`.

#### Calibrate Start
The service should detect in the messages it receives when it sees the session start message. With the automation
setup below, you can have a button you press when you see the broadcast start. The service will then use this
difference to set the MQTT publishing delay.
```yaml
alias: F1 Calibrate Start
description: Send the session start time for calibrating the delay
sequence:
  - data:
      topic: f1/service/control
      payload: CALIBRATE_START
    action: mqtt.publish
```

>[!Note]
> For Practice and Qualifying it will be when there's a Green light at the Pit Exit (F1 TV usually has a countdown to this). For Qualifying it is only needed for the start of Q1.
>
> For races this is when it's all five lights out and away they go! (**not** the start of the formation lap!)

#### Adjust
Another way is to publish direct adjustment values that is added or subtracted to the current delay. The example
below shows how the automation script and the button is set up, which would allow you to create some button variations 
based on one automation script
```yaml
alias: F1 Adjust Delay
description: Adjusts the F1 MQTT delay by a specific amount.
fields:
  adjustment_value:
    description: The number of seconds to add or subtract from the delay
    example: "1.0"
sequence:
  - data:
      topic: f1/service/control
      payload: ADJUST:{{ adjustment_value }}
    action: mqtt.publish
mode: single
```

**button example**
```yaml
- type: button
        name: Delay +1s
        icon: mdi:plus-box
        tap_action:
          action: call-service
          service: script.f1_adjust_delay
          data:
            adjustment_value: "1.0"
```

>[!NOTE]
> It is important that the payload starts with 'ADJUST:' followed by the
> value!

**Screenshot of my delay adjustment buttons**
<img width="1079" height="1010" alt="Screenshot of my Home Assistant delay and calibartion buttons" src="https://github.com/user-attachments/assets/7e0308a2-30a0-4115-bf62-077320eef0c3" />


# MQTT Topic Reference
The service communicates using the following MQTT topics.

## Topics Published by DRS
These topics are broadcast by the service for Home Assistant to consume.
* **Topic:** `f1/service/running_status`
  * **Payload:** `ON` or `OFF`
  * **Description:** A retained message that shows whether the DRS script is currently running or has shut down. Ideal for a status light in your dashboard, letting you know if the service for some reason has shut down or crashed.
* **Topic:** `f1/service/publishing_delay`
  * **Payload:** A number representing the delay in seconds (e.g.,`54.25` )
  * **Description:** A retained message holding the current publishing delay.
* **Topic:** `f1/race/flag_status`
  * **Payload:** e.g,`{"flag": "YELLOW", "message": "DOUBLE YELLOW IN TRACK SECTOR 8"}`
  * **Description:** A retained message that provides the current overall track status. (e.g,`GREEN`, `YELLOW`, `SAFETY CAR`, `RED`)
* **Topic:** `f1/race/leader`
  * **Payload:** e.g,`{"driver": "LEC", "driver_number": "16", "team": "Ferrari"}`
  * **Description:** An event message published when a new leader is set. The leader is determined by race lead in races, or fastest lap in pracitce and qualifying. Note that fastest lap is reset between Qualifying sessions (i.e. Q1, Q2 and Q3).

## Topics Listened to by DRS
This topic is used to send commands from Home Assistant back to the service.
* **Topic:** `f1/service/control`
  * **Payload:** `CALIBRATE_START` or `ADJUST:<number>`
  * **Description:** Used to send commands to adjust the publishing delay in real-time. (See HA adjustment section for more info)

# Testing and Debugging
You might want to test that your setup works, and since the main functionality of this tool relies on the lime data coming in *during* a broadcast; it can be tricky and frustrating. For this you will find a text file containing "debugging lines" in `docs\debug_lines.txt`.

* First ensure DRS is running, and HA is set to act on the MQTT topics.
* Copy a line from `debug_lines.txt` that you want to test in your HA setup (I have tried to organize them based on events)
* Paste it into the cache file DRS is listening to.
* Save the cache file and see if DRS is logging a response, and then if your HA is doing what you expect.
  * A good tip here is to temporarily set publishing delay very short in `config.py`

## E2E Testing
Version `0.6.0` introduced a session simulator tool (found here `tools/simulation_run.py`) which is an End-to-End testing tool. The idea is that it attempts to simulate the livetmining client by writing to the cache file. This allows you to fully test the DRS tool, broadcasting to MQTT and seeing it happen in your smart home (hopefully). To use it:

* Set your `PUBLISH_DELAY` short so you don't have to wait a long time to start seeing the events (could also set it to 0 in this instance)
* Start `main.py` in race, qualifying or fp mode
* In another console, start `simulation_run.py`. Set the same mode here when prompted.
  * The simulation tool should now take you through a set of preset action to test "all functionalities" .

>[!NOTE]
> there are also some settings in the `simulation_run.py` tool such as `DELAY_SECONDS` which will set the speed of when it writes to the cache file.

>[!INFO]
> The order of the simulation is: Session start, Red Bull taking lead, Yellow flag out, yellow flag cleared, safety car out, safety car in, red flag out, track clear.

# Current Status

- Functions and is roughly stable in all F1 session types.
  - Very well tested for practice, not so well tested for races
- Works by itself in Qualifying (resetting between qualifying sessions)
- Handles events like Safety Cars and flags.
  - Resets itself when yellow or red flags are cleared from track
  - Resets itself when Safety car (or VSC) is deployed and ending
- Adjustable publishing delay now works (though very untested)
- Testing suites:
  - Unit tests for devs
  - End to End testing with a session simulator
- Most likely unstable and will fail when you need it the most, but I am working on making it better for every race 💖

## Plans going forward

- More testing, using it in as many sessions as I can! Testing is best way to improve this tool
- Make it more stable
- General code improvements (and make the code more testable)
- Make a "State Cache" so you can restart if there's a crash without having to start a "clean slate"

# Thank You!
A very special thanks to all of you who has downloaded this repo and tested it! I did not expect this amount of response, so this is awesome!
A special thanks to [@Winehorn](https://github.com/Winehorn) and [@Gtwizzy](https://github.com/Gtwizzy) for their insights and direct help and contribution

# Disclaimer
This is a personal, non-commercial project created for fun and educational purposes. It is not affiliated with, authorized by, endorsed by, or in any way officially connected with Formula 1, the FIA, or any of their affiliates.

All official Formula 1 content, trademarks, and intellectual property are the property of their respective owners. The data used by this project is sourced from the public FastF1 API and is intended for personal use in conjunction with a valid F1 subscription. This tool is not a replacement for any official F1 products or services.
