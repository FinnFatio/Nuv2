import base64
import sys
import types

# stub sanitize deps
sys.modules["agent_local"] = types.SimpleNamespace(
    _redact=lambda x: x, _truncate=lambda x: x
)

from tools import ui, system, image  # noqa: E402
import ocr as ocr_module  # noqa: E402


def test_mouse_crop_ocr_pipeline(monkeypatch):
    # stub minimal PIL modules within test
    class Img:
        def crop(self, box):
            return self

        def save(self, buf, format="PNG"):
            buf.write(b"fake")

    fake_image_module = types.SimpleNamespace(open=lambda b: Img())
    monkeypatch.setitem(sys.modules, "PIL", types.SimpleNamespace(Image=fake_image_module))
    monkeypatch.setitem(sys.modules, "PIL.Image", fake_image_module)

    monkeypatch.setattr(
        ui,
        "what_under_mouse",
        lambda: {"kind": "ok", "result": {"x": 5, "y": 5, "window": None, "control": None}},
    )

    screenshot_b64 = base64.b64encode(b"fake").decode("ascii")
    monkeypatch.setattr(
        system,
        "capture_screen",
        lambda bounds=None: {"kind": "ok", "result": {"png_base64": screenshot_b64}},
    )

    monkeypatch.setattr(
        ocr_module, "extract_text", lambda img, region=None: ("hi", 1.0)
    )

    mouse = ui.what_under_mouse()
    shot = system.capture_screen()
    cropped = image.crop(
        png_base64=shot["result"]["png_base64"], x=0, y=0, w=1, h=1
    )
    assert cropped["kind"] == "ok"
    out = system.ocr(png_base64=cropped["result"]["png_base64"])
    assert out["kind"] == "ok"
    assert out["result"]["text"] == "hi"
