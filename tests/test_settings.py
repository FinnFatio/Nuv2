import json

import settings


def test_load_settings_priority_and_invalid(monkeypatch, tmp_path, capsys):
    (tmp_path / "config.json").write_text(
        json.dumps({
            "CAPTURE_WIDTH": 111,
            "CAPTURE_HEIGHT": 111,
            "CAPTURE_LOG_SAMPLE_RATE": 0.2,
        })
    )
    (tmp_path / ".env").write_text(
        "CAPTURE_WIDTH=222\nCAPTURE_HEIGHT=222\nCAPTURE_LOG_SAMPLE_RATE=0.3\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CAPTURE_WIDTH", "333")
    monkeypatch.setenv("CAPTURE_LOG_SAMPLE_RATE", "abc")

    cfg = settings.load_settings()

    assert cfg["CAPTURE_WIDTH"] == 333
    assert cfg["CAPTURE_HEIGHT"] == 222
    assert cfg["CAPTURE_LOG_SAMPLE_RATE"] == settings.DEFAULTS["CAPTURE_LOG_SAMPLE_RATE"]

    err = capsys.readouterr().err
    assert "Invalid CAPTURE_LOG_SAMPLE_RATE" in err


def test_version_stamp_in_config_digest(capsys):
    import importlib

    importlib.reload(settings)
    out = capsys.readouterr().err.strip()
    data = json.loads(out)
    assert "version_stamp" in data
    assert "python" in data["version_stamp"]
