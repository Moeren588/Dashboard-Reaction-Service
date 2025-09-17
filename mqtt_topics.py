from enum import Enum

class MqttTopics(str, Enum):
    """Enumeration for all MQTT topics used in the application"""

    def __str__(self) -> str:
        return self.value
    
    # BROADCASTING
    ## Race related
    LEADER_TOPIC = "f1/race/leader"
    FLAG_TOPIC = "f1/race/flag_status"
    ## Service related
    RUNNING_STATUS_TOPIC = "f1/service/running_status"
    PUBLISHING_DELAY_TOPIC = "f1/service/publishing_delay"

    # LISTENING
    CONTROL_TOPIC = "f1/service/control"
