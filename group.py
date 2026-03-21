import random
from player import Player, SkillLevel
from team import Team

class Group:
    def __init__(self, group_number, players, team1=None, team2=None):
        self.group_number = group_number
        self.players = players
        self.team1 = team1
        self.team2 = team2

    def get_group_number(self):
        return self.group_number

    def get_players(self):
        return self.players

    def get_team1(self):
        return self.team1

    def get_team2(self):
        return self.team2