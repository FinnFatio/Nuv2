import api
import screenshot


def test_error_code_map_parity():
    assert api.ERROR_CODE_MAP == screenshot.ERROR_CODE_MAP
