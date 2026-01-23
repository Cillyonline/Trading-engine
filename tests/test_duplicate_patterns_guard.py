from __future__ import annotations

from collections import defaultdict
from pathlib import Path


def _collect_named_dirs(root: Path, dir_names: set[str]) -> dict[str, list[Path]]:
    matches: dict[str, list[Path]] = {name: [] for name in dir_names}
    for path in root.rglob("*"):
        if path.is_dir() and path.name in dir_names:
            matches[path.name].append(path)
    return matches


def _collect_duplicate_filenames(dirs: list[Path]) -> dict[str, list[Path]]:
    name_map: defaultdict[str, list[Path]] = defaultdict(list)
    for dir_path in dirs:
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                name_map[file_path.name].append(file_path)
    return {name: paths for name, paths in name_map.items() if len(paths) > 1}


def test_no_duplicate_test_data_patterns() -> None:
    test_root = Path(__file__).resolve().parent
    data_dir_names = {"golden", "fixtures", "snapshots"}

    duplicate_dirs = _collect_named_dirs(test_root, data_dir_names)
    duplicate_dir_conflicts = {
        name: paths for name, paths in duplicate_dirs.items() if len(paths) > 1
    }

    duplicate_files = _collect_duplicate_filenames(
        [path for paths in duplicate_dirs.values() for path in paths]
    )

    messages = []
    if duplicate_dir_conflicts:
        for name, paths in duplicate_dir_conflicts.items():
            joined = "\n  ".join(str(path) for path in sorted(paths))
            messages.append(f"Duplicate '{name}' directories found:\n  {joined}")

    if duplicate_files:
        for name, paths in duplicate_files.items():
            joined = "\n  ".join(str(path) for path in sorted(paths))
            messages.append(f"Duplicate test data filenames '{name}' found:\n  {joined}")

    assert not messages, "\n\n".join(messages)
