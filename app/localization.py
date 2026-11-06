"""Centralised localisation (Persian default, English secondary)."""

from __future__ import annotations

import contextlib
from typing import Final

LANGUAGES: Final = ("fa", "en")
DEFAULT_LANGUAGE: Final = "fa"
RTL_LANGUAGES: Final = frozenset({"fa"})

_FA_DIGITS = str.maketrans("0123456789.,%", "۰۱۲۳۴۵۶۷۸۹٫٬٪")

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "window_title": "Disk Analyzer",
        "no_drive": "No drive selected",
        "status_idle": "Ready",
        "status_scanning": "Scanning…",
        "status_done": "Scan complete",
        "status_cancelled": "Scan cancelled",
        "status_error": "Scan failed",
        "settings": "Settings",
        "language": "Language",
        "lang_fa": "فارسی",
        "lang_en": "English",
        "switch_language": "فارسی",
        "export_csv": "Export CSV…",
        "export_json": "Export JSON…",
        "about": "About",
        "drives": "Drives",
        "scan": "Scan",
        "rescan": "Rescan",
        "cancel": "Cancel",
        "choose_folder": "Choose folder…",
        "home_folder": "Home folder",
        "up": "Up",
        "location": "Location",
        "search_placeholder": "Search files and folders…",
        "filter_all": "All categories",
        "col_name": "Name",
        "col_type": "Type",
        "col_size": "Size",
        "type_folder": "Folder",
        "type_file": "File",
        "type_more_files": "{n} smaller files",
        "stats_title": "Storage",
        "capacity": "Total capacity",
        "used": "Used",
        "free": "Free",
        "files": "Files",
        "folders": "Folders",
        "categories": "File types",
        "largest_files": "Largest files",
        "largest_folders": "Largest folders",
        "largest_folders_tip": "Ranked by the size of files placed directly inside each folder.",
        "issues": "Skipped items",
        "issues_text": "{errors} inaccessible · {links} links skipped",
        "status_files": "Files: {n}",
        "status_folders": "Folders: {n}",
        "status_elapsed": "Time: {t}",
        "status_current": "Scanning: {p}",
        "empty_state": "Select a drive and press Scan",
        "empty_scanning": "Scanning… the map appears when finished",
        "dialog_choose_folder": "Choose a folder to analyze",
        "dialog_export_csv": "Export as CSV",
        "dialog_export_json": "Export as JSON",
        "export_ok": "Exported successfully:\n{path}",
        "export_fail": "Export failed:\n{error}",
        "no_data": "Run a scan first.",
        "scan_failed": "The scan could not be completed:\n{error}",
        "scan_busy": "A scan is already running.",
        "path_missing": "The selected location no longer exists:\n{path}",
        "error_title": "Error",
        "info_title": "Information",
        "readonly_note": "Disk Analyzer is read-only: it never changes, moves or deletes your files.",
        "about_text": "Version {version}\nDeveloper: {author}\n\n{note}\n\n{copyright}",
        "cat_video": "Video",
        "cat_audio": "Audio",
        "cat_images": "Images",
        "cat_documents": "Documents",
        "cat_archives": "Archives & disk images",
        "cat_code": "Code & data",
        "cat_executables": "Applications",
        "cat_system": "System & cache",
        "cat_other": "Other",
        "hover_info": "{name}\n{size} · {pct}\n{kind}",
        "unit_b": "B", "unit_kb": "KB", "unit_mb": "MB", "unit_gb": "GB", "unit_tb": "TB",
    },
    "fa": {
        "window_title": "دیسک آنالایزر",
        "no_drive": "درایوی انتخاب نشده",
        "status_idle": "آماده",
        "status_scanning": "در حال اسکن…",
        "status_done": "اسکن کامل شد",
        "status_cancelled": "اسکن لغو شد",
        "status_error": "اسکن ناموفق بود",
        "settings": "تنظیمات",
        "language": "زبان",
        "lang_fa": "فارسی",
        "lang_en": "English",
        "switch_language": "English",
        "export_csv": "خروجی CSV…",
        "export_json": "خروجی JSON…",
        "about": "درباره",
        "drives": "درایوها",
        "scan": "اسکن",
        "rescan": "اسکن مجدد",
        "cancel": "لغو",
        "choose_folder": "انتخاب پوشه…",
        "home_folder": "پوشه کاربر",
        "up": "بالا",
        "location": "مسیر",
        "search_placeholder": "جستجوی فایل‌ها و پوشه‌ها…",
        "filter_all": "همه دسته‌ها",
        "col_name": "نام",
        "col_type": "نوع",
        "col_size": "حجم",
        "type_folder": "پوشه",
        "type_file": "فایل",
        "type_more_files": "{n} فایل کوچک‌تر",
        "stats_title": "فضای ذخیره‌سازی",
        "capacity": "ظرفیت کل",
        "used": "استفاده‌شده",
        "free": "آزاد",
        "files": "فایل‌ها",
        "folders": "پوشه‌ها",
        "categories": "نوع فایل‌ها",
        "largest_files": "بزرگ‌ترین فایل‌ها",
        "largest_folders": "بزرگ‌ترین پوشه‌ها",
        "largest_folders_tip": "بر اساس حجم فایل‌هایی که مستقیماً داخل هر پوشه قرار دارند.",
        "issues": "موارد رد‌شده",
        "issues_text": "{errors} غیرقابل‌دسترس · {links} پیوند نادیده گرفته شد",
        "status_files": "فایل‌ها: {n}",
        "status_folders": "پوشه‌ها: {n}",
        "status_elapsed": "زمان: {t}",
        "status_current": "در حال اسکن: {p}",
        "empty_state": "یک درایو انتخاب کنید و «اسکن» را بزنید",
        "empty_scanning": "در حال اسکن… نقشه پس از پایان نمایش داده می‌شود",
        "dialog_choose_folder": "پوشه موردنظر برای تحلیل را انتخاب کنید",
        "dialog_export_csv": "ذخیره به‌صورت CSV",
        "dialog_export_json": "ذخیره به‌صورت JSON",
        "export_ok": "با موفقیت ذخیره شد:\n{path}",
        "export_fail": "ذخیره‌سازی ناموفق بود:\n{error}",
        "no_data": "ابتدا یک اسکن انجام دهید.",
        "scan_failed": "اسکن کامل نشد:\n{error}",
        "scan_busy": "یک اسکن در حال اجراست.",
        "path_missing": "مسیر انتخاب‌شده دیگر وجود ندارد:\n{path}",
        "error_title": "خطا",
        "info_title": "اطلاعات",
        "readonly_note": "دیسک آنالایزر فقط‌خواندنی است: هرگز فایل‌های شما را تغییر نمی‌دهد، جابه‌جا یا حذف نمی‌کند.",
        "about_text": "نسخه {version}\nسازنده: {author}\n\n{note}\n\n{copyright}",
        "cat_video": "ویدیو",
        "cat_audio": "صوت",
        "cat_images": "تصاویر",
        "cat_documents": "اسناد",
        "cat_archives": "آرشیو و ایمیج دیسک",
        "cat_code": "کد و داده",
        "cat_executables": "برنامه‌ها",
        "cat_system": "سیستم و کش",
        "cat_other": "سایر",
        "hover_info": "{name}\n{size} · {pct}\n{kind}",
        "unit_b": "بایت", "unit_kb": "کیلوبایت", "unit_mb": "مگابایت", "unit_gb": "گیگابایت", "unit_tb": "ترابایت",
    },
}  # fmt: skip


