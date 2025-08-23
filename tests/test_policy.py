from policy import Policy


def test_policy_conceptual_no_tool():
    pol = Policy()
    assert pol.plan("O que é entropia?") == []


def test_policy_recent_web():
    pol = Policy()
    assert pol.plan("preço do dólar hoje?") == ["web.read"]


def test_policy_explicit_tools():
    pol = Policy()
    msg = "Por favor, tire um screenshot e faça OCR"
    assert pol.plan(msg) == ["system.capture_screen", "system.ocr"]


def test_policy_system_info():
    pol = Policy()
    assert pol.plan("Qual é a info do sistema?") == ["system.info"]


def test_policy_destructive_block():
    pol = Policy()
    assert pol.plan("delete arquivo") == ["forbidden"]
