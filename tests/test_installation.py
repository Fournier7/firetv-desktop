from pathlib import Path

import pytest

from firetv.installation import install_payload, shell_script, uninstall_script


def test_install_places_app_in_target_and_preserves_unrelated_files(tmp_path):
    payload = tmp_path / "payload.exe"
    payload.write_bytes(b"MZ-exemplo")
    target = tmp_path / "Programs" / "FireTVDesktop"
    target.mkdir(parents=True)
    note = target / "anotacao.txt"
    note.write_text("preservar")
    integrated = []
    install_payload(payload, target, lambda folder: integrated.append(folder))
    assert (target / "FireTVDesktop.exe").read_bytes() == payload.read_bytes()
    assert (target / "desinstalar.ps1").exists()
    assert note.read_text() == "preservar"
    assert integrated == [target]


def test_update_does_not_destroy_old_executable_if_replace_fails(tmp_path, monkeypatch):
    payload = tmp_path / "payload.exe"
    payload.write_bytes(b"nova")
    target = tmp_path / "app"
    target.mkdir()
    (target / "FireTVDesktop.exe").write_bytes(b"anterior")

    def denied(self, other):
        raise PermissionError("Em uso")

    monkeypatch.setattr(Path, "replace", denied)
    with pytest.raises(PermissionError):
        install_payload(payload, target, lambda _: None)
    assert (target / "FireTVDesktop.exe").read_bytes() == b"anterior"
    assert list(target.iterdir()) == [target / "FireTVDesktop.exe"]


def test_shell_scripts_quote_paths_and_uninstall_only_named_app_files():
    target = Path("C:/Users/Example's Name/Programs/FireTVDesktop")
    assert "Example''s Name" in shell_script(target)
    script = uninstall_script(target)
    assert "-Recurse" not in script
    assert "GetFullPath" in script
    assert "TargetPath -eq $exe" in script
    assert "firetv-desktop" not in script  # não toca em configuração ou histórico
