import pytest

from fakes import FakeConnection
from firetv.connection import AuthRequiredError, ConnectionFailedError, ConnectionLostError
from firetv.controller import Controller
from firetv.session import POLL_INTERVAL_SECONDS, ConnectionState, Session

CMD = "dumpsys window | grep mCurrentFocus"
LINE = "mCurrentFocus=Window{abc u0 com.netflix.ninja/com.netflix.ninja.MainActivity}"


@pytest.fixture
def setup():
    conn = FakeConnection()
    conn.responses[CMD] = LINE
    sleeps: list[float] = []
    session = Session(lambda: conn, sleep=sleeps.append)
    return conn, session, sleeps


def test_poll_interval_is_three_seconds():
    assert POLL_INTERVAL_SECONDS == 3


def test_connect_sets_connected_and_exposes_controller(setup):
    conn, session, _ = setup
    assert session.state is ConnectionState.DISCONNECTED
    session.connect("192.168.0.10")
    assert session.state is ConnectionState.CONNECTED
    assert isinstance(session.controller, Controller)
    assert conn.host == "192.168.0.10"


def test_connect_propagates_auth_required(setup):
    conn, session, _ = setup
    conn.fail_connect = AuthRequiredError("x")
    with pytest.raises(AuthRequiredError):
        session.connect("192.168.0.10")
    assert session.state is ConnectionState.DISCONNECTED


def test_run_returns_op_result(setup):
    _, session, sleeps = setup
    session.connect("192.168.0.10")
    assert session.run(lambda c: c.current_app()) == "com.netflix.ninja"
    assert sleeps == []


def test_session_reconnects_after_drop(setup):
    conn, session, sleeps = setup
    session.connect("192.168.0.10")
    conn.drop_next = True
    assert session.run(lambda c: c.current_app()) == "com.netflix.ninja"
    assert session.state is ConnectionState.CONNECTED
    assert sleeps == [1]


def test_session_gives_up_after_three_failures(setup):
    conn, session, sleeps = setup
    session.connect("192.168.0.10")
    conn.drop_next = True
    conn.fail_connect = ConnectionFailedError("sem rota")
    with pytest.raises(ConnectionLostError):
        session.run(lambda c: c.current_app())
    assert session.state is ConnectionState.DISCONNECTED
    assert sleeps == [1, 2, 4]


def test_session_notifies_state_changes(setup):
    conn, session, _ = setup
    session.connect("192.168.0.10")
    seen = []
    session.on_state_change = seen.append
    conn.drop_next = True
    session.run(lambda c: c.current_app())
    assert seen == [ConnectionState.RECONNECTING, ConnectionState.CONNECTED]


def test_run_without_ever_connecting_raises_without_waiting(setup):
    _, session, sleeps = setup
    with pytest.raises(ConnectionLostError):
        session.run(lambda c: c.current_app())
    assert sleeps == [] and session.state is ConnectionState.DISCONNECTED


def test_run_serializes_concurrent_operations(setup):
    import threading
    import time

    _, session, _ = setup
    session.connect("192.168.0.10")
    active = 0
    overlaps = 0
    guard = threading.Lock()

    def op(_controller):
        nonlocal active, overlaps
        with guard:
            active += 1
            if active > 1:
                overlaps += 1
        time.sleep(0.05)
        with guard:
            active -= 1

    threads = [threading.Thread(target=session.run, args=(op,)) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert overlaps == 0
