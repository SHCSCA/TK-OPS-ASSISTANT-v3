from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

UTF8_TEXT_FILES = [
    ROOT / "docs" / "RUNTIME-API-CALLS.md",
    ROOT / "apps" / "desktop" / "src" / "pages" / "assets" / "AssetLibraryPage.vue",
    ROOT / "apps" / "desktop" / "src" / "components" / "assets" / "AssetPreview.vue",
    ROOT / "apps" / "desktop" / "src" / "components" / "shell" / "details" / "AssetDetail.vue",
]

MOJIBAKE_MARKERS = (
    "\u00c3",
    "\u00c2",
    "\u00e2\u20ac",
    "\u00ef\u00bc",
    "\u74a7\u52ea\u9a87",
    "\u7eef\u8364\u7cba",
    "\u7035\u714e\u53c6",
    "\u68f0\u52ee\ue74d",
)


def test_user_facing_text_files_are_utf8_without_bom() -> None:
    for path in UTF8_TEXT_FILES:
        data = path.read_bytes()

        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} must use UTF-8 without BOM"
        data.decode("utf-8")


def test_user_facing_text_files_do_not_contain_mojibake_markers() -> None:
    for path in UTF8_TEXT_FILES:
        text = path.read_text(encoding="utf-8")

        for marker in MOJIBAKE_MARKERS:
            assert marker not in text, f"{path} contains mojibake marker {marker!r}"


def test_runtime_api_calls_documents_utf8_contract() -> None:
    text = (ROOT / "docs" / "RUNTIME-API-CALLS.md").read_text(encoding="utf-8")

    assert "UTF-8" in text
    assert "无 BOM" in text
