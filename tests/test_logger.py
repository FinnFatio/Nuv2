
import importlib
import json
import time

import logger


def reload_logger():
    importlib.reload(logger)
    logger.get_logger().handlers.clear()


def test_log_includes_sample_id(capsys):
    reload_logger()
    logger.setup(enable=True, jsonl=True)
    start = time.time()
    logger.log("stage1", start)
    logger.log("stage2", start)
    out = capsys.readouterr().err.strip().splitlines()
    data1 = json.loads(out[0])
    data2 = json.loads(out[1])
    assert data1["sample_id"] == data2["sample_id"]


def test_log_rate_limit(capsys):
    reload_logger()
    logger.setup(enable=True, jsonl=True, rate_limit_hz=1)
    start = time.time()
    logger.log("stage1", start)
    logger.log("stage2", start)
    out = capsys.readouterr().err.strip().splitlines()
    assert len(out) == 1


def test_log_rate_limit_smoke(capsys):
    reload_logger()
    logger.setup(enable=True, jsonl=True, rate_limit_hz=5)
    start = time.time()
    for _ in range(5):
        logger.log("stage", start)
    out = capsys.readouterr().err.strip().splitlines()
    assert len(out) == 1


def test_log_level_filter(capsys):
    reload_logger()
    logger.setup(level="WARNING", jsonl=True)
    logger.get_logger().info("info")
    logger.get_logger().warning("warn")
    out = capsys.readouterr().err.strip().splitlines()
    assert len(out) == 1
    assert json.loads(out[0])["message"] == "warn"


def test_json_format(capsys):
    reload_logger()
    logger.setup(level="INFO", jsonl=True)
    logger.get_logger().info("hello")
    out = capsys.readouterr().err.strip()
    data = json.loads(out)
    assert data["message"] == "hello"
    assert data["level"] == "INFO"


def test_rate_limit_reset(capsys):
    reload_logger()
    logger.setup(enable=True, jsonl=True, rate_limit_hz=5)
    start = time.time()
    for _ in range(5):
        logger.log("stage", start)
    logger._LAST_LOG_TIME = 0.0
    for _ in range(5):
        logger.log("stage", start)
    out = capsys.readouterr().err.strip().splitlines()
    assert len(out) == 2
