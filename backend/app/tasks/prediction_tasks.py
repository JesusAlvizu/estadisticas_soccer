"""Prediction tasks."""
from celery import shared_task
from loguru import logger


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_predictions(self, match_id: int):
    """Generate predictions for a match."""
    try:
        logger.info(f"Generating predictions for match {match_id}...")
        # TODO: Implement prediction logic
        logger.info(f"Predictions generated for match {match_id}")
        return {"status": "success", "match_id": match_id}
    except Exception as exc:
        logger.error(f"Error generating predictions: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_monte_carlo_simulation(self, match_id: int, simulations: int = 5000):
    """Run Monte Carlo simulation for a match."""
    try:
        logger.info(f"Running {simulations} simulations for match {match_id}...")
        # TODO: Implement simulation logic
        logger.info(f"Simulations completed for match {match_id}")
        return {"status": "success", "match_id": match_id, "simulations": simulations}
    except Exception as exc:
        logger.error(f"Error running simulations: {exc}")
        raise self.retry(exc=exc)
