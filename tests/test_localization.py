import re
from pathlib import Path

import pytest

from app.file_categories import CATEGORIES
from app.localization import DEFAULT_LANGUAGE, LANGUAGES, STRINGS, Translator
from app.settings import Settings


def test_default_is_persian_and_rtl():
    t = Translator()
    assert DEFAULT_LANGUAGE == "fa" and t.language == "fa" and t.is_rtl
    assert not Translator("en").is_rtl


def test_unknown_language_falls_back():
    assert Translator("de").language == "fa"


def test_key_parity_between_languages():
    assert set(STRINGS["fa"]) == set(STRINGS["en"])


def test_placeholders_match():
    field = re.compile(r"{(\w+)}")
    for key, en in STRINGS["en"].items():
        assert set(field.findall(en)) == set(field.findall(STRINGS["fa"][key])), key


def test_every_category_is_translated():
    for lang in LANGUAGES:
        for cat in CATEGORIES:
            assert f"cat_{cat}" in STRINGS[lang]


def test_all_keys_used_in_source_exist():
    root = Path(__file__).resolve().parent.parent / "app"
    used = set()
    for py in root.rglob("*.py"):
        if py.name == "localization.py":
            continue
        used |= set(re.findall(r"""\.t\(\s*["']([a-z_0-9]+)["']""", py.read_text(encoding="utf-8")))
    assert used, "no translation keys found"
    assert used <= set(STRINGS["en"]), used - set(STRINGS["en"])


def test_persian_digits_and_sizes():
    fa, en = Translator("fa"), Translator("en")
    assert fa.number(1234) == "۱٬۲۳۴" and en.number(1234) == "1,234"
    assert fa.size(1536) == "۱٫۵ کیلوبایت" and en.size(1536) == "1.5 KB"
    assert en.size(0) == "0 B" and en.size(5 * 1024**4) == "5.0 TB"
    assert fa.duration(3725) == "۰۱:۰۲:۰۵" and en.duration(65) == "00:01:05"
    assert en.percent(0.5) == "50%" and en.percent(0.052) == "5.2%"


def test_format_missing_argument_does_not_crash():
    assert Translator("en").t("status_files") == "Files: {n}"
    assert Translator("en").t("nonexistent_key") == "nonexistent_key"


def test_settings_roundtrip_and_corruption(tmp_path):
    path = tmp_path / "s.json"
    Settings(language="en", last_folder="/x").save(path)
    assert Settings.load(path) == Settings("en", "/x")
    path.write_text("{not json", encoding="utf-8")
    assert Settings.load(path).language == "fa"
    path.write_text('{"language": "klingon"}', encoding="utf-8")
    assert Settings.load(path).language == "fa"
    assert Settings.load(tmp_path / "missing.json") == Settings()


@pytest.mark.parametrize("lang", ["fa", "en"])
def test_window_builds_and_switches_language(lang):
    from PySide6.QtWidgets import QApplication

    from app.main_window import MainWindow
    from app.theme import load_fonts

    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])
    load_fonts(app)
    win = MainWindow(Settings(language=lang), persist_settings=False)
    assert win.tr_.language == lang
    win.set_language("en" if lang == "fa" else "fa")
    assert win.tr_.language != lang
    win.close()