class Translator:
    def __init__(self, language: str = DEFAULT_LANGUAGE) -> None:
        self._lang = DEFAULT_LANGUAGE
        self.set_language(language)

    @property
    def language(self) -> str:
        return self._lang

    @property
    def is_rtl(self) -> bool:
        return self._lang in RTL_LANGUAGES

    def set_language(self, language: str) -> None:
        self._lang = language if language in STRINGS else DEFAULT_LANGUAGE

    def t(self, key: str, **kwargs: object) -> str:
        text = STRINGS[self._lang].get(key) or STRINGS["en"].get(key) or key
        if kwargs:
            kwargs = {k: (self.digits(v) if isinstance(v, str) and k in {"n", "t"} else v) for k, v in kwargs.items()}
            with contextlib.suppress(KeyError, IndexError):
                text = text.format(**kwargs)
        return text

    # ----- number formatting
    def digits(self, text: str) -> str:
        return text.translate(_FA_DIGITS) if self._lang == "fa" else text

    def number(self, value: int) -> str:
        return self.digits(f"{value:,}")

    def percent(self, fraction: float) -> str:
        pct = fraction * 100.0
        text = f"{pct:.1f}%" if 0 < pct < 10 else f"{pct:.0f}%"
        return self.digits(text)

    def size(self, num_bytes: int) -> str:
        value = float(num_bytes)
        units = ("unit_b", "unit_kb", "unit_mb", "unit_gb", "unit_tb")
        idx = 0
        while value >= 1024 and idx < len(units) - 1:
            value /= 1024
            idx += 1
        number = f"{int(value)}" if idx == 0 else (f"{value:.1f}" if value < 100 else f"{value:.0f}")
        return self.digits(number) + " " + self.t(units[idx])

    def duration(self, seconds: float) -> str:
        s = int(seconds)
        return self.digits(f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}")


def format_size_plain(num_bytes: int) -> str:
    """Language-neutral size string (used by exports)."""
    return Translator("en").size(num_bytes)
