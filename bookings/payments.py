import os
from django.conf import settings
from .errors import PaymentFailed

# Global switch for testing / manual demos
_FORCE_PAYMENT_FAILURE = False


def set_force_payment_failure(flag: bool):
    global _FORCE_PAYMENT_FAILURE
    _FORCE_PAYMENT_FAILURE = bool(flag)


def charge(amount, force_fail=False):
    """
    Simulated payment charge.
    Raises PaymentFailed if force_fail or setting is set.
    Otherwise succeeds immediately.
    """
    should_fail = (
        force_fail
        or _FORCE_PAYMENT_FAILURE
        or getattr(settings, "SIMULATE_PAYMENT_FAILURE", False)
        or os.environ.get("SIMULATE_PAYMENT_FAILURE", "false").lower() == "true"
    )

    if should_fail:
        raise PaymentFailed()

    return {
        "status": "paid",
        "amount": f"{float(amount):.2f}",
        "simulated": True,
    }
