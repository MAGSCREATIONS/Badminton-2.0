class Team:
    def __init__(self, players, name="Team"):
        self.players = players
        self.name = name

    def get_players(self):
        return self.players

    def get_name(self):
        return self.name