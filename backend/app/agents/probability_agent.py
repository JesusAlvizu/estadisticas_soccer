"""ProbabilityAgent - IA para análisis de probabilidades."""
from dataclasses import dataclass
from typing import Optional, Dict
import numpy as np
from loguru import logger


@dataclass
class MatchAnalysis:
    """Result of match analysis."""

    match_id: int
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    confidence_level: float
    reasoning: str
    key_factors: Dict[str, float]


class ProbabilityAgent:
    """AI Agent for calculating probabilities."""

    # Weights for different factors
    WEIGHTS = {
        "team_form": 0.15,
        "head_to_head": 0.10,
        "home_away": 0.12,
        "goals_avg": 0.10,
        "xg_xga": 0.12,
        "injuries": 0.08,
        "possession": 0.08,
        "clean_sheets": 0.06,
        "recent_form": 0.12,
        "player_value": 0.05,
        "motivation": 0.04,
    }

    def __init__(self):
        """Initialize agent."""
        logger.info("Initializing ProbabilityAgent")

    async def analyze_match(
        self,
        match_id: int,
        home_team_stats: dict,
        away_team_stats: dict,
        home_injuries: list = None,
        away_injuries: list = None,
        historical_h2h: dict = None,
    ) -> MatchAnalysis:
        """Analyze a match and return probabilities."""
        logger.info(f"Analyzing match {match_id}")

        # Initialize injury factors
        home_injuries = home_injuries or []
        away_injuries = away_injuries or []

        # Calculate individual factors
        factors = self._calculate_factors(
            home_team_stats,
            away_team_stats,
            home_injuries,
            away_injuries,
            historical_h2h or {},
        )

        # Normalize and apply weights
        weighted_factors = self._apply_weights(factors)

        # Calculate probabilities
        probabilities = self._calculate_probabilities(weighted_factors)

        # Calculate confidence
        confidence = self._calculate_confidence(factors, probabilities)

        # Generate reasoning
        reasoning = self._generate_reasoning(factors, probabilities)

        logger.info(f"Match {match_id} analyzed: {probabilities}")

        return MatchAnalysis(
            match_id=match_id,
            home_win_probability=probabilities["home"],
            draw_probability=probabilities["draw"],
            away_win_probability=probabilities["away"],
            confidence_level=confidence,
            reasoning=reasoning,
            key_factors=factors,
        )

    def _calculate_factors(
        self, home_stats: dict, away_stats: dict, home_injuries: list, away_injuries: list, h2h: dict
    ) -> Dict[str, float]:
        """Calculate individual factors."""
        factors = {}

        # Team form (últimos 5 partidos)
        home_form = home_stats.get("win_rate", 0.5)
        away_form = away_stats.get("win_rate", 0.5)
        factors["team_form"] = (home_form - away_form + 1) / 2

        # Head to head
        if h2h and "home_wins" in h2h:
            total = h2h.get("total_matches", 1)
            h2h_factor = (
                (h2h.get("home_wins", 0) - h2h.get("away_wins", 0)) / total + 1
            ) / 2
            factors["head_to_head"] = h2h_factor
        else:
            factors["head_to_head"] = 0.5

        # Home advantage
        factors["home_away"] = 0.55  # Estadístico: 55% ventaja local

        # Goals average
        home_goals_avg = home_stats.get("avg_goals_for", 1.5)
        away_goals_avg = away_stats.get("avg_goals_for", 1.5)
        max_goals = max(home_goals_avg, away_goals_avg, 3.0)
        factors["goals_avg"] = home_goals_avg / max_goals

        # Expected goals
        home_xg = home_stats.get("avg_xg", 1.2)
        away_xg = away_stats.get("avg_xg", 1.2)
        max_xg = max(home_xg, away_xg, 2.0)
        factors["xg_xga"] = home_xg / max_xg

        # Injuries impact
        home_injury_impact = 1.0 - (len(home_injuries) * 0.05)
        away_injury_impact = 1.0 - (len(away_injuries) * 0.05)
        factors["injuries"] = (home_injury_impact - away_injury_impact + 1) / 2

        # Possession
        home_possession = home_stats.get("possession", 50.0)
        factors["possession"] = home_possession / 100.0

        # Clean sheets
        home_clean_sheets = home_stats.get("clean_sheets", 0)
        away_clean_sheets = away_stats.get("clean_sheets", 0)
        max_cs = max(home_clean_sheets, away_clean_sheets, 1)
        factors["clean_sheets"] = home_clean_sheets / max_cs

        # Recent form
        home_recent = home_stats.get("recent_form", 0.5)
        away_recent = away_stats.get("recent_form", 0.5)
        factors["recent_form"] = (home_recent - away_recent + 1) / 2

        # Player value
        home_value = home_stats.get("squad_market_value", 100)
        away_value = away_stats.get("squad_market_value", 100)
        max_value = max(home_value, away_value)
        factors["player_value"] = home_value / max_value

        # Motivation
        home_position = home_stats.get("position", 10)
        away_position = away_stats.get("position", 10)
        motivation_diff = (away_position - home_position) / 20.0  # Normalized
        factors["motivation"] = (motivation_diff + 1) / 2

        return factors

    def _apply_weights(self, factors: Dict[str, float]) -> Dict[str, float]:
        """Apply weights to factors."""
        weighted = {}
        total_weight = sum(self.WEIGHTS.values())

        for factor, value in factors.items():
            weight = self.WEIGHTS.get(factor, 0.0)
            weighted[factor] = (value * weight) / total_weight

        return weighted

    def _calculate_probabilities(self, weighted_factors: Dict[str, float]) -> dict:
        """Calculate final probabilities."""
        # Combine factors
        home_score = sum(weighted_factors.values())

        # Normalize to [0, 1]
        home_prob = max(0.0, min(1.0, home_score))

        # Draw probability (more likely when teams are similar)
        draw_margin = 1.0 - abs(2 * home_prob - 1.0)
        draw_prob = 0.25 * draw_margin

        # Distribute remaining probability
        remaining = 1.0 - draw_prob
        home_win = home_prob * remaining
        away_win = (1.0 - home_prob) * remaining

        # Normalize to sum to 1.0
        total = home_win + draw_prob + away_win
        if total > 0:
            home_win /= total
            draw_prob /= total
            away_win /= total

        return {"home": home_win, "draw": draw_prob, "away": away_win}

    def _calculate_confidence(self, factors: Dict[str, float], probabilities: dict) -> float:
        """Calculate confidence level."""
        # Confidence based on probability spread
        probs = sorted(
            [probabilities["home"], probabilities["draw"], probabilities["away"]]
        )
        spread = probs[2] - probs[0]

        # Confidence based on factor variance
        factor_values = list(factors.values())
        if factor_values:
            variance = np.var(factor_values)
            factor_confidence = 1.0 - (variance / 0.25)  # Normalized
        else:
            factor_confidence = 0.5

        confidence = (spread + factor_confidence) / 2.0
        return max(0.0, min(1.0, confidence))

    def _generate_reasoning(self, factors: Dict[str, float], probabilities: dict) -> str:
        """Generate reasoning for the analysis."""
        # Get top 3 factors
        sorted_factors = sorted(factors.items(), key=lambda x: abs(x[1] - 0.5), reverse=True)
        top_factors = sorted_factors[:3]

        reasoning = f"Analysis based on: "
        reasoning += ", ".join([f.format(name=k, value=v) for k, v in top_factors] for k, v in top_factors)

        # Add probability comment
        max_prob_type = max(probabilities.items(), key=lambda x: x[1])
        reasoning += f". Highest probability: {max_prob_type[0]} ({max_prob_type[1]:.1%})"

        return reasoning
