# DEBUGGING AND TEST LINES
This text file contains debugging lines you can past into the cache file you're listening to
for debugging and testing: Ensuring messages are picked up, queued, published, received and reacted
to accordingly.

## Fastest Lap Time (Free Practice Testing):
Lines going from slowest to fastest:

['TimingData', {'Lines': {'10': {'NumberOfLaps': 3, 'Sectors': {'2': {'Value': '24.386'}}, 'Speeds': {'FL': {'Value': '250'}}, 'BestLapTime': {'Value': '1:28.552', 'Lap': 2}, 'LastLapTime': {'Value': '1:28.552', 'OverallFastest': True, 'PersonalFastest': True}}}}, '2025-07-05T10:38:19.212Z']
['TimingData', {'Lines': {'1': {'NumberOfLaps': 3, 'Sectors': {'2': {'Value': '24.386'}}, 'Speeds': {'FL': {'Value': '250'}}, 'BestLapTime': {'Value': '1:28.552', 'Lap': 2}, 'LastLapTime': {'Value': '1:27.552', 'OverallFastest': True, 'PersonalFastest': True}}}}, '2025-07-05T10:38:19.212Z']
['TimingData', {'Lines': {'55': {'NumberOfLaps': 3, 'Sectors': {'2': {'Value': '24.386'}}, 'Speeds': {'FL': {'Value': '250'}}, 'BestLapTime': {'Value': '1:28.552', 'Lap': 2}, 'LastLapTime': {'Value': '1:26.552', 'OverallFastest': True, 'PersonalFastest': True}}}}, '2025-07-05T10:38:19.212Z']
['TimingData', {'Lines': {'4': {'NumberOfLaps': 3, 'Sectors': {'2': {'Value': '24.386'}}, 'Speeds': {'FL': {'Value': '250'}}, 'BestLapTime': {'Value': '1:28.552', 'Lap': 2}, 'LastLapTime': {'Value': '1:25.552', 'OverallFastest': True, 'PersonalFastest': True}}}}, '2025-07-05T10:38:19.212Z']


## Race Lead Change (Race):
Race change messages, does not matter in what order you test them.

['TopThree', {'Lines': {'0': {'RacingNumber': '4', 'Tla': 'NOR', 'BroadcastName': 'L NORRIS', 'FullName': 'Lando NORRIS', 'FirstName': 'Lando', 'LastName': 'Norris', 'Reference': 'LANNOR01', 'LapTime': '1:39.005', 'LapState': 64}, '1': {'RacingNumber': '81', 'Tla': 'PIA', 'BroadcastName': 'O PIASTRI', 'FullName': 'Oscar PIASTRI', 'FirstName': 'Oscar', 'LastName': 'Piastri', 'Reference': 'OSCPIA01', 'LapTime': '1:37.478', 'LapState': 80, 'DiffToAhead': '', 'DiffToLeader': ''}}}, '2025-07-06T15:27:00.924Z']
['TopThree', {'Lines': {'0': {'RacingNumber': '81', 'Tla': 'PIA', 'BroadcastName': 'O PIASTRI', 'FullName': 'Oscar PIASTRI', 'FirstName': 'Oscar', 'LastName': 'Piastri', 'Reference': 'OSCPIA01', 'Team': 'McLaren', 'TeamColour': 'F47600', 'LapTime': '2:43.087'}, '1': {'RacingNumber': '1', 'Tla': 'VER', 'BroadcastName': 'M VERSTAPPEN', 'FullName': 'Max VERSTAPPEN', 'FirstName': 'Max', 'LastName': 'Verstappen', 'Reference': 'MAXVER01', 'Team': 'Red Bull Racing', 'TeamColour': '4781D7', 'LapTime': '2:42.616', 'DiffToAhead': '', 'DiffToLeader': ''}}}, '2025-07-06T14:49:19.685Z']
['TopThree', {'Lines': {'0': {'RacingNumber': '1', 'Tla': 'VER', 'BroadcastName': 'M VERSTAPPEN', 'FullName': 'Max VERSTAPPEN', 'FirstName': 'Max', 'LastName': 'Verstappen', 'Reference': 'MAXVER01', 'Team': 'Red Bull Racing', 'TeamColour': '4781D7', 'LapTime': '2:42.616'}, '1': {'RacingNumber': '81', 'Tla': 'PIA', 'BroadcastName': 'O PIASTRI', 'FullName': 'Oscar PIASTRI', 'FirstName': 'Oscar', 'LastName': 'Piastri', 'Reference': 'OSCPIA01', 'Team': 'McLaren', 'TeamColour': 'F47600', 'LapTime': '2:43.087', 'DiffToAhead': '', 'DiffToLeader': ''}}}, '2025-07-06T14:49:09.888Z']


