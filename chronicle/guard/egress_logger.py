"""External request audit logging."""

import logging

logger = logging.getLogger(__name__)


def log_egress(provider: str, *, redacted: bool) -> None:
    logger.info("egress provider=%s redacted=%s", provider, redacted)
