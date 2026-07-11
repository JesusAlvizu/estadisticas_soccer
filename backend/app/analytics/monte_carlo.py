"""Monte Carlo Simulator for match predictions."""
import numpy as np
from dataclasses import dataclass
from typing import Optional
from loguru import logger


@dataclass
class SimulationResult:
    """Monte Carlo simulation results."""

    simulations: int
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    most_likely_score: str
    average_goals: float
    over_2_5_probability: float
    over_1_5_probability: float
    over_3_5_probability: float
    both_teams_score_probability: float
    home_clean_sheet_probability: float
    away_clean_sheet_probability: float
    score_distribution: dict


class MonteCarlo:
    """Monte Carlo simulator for match predictions."""

    def __init__(
        self,
        home_team_stats: dict,
        away_team_stats: dict,
        simulations: int = 5000,
    ):
        """Initialize simulator.
        
        Args:
            home_team_stats: Home team statistics
            away_team_stats: Away team statistics
            simulations: Number of simulations to run (1000-10000)
        """
        self.home_stats = home_team_stats
        self.away_stats = away_team_stats
        self.simulations = max(1000, min(10000, simulations))
        
        logger.info(
            f"Initializing Monte Carlo with {self.simulations} simulations"
        )

    def run(self) -> SimulationResult:
        """Run Monte Carlo simulations."""
        logger.info("Running Monte Carlo simulations...")
        
        # Extract lambda values (average goals)
        home_lambda = self.home_stats.get("goals_per_match", 1.5)
        away_lambda = self.away_stats.get("goals_per_match", 1.2)
        
        # Adjust based on expected goals if available
        if "expected_goals" in self.home_stats:
            home_lambda = self.home_stats["expected_goals"]
        if "expected_goals" in self.away_stats:
            away_lambda = self.away_stats["expected_goals"]

        # Run simulations using Poisson distribution
        home_goals_distribution = np.random.poisson(
            home_lambda, self.simulations
        )
        away_goals_distribution = np.random.poisson(
            away_lambda, self.simulations
        )

        # Calculate outcomes
        home_wins = np.sum(home_goals_distribution > away_goals_distribution)
        draws = np.sum(home_goals_distribution == away_goals_distribution)
        away_wins = np.sum(home_goals_distribution < away_goals_distribution)

        # Calculate probabilities
        home_win_prob = home_wins / self.simulations
        draw_prob = draws / self.simulations
        away_win_prob = away_wins / self.simulations

        # Calculate goals statistics
        total_goals = home_goals_distribution + away_goals_distribution
        average_goals = np.mean(total_goals)
        
        over_2_5 = np.sum(total_goals > 2.5) / self.simulations
        over_1_5 = np.sum(total_goals > 1.5) / self.simulations
        over_3_5 = np.sum(total_goals > 3.5) / self.simulations
        
        # Both teams score
        both_score = np.sum(
            (home_goals_distribution > 0) & (away_goals_distribution > 0)
        ) / self.simulations
        
        # Clean sheets
        home_clean_sheet = np.sum(away_goals_distribution == 0) / self.simulations
        away_clean_sheet = np.sum(home_goals_distribution == 0) / self.simulations

        # Most likely score
        score_distribution = {}
        for h_goals, a_goals in zip(home_goals_distribution, away_goals_distribution):
            score_key = f"{h_goals}-{a_goals}"
            score_distribution[score_key] = score_distribution.get(score_key, 0) + 1

        # Get top 5 scores
        top_scores = sorted(
            score_distribution.items(), key=lambda x: x[1], reverse=True
        )[:5]
        most_likely_score = top_scores[0][0] if top_scores else "1-1"

        logger.info(f"Simulations completed: {self.simulations}")
        logger.info(
            f"Results - Home: {home_win_prob:.1%}, Draw: {draw_prob:.1%}, Away: {away_win_prob:.1%}"
        )

        return SimulationResult(
            simulations=self.simulations,
            home_win_probability=home_win_prob,
            draw_probability=draw_prob,
            away_win_probability=away_win_prob,
            most_likely_score=most_likely_score,
            average_goals=float(average_goals),
            over_2_5_probability=over_2_5,
            over_1_5_probability=over_1_5,
            over_3_5_probability=over_3_5,
            both_teams_score_probability=both_score,
            home_clean_sheet_probability=home_clean_sheet,
            away_clean_sheet_probability=away_clean_sheet,
            score_distribution=dict(top_scores),
        )
