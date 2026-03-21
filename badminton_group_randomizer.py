import random
from team import Team
from group import Group

class BadmintonGroupRandomizer:
    @staticmethod
    def randomize_players(players):
        random.shuffle(players)
        groups = []
        group_num = 1
        
        # Process players in chunks of 4
        for i in range(0, len(players) - (len(players) % 4), 4):
            foursome = players[i:i+4]
            t1_players, t2_players = BadmintonGroupRandomizer.split_into_balanced_teams(foursome)
            
            groups.append(Group(
                group_num, 
                foursome, 
                Team(t1_players, "Team A"), 
                Team(t2_players, "Team B")
            ))
            group_num += 1
        return groups

    @staticmethod
    def split_into_balanced_teams(players):
        """Calculates the best 2v2 split to minimize skill difference."""
        def val(p):
            mapping = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}
            return mapping.get(p.get_skill_level().value, 1)

        best_split = ([players[0], players[1]], [players[2], players[3]])
        min_diff = float("inf")
        
        # Test the three possible 2v2 combinations
        combos = [
            ([players[0], players[1]], [players[2], players[3]]),
            ([players[0], players[2]], [players[1], players[3]]),
            ([players[0], players[3]], [players[1], players[2]])
        ]

        for t1, t2 in combos:
            diff = abs(sum(val(p) for p in t1) - sum(val(p) for p in t2))
            if diff < min_diff:
                min_diff = diff
                best_split = (t1, t2)
        return best_split