from firetv.ui.instance import SingleInstance


def test_second_launch_activates_first_without_taking_ownership(qtbot, tmp_path):
    activated = []
    first = SingleInstance(tmp_path)
    second = SingleInstance(tmp_path)
    try:
        assert first.acquire_or_activate()
        first.set_activation_callback(lambda: activated.append(True))
        assert not second.acquire_or_activate()
        qtbot.waitUntil(lambda: activated == [True], timeout=3000)
    finally:
        second.close()
        first.close()


def test_app_can_be_started_again_after_exit(qapp, tmp_path):
    first = SingleInstance(tmp_path)
    assert first.acquire_or_activate()
    first.close()
    second = SingleInstance(tmp_path)
    try:
        assert second.acquire_or_activate()
    finally:
        second.close()
