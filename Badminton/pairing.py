"""
pairing.py
----------
History-aware court grouping for doubles.

Each player's strength is their smoothed win rate, starting from a prior set
by their roster skill level. Partner pairs carry a record too. The search
draws many random groupings and keeps the one with the lowest cost for the
chosen mode:

  develop  -- put stronger and weaker players together so weaker players
              improve, while keeping the two teams evenly matched.
  spread   -- keep the strongest players apart: no two of them on the same
              team or the same court, so no single court dominates.

Both modes still shuffle, and repeat partnerships are only discouraged, not
banned, so any pair can still be drawn together occasionally.
"""
import random

PRIOR_WEIGHT = 5           # how many games' worth of weight the skill prior gets
PRIOR_STRENGTH = {"Beginner": 0.40, "Intermediate": 0.50, "Advanced": 0.60}
TRIALS = 2000              # random groupings sampled per request
FAIRNESS_COST = 4.0        # penalty per point of team-strength gap
REPEAT_COST = 0.3          # penalty per earlier time two players partnered (low, so repeats still happen now and then)
SYNERGY_COST = 2.0         # extra penalty for a pair that already wins a lot together
DEVELOP_REWARD = 1.5       # bonus for a strong+weak combination within a team
SPREAD_COST = 2.0          # penalty for strong players sharing a team or court
MODES = ("develop", "spread")


def _smoothed(wins: int, played: int, prior: float) -> float:
    return (wins + prior * PRIOR_WEIGHT) / (played + PRIOR_WEIGHT)


class _Context:
    def __init__(self, present, skills, games, mode):
        self.mode = mode
        self.player_wins = {}
        self.player_played = {}
        self.pair_wins = {}
        self.pair_played = {}

        for g in games:
            for team, won in ((g["team1"], g["winner"] == 1), (g["team2"], g["winner"] == 2)):
                for name in team:
                    self.player_played[name] = self.player_played.get(name, 0) + 1
                    if won:
                        self.player_wins[name] = self.player_wins.get(name, 0) + 1
                key = frozenset(team)
                self.pair_played[key] = self.pair_played.get(key, 0) + 1
                if won:
                    self.pair_wins[key] = self.pair_wins.get(key, 0) + 1

        self.strength = {}
        for name in present:
            prior = PRIOR_STRENGTH.get(skills.get(name), 0.5)
            self.strength[name] = _smoothed(
                self.player_wins.get(name, 0), self.player_played.get(name, 0), prior
            )

        # Top quarter of the present players count as "strong" for spread mode.
        ranked = sorted(present, key=lambda n: self.strength[n], reverse=True)
        strong_count = max(1, len(present) // 4)
        self.strong = set(ranked[:strong_count])

    def pair_rate(self, a, b) -> float:
        key = frozenset((a, b))
        return _smoothed(self.pair_wins.get(key, 0), self.pair_played.get(key, 0), 0.5)

    def team_cost(self, a, b) -> float:
        key = frozenset((a, b))
        cost = REPEAT_COST * self.pair_played.get(key, 0)
        cost += SYNERGY_COST * max(0.0, self.pair_rate(a, b) - 0.5)
        gap = abs(self.strength[a] - self.strength[b])
        if self.mode == "develop":
            cost -= DEVELOP_REWARD * gap
        elif self.mode == "spread" and a in self.strong and b in self.strong:
            cost += SPREAD_COST
        return cost


def _best_split(four, ctx):
    """Cheapest way to split four players into two teams of two."""
    a, b, c, d = four
    options = (((a, b), (c, d)), ((a, c), (b, d)), ((a, d), (b, c)))
    best = None
    for t1, t2 in options:
        cost = FAIRNESS_COST * abs(
            sum(ctx.strength[p] for p in t1) - sum(ctx.strength[p] for p in t2)
        )
        cost += ctx.team_cost(*t1) + ctx.team_cost(*t2)
        if best is None or cost < best[0]:
            best = (cost, list(t1), list(t2))

    if ctx.mode == "spread":
        strong_on_court = sum(1 for p in four if p in ctx.strong)
        best = (best[0] + SPREAD_COST * max(0, strong_on_court - 1), best[1], best[2])
    return best


def build_history_groups(present_names, skills, games, mode, rng=random):
    """
    Returns a list of (team1, team2) tuples, one per court.

    present_names: names checked in as present (must be on the roster).
    skills:        {name: "Beginner" | "Intermediate" | "Advanced"}.
    games:         list of game dicts from games_db.get_all_games().
    mode:          "develop" or "spread".
    """
    if mode not in MODES:
        raise ValueError(f"Unknown grouping mode '{mode}'.")

    present = [n for n in dict.fromkeys(present_names) if n in skills]
    if len(present) < 4:
        raise ValueError("Need at least 4 present players.")

    ctx = _Context(present, skills, games, mode)
    usable = len(present) - (len(present) % 4)

    best_cost, best_courts = None, None
    for _ in range(TRIALS):
        order = present[:]
        rng.shuffle(order)
        total = 0.0
        courts = []
        for i in range(0, usable, 4):
            cost, t1, t2 = _best_split(order[i:i + 4], ctx)
            total += cost
            courts.append((t1, t2))
        if best_cost is None or total < best_cost:
            best_cost, best_courts = total, courts

    return best_courts
