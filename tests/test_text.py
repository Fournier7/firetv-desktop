from firetv.text import prepare_text


def test_prepare_text_space():
    assert prepare_text("oi mundo") == ("oi%smundo", "")


def test_prepare_text_accents():
    assert prepare_text("ação") == ("ao", "çã")


def test_prepare_text_percent():
    assert prepare_text("5%") == ("5", "%")


def test_prepare_text_quote_is_escaped_for_single_quotes():
    assert prepare_text("it's") == ("it'\\''s", "")
