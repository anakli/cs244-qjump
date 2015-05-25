import logging
logger = logging.getLogger(__name__)

def kill_safe(process):
    try:
        process.kill()
    except OSError as e:
        if getattr(e, "errno", None) == 3:
            logger.info("Tried to kill %r, no such process" % process)
        else:
            raise
