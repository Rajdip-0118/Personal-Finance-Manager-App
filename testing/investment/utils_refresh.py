from django.utils import timezone
from datetime import timedelta
from .utils import get_expected_return_by_type
import logging

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 3600 

def refresh_if_stale(investment, save=True):
    """
    Update expected_return if the last update is older than REFRESH_INTERVAL_SECONDS.
    Returns True if updated, False otherwise.
    """
    try:
        if getattr(investment, "status", "") == "Completed":
            return False

        now = timezone.now()

        last_updated = investment.last_updated or (now - timedelta(seconds=REFRESH_INTERVAL_SECONDS + 1))
        if timezone.is_naive(last_updated):
            last_updated = timezone.make_aware(last_updated, timezone.get_current_timezone())

        if last_updated < now - timedelta(seconds=REFRESH_INTERVAL_SECONDS):
            new_return = get_expected_return_by_type(investment.investment_type)
            if new_return is not None:
                investment.expected_return = new_return
                investment.last_updated = now
                if save:
                    investment.save(update_fields=["expected_return", "last_updated"])
                logger.info(
                    f"Refreshed expected return for {investment.name} ({investment.investment_type}) → {new_return}%"
                )
                return True
            else:
                logger.warning(f"Could not fetch new return for {investment.name} ({investment.investment_type})")
        return False

    except Exception as e:
        logger.error(f"refresh_if_stale() failed for {investment.name}: {e}")
        return False

