import struct

import pytest
import verify_artifacts as va


def make_pe(machine: int) -> bytes:
    header = bytearray(0x40)
    header[:2] = b"MZ"
    header[0x3C:0x40] = struct.pack("<I", 0x80)
    pe = bytearray(0x80) + b"PE\0\0" + struct.pack("<H", machine) + b"\0" * 20
    return bytes(header) + bytes(pe[0x40:])


def test_pe_machine_detection(tmp_path):
    x64, arm = tmp_path / "x64.exe", tmp_path / "arm.exe"
    x64.write_bytes(make_pe(0x8664))
    arm.write_bytes(make_pe(0xAA64))
    assert va.pe_arch(x64) == "x64"
    assert va.pe_arch(arm) == "arm64"


def test_pe_rejects_garbage(tmp_path):
    bad = tmp_path / "bad.exe"
    bad.write_bytes(b"not a pe file at all" * 10)
    with pytest.raises(va.VerificationError):
        va.pe_arch(bad)


def test_macho_thin_and_fat(tmp_path):
    arm = tmp_path / "arm"
    arm.write_bytes(struct.pack("<II", 0xFEEDFACF, 0x0100000C) + b"\0" * 24)
    x64 = tmp_path / "x64"
    x64.write_bytes(struct.pack("<II", 0xFEEDFACF, 0x01000007) + b"\0" * 24)
    fat = tmp_path / "fat"
    fat.write_bytes(
        struct.pack(">II", 0xCAFEBABE, 2)
        + struct.pack(">IIIII", 0x01000007, 3, 4096, 100, 12)
        + struct.pack(">IIIII", 0x0100000C, 0, 8192, 100, 14)
    )
    assert va.macho_archs(arm) == {"arm64"}
    assert va.macho_archs(x64) == {"x64"}
    assert va.macho_archs(fat) == {"x64", "arm64"}


def test_artifact_names_and_checksums(tmp_path):
    from common import TARGETS, artifact_name

    assert artifact_name("1.0.0", "windows-x64") == "Disk-Analyzer-v1.0.0-Windows-x64.zip"
    assert artifact_name("1.0.0", "macos-intel") == "Disk-Analyzer-v1.0.0-macOS-Intel-x86_64.dmg"
    assert len(TARGETS) == 4
    for t in TARGETS:
        (tmp_path / artifact_name("1.0.0", t)).write_bytes(t.encode())
    va.check_final(tmp_path, "1.0.0")
    va.write_checksums(tmp_path, "1.0.0")
    va.verify_checksums(tmp_path, "1.0.0")
    victim = tmp_path / artifact_name("1.0.0", "windows-x64")
    victim.write_bytes(b"tampered")
    with pytest.raises(va.VerificationError):
        va.verify_checksums(tmp_path, "1.0.0")
    victim.unlink()
    with pytest.raises(va.VerificationError):
        va.check_final(tmp_path, "1.0.0")


@pytest.mark.parametrize(
    "ver,ok", [("1.0.0", True), ("v2.10.3", True), ("1.0.0-rc.1", True), ("1.0", False), ("01.0.0", False), ("1.0.0.0", False)]
)
def test_semver_validation(ver, ok):
    from common import normalize_version

    if ok:
        assert normalize_version(ver) == ver.lstrip("v")
    else:
        with pytest.raises(ValueError):
            normalize_version(ver)
