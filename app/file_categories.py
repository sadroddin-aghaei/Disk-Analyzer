"""File extension -> category mapping and category colours."""

from __future__ import annotations

CATEGORIES: tuple[str, ...] = (
    "video",
    "audio",
    "images",
    "documents",
    "archives",
    "code",
    "executables",
    "system",
    "other",
)

CATEGORY_COLORS: dict[str, str] = {
    "video": "#E4572E",
    "audio": "#F29E4C",
    "images": "#43AA8B",
    "documents": "#4C8DFF",
    "archives": "#9B5DE5",
    "code": "#2EC4B6",
    "executables": "#F15BB5",
    "system": "#E9C46A",
    "other": "#6F7FA3",
}

_GROUPS: dict[str, str] = {
    "video": "mp4 mkv avi mov wmv flv webm m4v mpg mpeg ts m2ts vob 3gp",
    "audio": "mp3 wav flac aac ogg oga m4a wma opus aiff mid midi",
    "images": "jpg jpeg png gif bmp tif tiff webp svg ico heic heif raw cr2 nef arw psd ai xcf",
    "documents": "pdf doc docx xls xlsx ppt pptx odt ods odp txt rtf md csv epub mobi pages numbers key tex",
    "archives": "zip rar 7z tar gz tgz bz2 xz zst iso dmg img cab wim vhd vhdx vmdk qcow2 pkg",
    "code": "py pyc js jsx tsx c cc cpp h hpp cs java kt go rs rb php swift sh bat ps1 json xml yml yaml toml html css sql lua",
    "executables": "exe msi app apk deb rpm appimage com scr bin run",
    "system": "dll sys so dylib lib a o ko drv cat inf mui log tmp dat db sqlite bak cache plist reg etl pf lnk",
}

_EXT_MAP: dict[str, str] = {ext: cat for cat, exts in _GROUPS.items() for ext in exts.split()}


def extension_of(name: str) -> str:
    """Lower-case extension without dot ('' when none; dotfiles have none)."""
    idx = name.rfind(".")
    if idx <= 0 or idx == len(name) - 1:
        return ""
    return name[idx + 1 :].lower()


def category_of(name: str) -> str:
    return _EXT_MAP.get(extension_of(name), "other")


def color_of(category: str) -> str:
    return CATEGORY_COLORS.get(category, CATEGORY_COLORS["other"])
