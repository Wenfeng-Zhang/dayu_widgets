# -*- coding: utf-8 -*-
"""
Test utils.safe_disconnect.

PySide6 对「从未连接的信号」调用 disconnect 只发 RuntimeWarning（不抛异常），
PySide2/PyQt 则抛 RuntimeError / TypeError。safe_disconnect 需要同时兼容两种情况，
供「先 disconnect 防重、再 connect」的模式使用。
"""

# Import third-party modules
from Qt import QtWidgets

# Import local modules
from dayu_widgets import utils


def test_disconnect_unconnected_signal_does_not_raise(qtbot):
    """回归：未连接的信号直接 disconnect，在 PySide6 下会产生 RuntimeWarning。"""
    button = QtWidgets.QPushButton()
    utils.safe_disconnect(button.clicked)
    utils.safe_disconnect(button.clicked, lambda: None)


def test_disconnect_removes_existing_connection(qtbot):
    button = QtWidgets.QPushButton()
    calls = []
    slot = lambda: calls.append(1)  # noqa: E731

    button.clicked.connect(slot)
    button.click()
    assert len(calls) == 1

    utils.safe_disconnect(button.clicked, slot)
    button.click()
    assert len(calls) == 1, "断开后不应再触发"


def test_disconnect_is_idempotent(qtbot):
    """重复调用不应抛异常（防重逻辑会被反复执行）。"""
    button = QtWidgets.QPushButton()
    slot = lambda: None  # noqa: E731

    button.clicked.connect(slot)
    utils.safe_disconnect(button.clicked, slot)
    utils.safe_disconnect(button.clicked, slot)
