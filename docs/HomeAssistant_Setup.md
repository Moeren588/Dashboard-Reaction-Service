# Home Assistant Setup
This is a brief overlook of how I have set up the Home Assistant to listen to the MQTT Broker,
and from there control my lights.

## Mosquitto Broker Add-on
1. **Settings > Add-ons > Add-on store:** Search for 'MQTT' or 'Mosquitto Broker'
2. After it has been installed, go to the configuration tab, edit in YAML and enter your login
    credential (the ones that fit with your mqtt_config).
    ```yaml
    logins:
    - username: f1-service
        password: your_strong_password
    ```
3. Open the Home Assistant configuration.yaml file (I use the File Editor plugin for easy access),
    and add the MQTT topics as sensors. E.g:
    ```yaml
    mqtt:
        sensor:
            - name: "F1 MQTT Flag Status"
            state_topic: "f1/race/flag_status"
            # This template extracts the 'flag' value from the JSON payload
            value_template: "{{ value_json.flag }}"
            # This makes the full message available as an attribute
            json_attributes_topic: "f1/race/flag_status"
        
            - name: "F1 MQTT Leader Team"
            state_topic: "f1/race/leader"
            # This template extracts the 'team' value from the JSON payload
            value_template: "{{ value_json.team }}"
            json_attributes_topic: "f1/race/leader"
    ```
4. Restart your Home Assistant
5. **Settings > Devices & Services** Home Assistant should hopefully have discovered your "MQTT Device" that you can add.
    And you should see your two sensors as entities now. These are the ones you can listen to for your automation.

## Scripts
To avoid a lot of code repetition I use scripts to store the Team or Event effects and colors, these are the ones I call
in my automation setup.

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

## Automation
The automation setup is, when active, what actually drives the entire setup. It listens to the MQTT sensors,
then reacts accordingly when specific messages has been broadcasted. This is how part of my setup looks like:
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

>[!NOTE]
>   The `input_boolean.f1_mode` is a simple helper toggle so I can have an overall "on-off" switch
>   on my dashboard.

## Broadcasting
The time delay between when the python service receives messages, and when you see it on the broadcast
can be very hard to detect. That is why the service also listens in on channels that allows for adjustments
in the broadcasting delay. Currently it has two functions `calibrate start` and `Adjust`.

### Calibrate Start
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

### Adjust
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

button example
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
