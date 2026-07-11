"""Betting analysis and value calculation."""
from dataclasses import dataclass
from typing import Optional
from loguru import logger


@dataclass
class BettingAnalysis:
    """Betting analysis result."""

    market: str
    outcome: str
    odds: float
    predicted_probability: float
    implied_probability: float
    expected_value: float
    expected_value_percentage: float
    roi: float
    kelly_percentage: float
    recommended_stake_percentage: float
    confidence_level: float
    recommendation: str
    value_found: bool


class BettingAnalyzer:
    """Analyzes betting opportunities."""

    # Kelly fraction (usually 1/4 or 1/2 of full Kelly for safety)
    KELLY_FRACTION = 0.25

    def __init__(self, bankroll: float = 1000.0):
        """Initialize betting analyzer.
        
        Args:
            bankroll: Total bankroll for Kelly calculation
        """
        self.bankroll = bankroll
        logger.info(f"Initializing BettingAnalyzer with bankroll: {bankroll}")

    def analyze_bet(
        self,
        market: str,
        outcome: str,
        odds: float,
        predicted_probability: float,
        confidence_level: float = 0.5,
    ) -> BettingAnalysis:
        """Analyze a single bet.
        
        Args:
            market: Betting market (e.g., 'match_winner', 'over_under_2_5')
            outcome: Predicted outcome
            odds: Decimal odds offered by bookmaker
            predicted_probability: Our predicted probability (0-1)
            confidence_level: Confidence in prediction (0-1)
        """
        logger.info(
            f"Analyzing bet: {market} -> {outcome} at odds {odds:.2f}"
        )

        # Calculate implied probability from odds
        implied_probability = 1.0 / odds

        # Calculate expected value
        ev = (predicted_probability * odds) - 1.0
        ev_percentage = ev * 100

        # Calculate ROI
        roi = ev * 100 if ev > 0 else 0

        # Calculate Kelly Criterion
        kelly_percentage = self._calculate_kelly(
            predicted_probability, odds
        )

        # Apply Kelly fraction for safer betting
        recommended_stake = kelly_percentage * self.KELLY_FRACTION

        # Determine if value exists
        value_found = ev > 0.01  # At least 1% edge

        # Generate recommendation
        recommendation = self._generate_recommendation(
            ev, kelly_percentage, confidence_level, value_found
        )

        logger.info(f"Analysis complete: EV={ev_percentage:.2f}%, Kelly={kelly_percentage:.1%}")

        return BettingAnalysis(
            market=market,
            outcome=outcome,
            odds=odds,
            predicted_probability=predicted_probability,
            implied_probability=implied_probability,
            expected_value=ev,
            expected_value_percentage=ev_percentage,
            roi=roi,
            kelly_percentage=kelly_percentage,
            recommended_stake_percentage=recommended_stake,
            confidence_level=confidence_level,
            recommendation=recommendation,
            value_found=value_found,
        )

    def _calculate_kelly(self, probability: float, odds: float) -> float:
        """Calculate Kelly Criterion percentage.
        
        Kelly = (b*p - q) / b
        where:
            b = odds - 1 (decimal odds - 1)
            p = probability of winning
            q = probability of losing (1 - p)
        """
        if probability <= 0 or probability >= 1:
            return 0.0

        b = odds - 1.0
        p = probability
        q = 1.0 - p

        kelly = (b * p - q) / b

        # Ensure Kelly is positive and reasonable
        return max(0.0, min(1.0, kelly))

    def _generate_recommendation(
        self,
        ev: float,
        kelly_percentage: float,
        confidence_level: float,
        value_found: bool,
    ) -> str:
        """Generate betting recommendation."""
        if not value_found:
            return "❌ NO BET - No value found (negative EV)"

        if confidence_level < 0.5:
            return "⚠️ AVOID - Low confidence level"

        if kelly_percentage < 0.02:
            return "⚠️ SMALL - Very small edge, use caution"

        if kelly_percentage < 0.05:
            return "✓ SMALL VALUE - Small positive EV, consider betting"

        if kelly_percentage < 0.10:
            return "✓ GOOD VALUE - Good EV, recommended"

        return "🔥 STRONG VALUE - Strong EV with good confidence, high recommendation"

    def compare_bookmakers(
        self,
        market: str,
        outcome: str,
        predicted_probability: float,
        bookmaker_odds: dict,
    ) -> dict:
        """Compare odds across multiple bookmakers.
        
        Args:
            market: Betting market
            outcome: Predicted outcome
            predicted_probability: Our predicted probability
            bookmaker_odds: Dict of {bookmaker_name: odds}
        """
        logger.info(
            f"Comparing {len(bookmaker_odds)} bookmakers for {market}"
        )

        analyses = {}
        best_bet = None
        best_ev = -1.0

        for bookmaker, odds in bookmaker_odds.items():
            analysis = self.analyze_bet(
                market, outcome, odds, predicted_probability
            )
            analyses[bookmaker] = analysis

            if analysis.expected_value > best_ev:
                best_ev = analysis.expected_value
                best_bet = bookmaker

        return {
            "analyses": analyses,
            "best_bookmaker": best_bet,
            "best_analysis": analyses.get(best_bet),
            "spread": max(bookmaker_odds.values()) - min(bookmaker_odds.values()),
        }

    def calculate_parlay(self, odds_list: list, probabilities: list) -> dict:
        """Calculate parlay (multiple bets combined).
        
        Args:
            odds_list: List of decimal odds
            probabilities: List of probabilities for each leg
        """
        logger.info(f"Calculating parlay with {len(odds_list)} legs")

        parlay_odds = 1.0
        parlay_probability = 1.0

        for odds in odds_list:
            parlay_odds *= odds

        for prob in probabilities:
            parlay_probability *= prob

        ev = (parlay_probability * parlay_odds) - 1.0

        return {
            "parlay_odds": parlay_odds,
            "parlay_probability": parlay_probability,
            "expected_value": ev,
            "ev_percentage": ev * 100,
            "recommended": ev > 0.02,
        }
