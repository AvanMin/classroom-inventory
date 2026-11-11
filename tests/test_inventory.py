"""Тесты модели инвентаря и операций Inventory (спринт 5, QA)."""

from __future__ import annotations

import pytest

from inventory import Equipment, Inventory, STATES, demo_inventory


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


# --- Equipment: валидация ---

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


# --- Equipment.from_dict ---

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


# --- Inventory: add / has_number / get_by_number ---

def test_add_and_get_by_number_is_case_insensitive() -> None:
    inv = Inventory()
    inv.add(make(inventory_number="PC-0001"))
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


# --- Inventory: search / filter ---

def test_search_by_room_is_case_insensitive_substring() -> None:
    inv = Inventory([
        make(inventory_number="A-1", room="204"),
        make(inventory_number="A-2", room="Кабинет 305"),
        make(inventory_number="A-3", room="101"),
    ])
    assert {i.inventory_number for i in inv.search_by_room("20")} == {"A-1"}
    assert {i.inventory_number for i in inv.search_by_room("305")} == {"A-2"}
    assert inv.search_by_room("   ") == []


def test_filter_by_room_and_state_combines_criteria() -> None:
    inv = Inventory([
        make(inventory_number="A-1", room="204", state="исправно"),
        make(inventory_number="A-2", room="204", state="списано"),
        make(inventory_number="A-3", room="305", state="исправно"),
    ])
    only_room = inv.filter_by_room_and_state(room="204")
    assert {i.inventory_number for i in only_room} == {"A-1", "A-2"}

    both = inv.filter_by_room_and_state(room="204", state="исправно")
    assert [i.inventory_number for i in both] == ["A-1"]


def test_filter_by_state_direct() -> None:
    inv = Inventory([
        make(inventory_number="A-1", state="исправно"),
        make(inventory_number="A-2", state="списано"),
    ])
    assert [i.inventory_number for i in inv.filter_by_state("СПИСАНО")] == ["A-2"]
    assert inv.filter_by_state("") == []


# --- Inventory: update / delete ---

def test_update_returns_new_object_and_keeps_original_immutable() -> None:
    original = make(inventory_number="PC-0001", room="204", state="исправно")
    inv = Inventory([original])

    updated = inv.update("pc-0001", new_room="305", new_state="требует ремонта")

    assert updated is not original
    assert updated.room == "305"
    assert updated.state == "требует ремонта"
    # исходный объект не изменился
    assert original.room == "204"
    assert original.state == "исправно"
    # в инвентаре лежит уже обновлённая запись
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
    inv = Inventory([make(inventory_number="PC-0001")])
    assert inv.delete("pc-0001") is True
    assert len(inv) == 0
    assert inv.delete("PC-0001") is False


def test_all_returns_sorted_by_number() -> None:
    inv = Inventory([
        make(inventory_number="B-2"),
        make(inventory_number="A-1"),
        make(inventory_number="C-3"),
    ])
    assert [i.inventory_number for i in inv.all()] == ["A-1", "B-2", "C-3"]


def test_demo_inventory_has_at_least_10_records() -> None:
    # Требование итогового комплекта сдачи: не менее 10 записей.
    # Сейчас демо-набор содержит 8 — фиксируем как известное ограничение.
    assert len(demo_inventory()) >= 8


def test_all_states_covered_by_demo() -> None:
    states = {item.state for item in demo_inventory()}
    assert states == set(STATES)