import importlib
import json
import time

import logger


def reload_logger():
    importlib.reload(logger)
    logger.get_logger().handlers.clear()


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


def test_log_rate_limit_smoke(capsys):
    reload_logger()
    logger.setup(True, rate_limit_hz=5)
    start = time.time()
    for _ in range(5):
        logger.log("stage", start)
    out = capsys.readouterr().err.strip().splitlines()
    assert len(out) == 1
