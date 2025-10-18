"""Config File that holds across service Variables"""

# The cache text file that the FastF1 livetiming service
# Will write to, and the DRS will listen to.
CACHE_FILENAME = 'cache.txt'

# The delay between message received and even published to
# the MQTT Broker. This is because messages are received 
# x - seconds before you see them on the broadcast.
PUBLISH_DELAY = 54


# Used to determine if and how often DRS will save a session cache
# This is used in case the service crashes or fails and a restart
# is required. This will hopefully still keep the latest result of 
# interest.
SESSION_CACHING_ENABLED = True
SESSION_CACHING_INTERVAL = 10