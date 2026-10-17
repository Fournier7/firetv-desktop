"""Executa trabalho fora da thread da interface e leva avisos de estado até ela."""
from __future__ import annotations

from typing import Callable, TypeVar

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

T = TypeVar("T")


class _Signals(QObject):
    done = Signal(object)
    error = Signal(object)
    finished = Signal()


# Mantém os sinais vivos até a entrega: se o QRunnable for destruído antes, os
# eventos já enfileirados se perdem e o callback nunca roda.
_ACTIVE: set[_Signals] = set()


class _Task(QRunnable):
    def __init__(self, fn: Callable[[], object], signals: _Signals) -> None:
        super().__init__()
        self._fn = fn
        self._signals = signals

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # o erro volta à interface, que decide a mensagem
            self._signals.error.emit(exc)
        else:
            self._signals.done.emit(result)
        finally:
            self._signals.finished.emit()


def run_in_background(
    fn: Callable[[], T],
    on_done: Callable[[T], None],
    on_error: Callable[[Exception], None],
) -> None:
    signals = _Signals()
    signals.done.connect(on_done)
    signals.error.connect(on_error)
    signals.finished.connect(lambda: _ACTIVE.discard(signals))
    _ACTIVE.add(signals)
    task = _Task(fn, signals)
    QThreadPool.globalInstance().start(task)


class SessionBridge(QObject):
    """Leva as mudanças de estado da Session (que podem vir de outra thread) à interface."""

    state_changed = Signal(object)

    def __init__(self, session) -> None:
        super().__init__()
        session.on_state_change = self.state_changed.emit


def get_bridge(session) -> SessionBridge:
    bridge = getattr(session, "_bridge", None)
    if bridge is None:
        bridge = SessionBridge(session)
        session._bridge = bridge
    return bridge
