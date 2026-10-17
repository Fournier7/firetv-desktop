import pytest
from adb_shell.exceptions import DeviceAuthError, TcpTimeoutException

from fakes import FakeConnection
from firetv import connection
from firetv.connection import (
    AdbConnection,
    AuthRequiredError,
    ConnectionFailedError,
    ConnectionLostError,
    FireTvError,
)


def make_device_class(connect_exc=None, shell_exc=None, output="ok"):
    class FakeDevice:
        instances = []

        def __init__(self, host, port=5555, **kwargs):
            self.host, self.port = host, port
            self.available = False
            self.closed = False
            FakeDevice.instances.append(self)

        def connect(self, rsa_keys=None, auth_timeout_s=10.0, **kwargs):
            if connect_exc:
                raise connect_exc
            self.rsa_keys = rsa_keys
            self.auth_timeout_s = auth_timeout_s
            self.available = True

        def shell(self, command, **kwargs):
            if shell_exc:
                raise shell_exc
            return output

        def close(self):
            self.closed = True
            self.available = False

    return FakeDevice


@pytest.fixture(autouse=True)
def appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_fake_records_commands():
    c = FakeConnection()
    c.connect("1.2.3.4")
    c.shell("echo oi")
    assert c.commands == ["echo oi"]


def test_errors_share_a_base_class():
    for exc in (ConnectionFailedError, AuthRequiredError, ConnectionLostError):
        assert issubclass(exc, FireTvError)


def test_adb_timeout_maps_to_connection_failed(monkeypatch):
    monkeypatch.setattr(connection, "AdbDeviceTcp", make_device_class(connect_exc=TcpTimeoutException()))
    with pytest.raises(ConnectionFailedError):
        AdbConnection().connect("192.168.0.10")


def test_adb_oserror_maps_to_connection_failed(monkeypatch):
    monkeypatch.setattr(connection, "AdbDeviceTcp", make_device_class(connect_exc=OSError("rede")))
    with pytest.raises(ConnectionFailedError):
        AdbConnection().connect("192.168.0.10")


def test_adb_auth_error_maps_to_auth_required(monkeypatch):
    monkeypatch.setattr(connection, "AdbDeviceTcp", make_device_class(connect_exc=DeviceAuthError("x")))
    with pytest.raises(AuthRequiredError):
        AdbConnection().connect("192.168.0.10")


def test_connect_creates_key_in_config_dir_and_runs_shell(monkeypatch, appdata):
    cls = make_device_class(output="resposta")
    monkeypatch.setattr(connection, "AdbDeviceTcp", cls)
    c = AdbConnection()
    c.connect("192.168.0.10")
    assert c.is_connected()
    assert (appdata / "firetv-desktop" / "adbkey").exists()
    assert cls.instances[0].host == "192.168.0.10" and cls.instances[0].port == 5555
    assert c.shell("ls") == "resposta"


def test_shell_when_not_connected_raises_connection_lost():
    with pytest.raises(ConnectionLostError):
        AdbConnection().shell("ls")


def test_shell_socket_error_raises_connection_lost_and_disconnects(monkeypatch):
    monkeypatch.setattr(connection, "AdbDeviceTcp", make_device_class(shell_exc=BrokenPipeError()))
    c = AdbConnection()
    c.connect("192.168.0.10")
    with pytest.raises(ConnectionLostError):
        c.shell("ls")
    assert not c.is_connected()


def test_disconnect_closes_device(monkeypatch):
    cls = make_device_class()
    monkeypatch.setattr(connection, "AdbDeviceTcp", cls)
    c = AdbConnection()
    c.connect("192.168.0.10")
    c.disconnect()
    assert cls.instances[0].closed and not c.is_connected()


def test_connect_gives_time_to_accept_the_authorization_prompt(monkeypatch):
    cls = make_device_class()
    monkeypatch.setattr(connection, "AdbDeviceTcp", cls)
    AdbConnection().connect("192.168.0.10")
    assert cls.instances[0].auth_timeout_s == 30.0
