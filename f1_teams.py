
def get_team_by_driver(driver_number_string: str) -> str:
    """Returns the team name based on driver number"""
    teams = {
        '1': "Red Bull", '22': "Red Bull",
        '16': "Ferrari", '44': "Ferrari",
        '12': "Mercedes", '63': "Mercedes",
        '4': "McLaren", '81': "McLaren",
        '14': "Aston Martin", '18': "Aston Martin",
        '10': "Alpine", '43': "Alpine",
        '6': "RB", '30': "RB",
        '31': "Haas", '87': "Haas",
        '5': "Sauber", '27': "Sauber",
        '55': "Williams", '23': "Williams"
    }
    
    return teams.get(driver_number_string, "Unknown")