from enum import Enum

class SkillLevel(Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"

class Player:
    def __init__(self, name, skill_level, amount_due=500, amount_paid=0):
        self.name = name
        self.skill_level = skill_level
        self.amount_due = amount_due
        self.amount_paid = amount_paid

    def get_name(self):
        return self.name

    def get_skill_level(self):
        return self.skill_level

    def get_balance(self):
        return self.amount_due - self.amount_paid

    def add_payment(self, amount):
        self.amount_paid += amount