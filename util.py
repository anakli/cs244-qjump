import subprocess
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

def check_pexec(node, cmd, *args, **kwargs):
    """Like subprocess.check_call, but for nodes."""
    out, err, exitcode = node.pexec(cmd, *args, **kwargs)
    if exitcode == 0:
        return
    print out
    print err
    raise subprocess.CalledProcessError("Command %r returned nonzero exit code %d" % (cmd, exitcode))
