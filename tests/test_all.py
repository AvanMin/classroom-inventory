"""Единый набор автотестов проекта «Система учёта инвентаря компьютерных классов» (Спринт 6).

Покрывает:
  - валидацию модели Equipment и сериализацию (to_dict / from_dict)
  - полный CRUD, поиск и комбинированную фильтрацию в Inventory
  - автогенерацию инвентарного номера (suggest_next_number)
  - безопасную загрузку и атомарное сохранение JSON в storage.py
  - сквозные сценарии консольного меню (main.py)
  - регрессию демонстрационного справочника
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from inventory import Equipment, Inventory, STATES, demo_inventory
from main import (
    add_equipment,
    delete_equipment,
    edit_equipment,
    filter_equipment,
    find_equipment,
    show_inventory,
)
from storage import load_inventory, save_inventory


def make(**overrides) -> Equipment:
    base = dict(
        inventory_number="PC-0001",
        kind="ПК",
        name="Системный блок",
        room="204",
        state="исправно",
    )
    base.update(overrides)
    return Equipment(**base)


# =====================================================================
# 1. Модель Equipment: валидация и сериализация
# =====================================================================

@pytest.mark.parametrize("field", ["inventory_number", "kind", "name", "room", "state"])
def test_equipment_requires_non_empty_field(field: str) -> None:
    with pytest.raises(ValueError):
        make(**{field: "   "})


def test_equipment_rejects_unknown_state() -> None:
    with pytest.raises(ValueError):
        make(state="сломано")


def test_equipment_received_at_display() -> None:
    assert make(received_at="2021-09-01").received_at_display == "01.09.2021"
    assert make(received_at="").received_at_display == "-"
    assert make(received_at="not-a-date").received_at_display == "not-a-date"


def test_from_dict_normalizes_number_and_state() -> None:
    item = Equipment.from_dict(
        {
            "inventory_number": "  pc-0001  ",
            "type": "ПК",
            "name": "  Системный   блок  ",
            "room": "204",
            "state": "ИСПРАВНО",
        }
    )
    assert item.inventory_number == "PC-0001"
    assert item.state == "исправно"
    assert item.name == "Системный блок"


def test_from_dict_rejects_non_string_required_field() -> None:
    with pytest.raises(ValueError):
        Equipment.from_dict(
            {
                "inventory_number": 123,
                "type": "ПК",
                "name": "x",
                "room": "204",
                "state": "исправно",
            }
        )


def test_from_dict_rejects_missing_required_fields() -> None:
    with pytest.raises(ValueError):
        Equipment.from_dict({"inventory_number": "PC-1"})


# =====================================================================
# 2. Контейнер Inventory: CRUD, поиск, фильтрация, сортировка
# =====================================================================

def test_add_and_get_by_number_is_case_insensitive() -> None:
    inv = Inventory()
    inv.add(make(inventory_number="PC-0001"))
    assert len(inv) == 1
    assert inv.has_number("pc-0001")
    assert inv.get_by_number("  Pc-0001  ") is not None


def test_add_duplicate_raises() -> None:
    inv = Inventory([make(inventory_number="PC-0001")])
    with pytest.raises(ValueError):
        inv.add(make(inventory_number="pc-0001"))


def test_get_by_number_returns_none_for_unknown_and_empty() -> None:
    inv = Inventory([make()])
    assert inv.get_by_number("ZZZ-9") is None
    assert inv.get_by_number("   ") is None


def test_search_by_room_is_case_insensitive_substring() -> None:
    inv = Inventory(
        [
            make(inventory_number="A-1", room="204"),
            make(inventory_number="A-2", room="Кабинет 305"),
            make(inventory_number="A-3", room="101"),
        ]
    )
    assert {i.inventory_number for i in inv.search_by_room("20")} == {"A-1"}
    assert {i.inventory_number for i in inv.search_by_room("305")} == {"A-2"}
    assert inv.search_by_room("   ") == []


def test_filter_by_state_direct() -> None:
    inv = Inventory(
        [
            make(inventory_number="A-1", state="исправно"),
            make(inventory_number="A-2", state="списано"),
        ]
    )
    assert [i.inventory_number for i in inv.filter_by_state("СПИСАНО")] == ["A-2"]
    assert inv.filter_by_state("") == []


def test_filter_by_room_and_state_combines_criteria() -> None:
    inv = Inventory(
        [
            make(inventory_number="A-1", room="204", state="исправно"),
            make(inventory_number="A-2", room="204", state="списано"),
            make(inventory_number="A-3", room="305", state="исправно"),
        ]
    )
    only_room = inv.filter_by_room_and_state(room="204")
    assert {i.inventory_number for i in only_room} == {"A-1", "A-2"}

    both = inv.filter_by_room_and_state(room="204", state="исправно")
    assert [i.inventory_number for i in both] == ["A-1"]


def test_update_returns_new_object_and_keeps_original_immutable() -> None:
    original = make(inventory_number="PC-0001", room="204", state="исправно")
    inv = Inventory([original])

    updated = inv.update("pc-0001", new_room="305", new_state="требует ремонта")

    assert updated is not original
    assert updated.room == "305"
    assert updated.state == "требует ремонта"
    assert original.room == "204"
    assert original.state == "исправно"
    assert inv.get_by_number("PC-0001") is updated


def test_update_rejects_invalid_state() -> None:
    inv = Inventory([make()])
    with pytest.raises(ValueError):
        inv.update("PC-0001", new_state="сломано")


def test_update_unknown_number_raises_keyerror() -> None:
    inv = Inventory([make()])
    with pytest.raises(KeyError):
        inv.update("ZZZ-9", new_room="305")


def test_update_without_changes_returns_same_item() -> None:
    item = make()
    inv = Inventory([item])
    assert inv.update("PC-0001") is item


def test_delete_existing_and_missing() -> None:
    inv = Inventory([make(inventory_number="PC-0001"), make(inventory_number="MON-0001")])
    assert inv.delete("pc-0001") is True
    assert len(inv) == 1
    assert inv.delete("PC-0001") is False


def test_all_returns_sorted_by_number() -> None:
    inv = Inventory(
        [
            make(inventory_number="B-2"),
            make(inventory_number="A-1"),
            make(inventory_number="C-3"),
        ]
    )
    assert [i.inventory_number for i in inv.all()] == ["A-1", "B-2", "C-3"]


# =====================================================================
# 3. Автогенерация инвентарных номеров (Спринт 6)
# =====================================================================

def test_suggest_next_number_empty_inventory() -> None:
    inv = Inventory()
    assert inv.suggest_next_number("ПК") == "PC-0001"
    assert inv.suggest_next_number("монитор") == "MON-0001"
    assert inv.suggest_next_number("неизвестный_тип") == "EQ-0001"


def test_suggest_next_number_increments_max() -> None:
    inv = demo_inventory()
    assert inv.suggest_next_number("ПК") == "PC-0003"
    assert inv.suggest_next_number("монитор") == "MON-0002"


def test_suggest_next_number_handles_gaps_and_custom_numbers() -> None:
    inv = Inventory(
        [
            make(inventory_number="CUSTOM-99", kind="ПК"),
            make(inventory_number="PC-0005", kind="ПК"),
        ]
    )
    assert inv.suggest_next_number("ПК") == "PC-0006"


# =====================================================================
# 4. Постоянное хранение JSON (storage.py)
# =====================================================================

def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    target = tmp_path / "nope" / "inventory.json"
    assert len(load_inventory(target)) == 0


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
            {
                "inventory_number": "",
                "type": "ПК",
                "name": "x",
                "room": "1",
                "state": "исправно",
            },
        ]
    }
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    inv = load_inventory(target)
    assert len(inv) == 1
    assert inv.get_by_number("PC-0001") is not None


def test_save_creates_parent_dir_and_round_trips(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "data" / "inventory.json"
    inv = Inventory([make(inventory_number="PC-0001"), make(inventory_number="PC-0002")])
    save_inventory(inv, target)

    assert target.exists()
    reloaded = load_inventory(target)
    assert [i.inventory_number for i in reloaded.all()] == ["PC-0001", "PC-0002"]


def test_save_does_not_leave_tmp_file(tmp_path: Path) -> None:
    target = tmp_path / "inventory.json"
    save_inventory(Inventory([make()]), target)
    assert list(tmp_path.glob("*.tmp")) == []


def test_save_is_atomic_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "inventory.json"
    save_inventory(Inventory([make(inventory_number="OLD-1")]), target)
    before = target.read_text(encoding="utf-8")

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "replace", boom)
    with pytest.raises(OSError):
        save_inventory(Inventory([make(inventory_number="NEW-1")]), target)

    assert target.read_text(encoding="utf-8") == before
    assert list(tmp_path.glob("*.tmp")) == []


# =====================================================================
# 5. Сценарии консольного меню (CLI)
# =====================================================================

def test_cli_show_inventory(capsys: pytest.CaptureFixture[str]) -> None:
    inv = Inventory([make(inventory_number="PC-0001", name="Alpha")])
    show_inventory(inv)
    output = capsys.readouterr().out
    assert "PC-0001" in output
    assert "Alpha" in output


def test_cli_add_equipment_accepts_suggested_number(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    inv = demo_inventory()
    data_file = tmp_path / "inventory.json"

    # Тип: 1 (ПК) -> Номер: "" (принять PC-0003) -> Имя -> Кабинет -> Состояние: 1 -> Дата -> Ответственный
    inputs = iter(
        [
            "1",
            "",
            "Системный блок Asus",
            "301",
            "1",
            "2026-11-13",
            "Лаборант",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    add_equipment(inv, data_file)

    output = capsys.readouterr().out
    assert "успешно добавлена" in output
    created = inv.get_by_number("PC-0003")
    assert created is not None
    assert created.name == "Системный блок Asus"
    assert created.room == "301"
    assert data_file.exists()


def test_cli_add_equipment_manual_number_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    inv = Inventory()
    data_file = tmp_path / "inventory.json"

    # Тип: ПК -> Номер вручную: LAB-777 -> Имя -> Кабинет -> Состояние -> Дата -> Ответственный
    inputs = iter(["ПК", "LAB-777", "Тестовый стенд", "105", "исправно", "", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    add_equipment(inv, data_file)

    assert inv.has_number("LAB-777")
    assert not inv.has_number("PC-0001")


def test_cli_find_by_number_and_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inv = Inventory([make(inventory_number="PC-0001", name="Системник")])

    inputs_found = iter(["1", "PC-0001"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs_found))
    find_equipment(inv)
    out_found = capsys.readouterr().out
    assert "Найдено оборудование" in out_found
    assert "Системник" in out_found

    inputs_missing = iter(["1", "NO-SUCH"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs_missing))
    find_equipment(inv)
    out_missing = capsys.readouterr().out
    assert "не найдена" in out_missing


def test_cli_edit_equipment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    inv = Inventory([make(inventory_number="PC-0001", room="204")])
    data_file = tmp_path / "inventory.json"

    inputs = iter(["PC-0001", "305", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    edit_equipment(inv, data_file)

    item = inv.get_by_number("PC-0001")
    assert item is not None
    assert item.room == "305"
    assert data_file.exists()


def test_cli_delete_confirmed_and_cancelled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    inv = Inventory([make(inventory_number="PC-0001")])
    data_file = tmp_path / "inventory.json"

    # Отмена удаления
    inputs_cancel = iter(["PC-0001", "нет"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs_cancel))
    delete_equipment(inv, data_file)
    assert inv.get_by_number("PC-0001") is not None
    assert "отменено" in capsys.readouterr().out.lower()

    # Подтверждение удаления
    inputs_confirm = iter(["PC-0001", "да"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs_confirm))
    delete_equipment(inv, data_file)
    assert inv.get_by_number("PC-0001") is None
    assert "успешно удалена" in capsys.readouterr().out


def test_cli_filter_equipment(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inv = Inventory(
        [
            make(inventory_number="A-1", room="204", state="исправно"),
            make(inventory_number="B-1", room="305", state="исправно"),
        ]
    )
    inputs = iter(["204", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    filter_equipment(inv)
    output = capsys.readouterr().out
    assert "Найдено записей: 1" in output
    assert "A-1" in output


# =====================================================================
# 6. Регрессия демонстрационного справочника
# =====================================================================

def test_demo_inventory_has_at_least_10_records() -> None:
    assert len(demo_inventory()) >= 10


def test_demo_inventory_is_sorted_and_covers_all_states() -> None:
    inv = demo_inventory()
    numbers = [item.inventory_number for item in inv.all()]
    assert numbers == sorted(numbers)
    assert {item.state for item in inv} == set(STATES)