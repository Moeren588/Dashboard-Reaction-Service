"""Config File that holds across service Variables"""

# The cache text file that the FastF1 livetiming service
# Will write to, and the other services in this tool will
# listen to.
CACHE_FILENAME = 'livetiming_cache.txt'

# The delay between message received and even published to
# the MQTT Broker. This is because messages are received 
# x - seconds before you see them on the broadcast.
# Default of 30s fits for the F1TV Broadcast we receive.
PUBLISH_DELAY = 30 # Seconds