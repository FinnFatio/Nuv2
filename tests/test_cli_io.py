import json
import os
import subprocess
import sys


def test_screenshot_stdout_stderr_separation(tmp_path):
    out = tmp_path / "out.png"
    script = f'''
import sys, screenshot
class DummyImg:
    def save(self, path):
        pass

def fake_capture(region):
    screenshot._log_sampled({{"stage":"test"}})
    return DummyImg()

screenshot.capture = fake_capture
sys.argv = ["screenshot.py", "--json", "--region", "0,0,1,1", "{out}"]
screenshot.main()
'''
    env = os.environ.copy()
    env["CAPTURE_LOG_SAMPLE_RATE"] = "1"
    env["CAPTURE_LOG_DEST"] = "stderr"
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"output": str(out), "region": [0, 0, 1, 1]}
    assert '"stage": "test"' in result.stderr

