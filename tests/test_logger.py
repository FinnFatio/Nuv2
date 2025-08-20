import importlib
import json
import time
import logging

import logger


def reload_logger():
    importlib.reload(logger)
    logging.getLogger().handlers.clear()


def test_log_includes_sample_id(capsys):
    reload_logger()
    logger.setup(True)
    start = time.time()
    logger.log("stage1", start)
    logger.log("stage2", start)
    out = capsys.readouterr().err.strip().splitlines()
    data1 = json.loads(out[0])
    data2 = json.loads(out[1])
    assert data1["sample_id"] == data2["sample_id"]


def test_log_rate_limit(capsys):
    reload_logger()
    logger.setup(True, rate_limit_hz=1)
    start = time.time()
    logger.log("stage1", start)
    logger.log("stage2", start)
    out = capsys.readouterr().err.strip().splitlines()
    assert len(out) == 1
