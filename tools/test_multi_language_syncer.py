from multi_language_syncer import MultiLanguageSyncer


def test_python_cli_is_not_an_active_sync_language():
    """
    Verify that python cli is not an active sync language.
    """
    assert "python-cli" not in MultiLanguageSyncer.LANGUAGES
