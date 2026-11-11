"""Тесты файлового хранилища (спринт 5, QA)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from inventory import Equipment, Inventory
from storage import load_inventory, save_inventory


def make(number: str = "PC-0001") -> Equipment:
    return Equipment(
        inventory_number=number,
        kind="ПК",
        name="Системный блок",
        room="204",
        state="исправно",
        received_at="2021-09-01",
        responsible="Иванов И. И.",
    )


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    target = tmp_path / "nope" / "inventory.json"
    inv = load_inventory(target)
    assert len(inv) == 0


def test_load_empty_file_returns_empty(tmp_path: Path) -> None:
    target = tmp_path / "inventory.json"
    target.write_text("   \n", encoding="utf-8")
    assert len(load_inventory(target)) == 0


def test_load_broken_json_returns_empty(tmp_path: Path) -> None:
    target = tmp_path / "inventory.json"
    target.write_text("{not json", encoding="utf-8")
    assert len(load_inventory(target)) == 0


def test_load_wrong_structure_returns_empty(tmp_path: Path) -> None:
    target = tmp_path / "inventory.json"
    target.write_text(json.dumps({"items": []}), encoding="utf-8")
    assert len(load_inventory(target)) == 0


def test_load_skips_invalid_record_but_keeps_valid(tmp_path: Path) -> None:
    target = tmp_path / "inventory.json"
    payload = {
        "records": [
            {
                "inventory_number": "PC-0001",
                "type": "ПК",
                "name": "Системный блок",
                "room": "204",
                "state": "исправно",
            },
            {"inventory_number": "", "type": "ПК", "name": "x", "room": "1", "state": "исправно"},
        ]
    }
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    inv = load_inventory(target)
    assert len(inv) == 1
    assert inv.get_by_number("PC-0001") is not None


def test_save_creates_parent_dir_and_round_trips(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "data" / "inventory.json"
    inv = Inventory([make("PC-0001"), make("PC-0002")])
    save_inventory(inv, target)

    assert target.exists()
    reloaded = load_inventory(target)
    assert [i.inventory_number for i in reloaded.all()] == ["PC-0001", "PC-0002"]


def test_save_does_not_leave_tmp_file(tmp_path: Path) -> None:
    target = tmp_path / "inventory.json"
    save_inventory(Inventory([make()]), target)
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


def test_save_is_atomic_on_replace_failure(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "inventory.json"
    save_inventory(Inventory([make("OLD-1")]), target)
    before = target.read_text(encoding="utf-8")

    # Ломаем replace, чтобы проверить, что старый файл не пострадал
    import storage

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "replace", boom)
    with pytest.raises(OSError):
        save_inventory(Inventory([make("NEW-1")]), target)

    assert target.read_text(encoding="utf-8") == before
    assert list(tmp_path.glob("*.tmp")) == []