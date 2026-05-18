import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging() -> logging.Logger:
    log_dir = Path.home() / "Library" / "Logs" / "podq"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "podq.log"

    logger = logging.getLogger("podq")
    logger.setLevel(logging.DEBUG)

    fh = RotatingFileHandler(log_path, maxBytes=5*1024*1024, backupCount=3)
    fh.setLevel(logging.DEBUG)

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger
