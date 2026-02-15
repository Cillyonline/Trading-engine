from __future__ import annotations

from pathlib import Path

from cilly_trading.strategies.registry import run_registry_smoke


REFERENCE_PACK_DIR = Path("docs/strategy_packs/reference_pack")


def test_reference_pack_directory_and_metadata_exist() -> None:
    assert REFERENCE_PACK_DIR.exists()
    metadata_path = REFERENCE_PACK_DIR / "metadata.yaml"
    assert metadata_path.exists()

    metadata_text = metadata_path.read_text(encoding="utf-8")
    for required_key in (
        "pack_id:",
        "version:",
        "deterministic_hash:",
        "dependencies:",
    ):
        assert required_key in metadata_text


def test_reference_pack_readme_contains_required_sections_in_order() -> None:
    readme_path = REFERENCE_PACK_DIR / "README.md"
    assert readme_path.exists()

    readme_text = readme_path.read_text(encoding="utf-8")
    required_sections = [
        "## Overview",
        "## Strategy Objective",
        "## Strategy Logic Summary",
        "## Parameter Definitions",
        "## Deterministic Behavior",
        "## Risk Disclosure",
        "## Version & Compatibility",
        "## Change Log Reference",
    ]

    section_positions = [readme_text.index(section) for section in required_sections]
    assert section_positions == sorted(section_positions)


def test_reference_strategy_is_in_deterministic_smoke_output() -> None:
    first = run_registry_smoke()
    second = run_registry_smoke()

    assert first == ["REFERENCE", "RSI2", "TURTLE"]
    assert second == ["REFERENCE", "RSI2", "TURTLE"]