## Race Control Flag Messages:

### YELLOW FLAGS
Note their sectors when pairing with CLEAR flags

['RaceControlMessages', {'Messages': {'56': {'Utc': '2025-07-05T11:39:56', 'Category': 'Flag', 'Flag': 'YELLOW', 'Scope': 'Sector', 'Sector': 2, 'Message': 'YELLOW IN TRACK SECTOR 2'}}}, '2025-07-05T11:39:56.262Z']
['RaceControlMessages', {'Messages': {'4': {'Utc': '2025-07-04T15:16:09', 'Category': 'Flag', 'Flag': 'DOUBLE YELLOW', 'Scope': 'Sector', 'Sector': 8, 'Message': 'DOUBLE YELLOW IN TRACK SECTOR 8'}}}, '2025-07-04T15:16:09.257Z']

### CLEAR FLAGS
Used for clearing sectors for yellow flags (they never show a GREEN flag)
['RaceControlMessages', {'Messages': {'13': {'Utc': '2025-09-06T14:22:44', 'Category': 'Flag', 'Flag': 'CLEAR', 'Scope': 'Sector', 'Sector': 8, 'Message': 'CLEAR IN TRACK SECTOR 8'}}}, '2025-09-06T14:22:43.772Z']
['RaceControlMessages', {'Messages': {'13': {'Utc': '2025-09-06T14:22:44', 'Category': 'Flag', 'Flag': 'CLEAR', 'Scope': 'Sector', 'Sector': 2, 'Message': 'CLEAR IN TRACK SECTOR 8'}}}, '2025-09-06T14:22:43.772Z']

### RED Flag
['RaceControlMessages', {'Messages': {'50': {'Utc': '2025-07-05T11:33:58', 'Category': 'Flag', 'Flag': 'RED', 'Scope': 'Track', 'Message': 'RED FLAG'}}}, '2025-07-05T11:33:58.102Z']
['RaceControlMessages', {'Messages': {'14': {'Utc': '2025-07-05T14:27:49', 'Category': 'Flag', 'Flag': 'CHEQUERED', 'Scope': 'Track', 'Message': 'CHEQUERED FLAG'}}}, '2025-07-05T14:27:49.153Z']

### VIRTUAL SAFETY CAR
Deployed and Ending

['RaceControlMessages', {'Messages': {'67': {'Utc': '2025-07-06T14:05:48', 'Lap': 2, 'Category': 'SafetyCar', 'Status': 'DEPLOYED', 'Mode': 'VIRTUAL SAFETY CAR', 'Message': 'VIRTUAL SAFETY CAR DEPLOYED'}}}, '2025-07-06T14:05:47.647Z']
['RaceControlMessages', {'Messages': {'72': {'Utc': '2025-07-06T14:10:18', 'Lap': 4, 'Category': 'SafetyCar', 'Status': 'ENDING', 'Mode': 'VIRTUAL SAFETY CAR', 'Message': 'VIRTUAL SAFETY CAR ENDING'}}}, '2025-07-06T14:10:17.861Z']

### FULL SAFETY CAR
Deployed and In this Lap
['RaceControlMessages', {'Messages': {'97': {'Utc': '2025-07-06T14:29:14', 'Lap': 14, 'Category': 'SafetyCar', 'Status': 'DEPLOYED', 'Mode': 'SAFETY CAR', 'Message': 'SAFETY CAR DEPLOYED'}}}, '2025-07-06T14:29:14.267Z']
['RaceControlMessages', {'Messages': {'99': {'Utc': '2025-07-06T14:38:36', 'Lap': 17, 'Category': 'SafetyCar', 'Status': 'IN THIS LAP', 'Mode': 'SAFETY CAR', 'Message': 'SAFETY CAR IN THIS LAP'}}}, '2025-07-06T14:38:36.526Z']

## Session Status Messages

### START or RESUME from stopped session
['SessionData', {'StatusSeries': {'4': {'Utc': '2025-09-07T13:03:34.805Z', 'SessionStatus': 'Started'}}}, '2025-09-07T13:03:34.805Z']

### END of session
['SessionData', {'StatusSeries': {'81': {'Utc': '2025-09-20T14:09:07.724Z', 'SessionStatus': 'Ends'}}}, '2025-09-20T14:09:07.724Z']

