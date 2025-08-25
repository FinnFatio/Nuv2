from __future__ import annotations

import base64
import time
import zipfile

import metrics

from dispatcher import dispatch
from registry import clear, register_tool, register_alias
import tools


def setup_module(module):
    clear()
    tools.register_all_tools()


def test_fs_and_archive(tmp_path):
    clear()
    tools.register_all_tools()
    f = tmp_path / "hello.txt"
    f.write_text("hi")
    env = dispatch(
        {"name": "fs.read", "args": {"path": str(f), "allow": [str(tmp_path)]}},
        request_id="1",
    )
    assert env["kind"] == "ok" and env["result"] == "hi"
    env = dispatch(
        {"name": "fs.list", "args": {"path": str(tmp_path), "allow": [str(tmp_path)]}},
        request_id="2",
    )
    assert env["kind"] == "ok" and "hello.txt" in env["result"]

    env = dispatch(
        {
            "name": "fs.list",
            "args": {"path": str(tmp_path), "recursive": True, "allow": [str(tmp_path)]},
        },
        request_id="2b",
    )
    assert env["kind"] == "ok" and "hello.txt" in env["result"]

    zpath = tmp_path / "a.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("readme.txt", "zip hi")
    env = dispatch(
        {
            "name": "archive.read",
            "args": {
                "path": str(zpath),
                "inner_path": "readme.txt",
                "allow": [str(tmp_path)],
            },
        },
        request_id="3",
    )
    assert env["kind"] == "ok"
    data = base64.b64decode(env["result"]["bytes_b64"]).decode()
    assert data == "zip hi"


def test_web_read_blocked():
    clear()
    tools.register_all_tools()
    env = dispatch(
        {"name": "web.read", "args": {"url": "http://localhost"}}, request_id="4"
    )
    assert env["kind"] == "error"


def test_dispatcher_errors(tmp_path):
    clear()
    tools.register_all_tools()
    env = dispatch({"name": "missing", "args": {}}, request_id="5")
    assert env["code"] == "not_found"

    register_tool(
        name="danger",
        version="1",
        summary="",
        safety="rw",
        timeout_ms=1000,
        rate_limit_per_min=10,
        enabled_in_safe_mode=False,
        func=lambda: None,
    )
    env = dispatch({"name": "danger", "args": {}}, request_id="6", safe_mode=True)
    assert env["code"] == "forbidden"

    register_tool(
        name="limited",
        version="1",
        summary="",
        safety="ro",
        timeout_ms=1000,
        rate_limit_per_min=1,
        enabled_in_safe_mode=True,
        func=lambda: "ok",
    )
    env1 = dispatch({"name": "limited", "args": {}}, request_id="7")
    env2 = dispatch({"name": "limited", "args": {}}, request_id="8")
    assert env1["kind"] == "ok" and env2["code"] == "rate_limit"

    register_tool(
        name="slow",
        version="1",
        summary="",
        safety="ro",
        timeout_ms=10,
        rate_limit_per_min=10,
        enabled_in_safe_mode=True,
        func=lambda: time.sleep(0.05),
    )
    env = dispatch({"name": "slow", "args": {}}, request_id="9")
    assert env["code"] == "timeout" and "elapsed_ms" in env

    env = dispatch({"name": "fs.read", "args": {}}, request_id="10")
    assert env["code"] == "bad_args"


def test_rate_limit_records_metric():
    clear()
    metrics.reset()
    register_tool(
        name="limited_metric",
        version="1",
        summary="",
        safety="ro",
        timeout_ms=1000,
        rate_limit_per_min=1,
        enabled_in_safe_mode=True,
        func=lambda: "ok",
    )
    dispatch({"name": "limited_metric", "args": {}}, request_id="1")
    dispatch({"name": "limited_metric", "args": {}}, request_id="2")
    data = metrics.summary()
    assert data["status_total"]["limited_metric"]["rate_limited"] == 1


def test_registry_alias_dispatch():
    clear()
    called = []

    def fn():
        called.append(True)
        return "ok"

    register_tool(
        name="orig",
        version="1",
        summary="",
        safety="ro",
        timeout_ms=1000,
        rate_limit_per_min=10,
        enabled_in_safe_mode=True,
        func=fn,
    )
    register_alias("orig", "alias")
    env = dispatch({"name": "alias", "args": {}}, request_id="1")
    assert env["kind"] == "ok" and called
