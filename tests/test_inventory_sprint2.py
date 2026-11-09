"""Автотесты спринта 2 (роль QA).

Проверяем:
  * модель Equipment — валидация обязательных полей и состояния;
  * Inventory — уникальность номера, поиск, сортировку, добавление;
  * сценарий "Добавить запись" из main.py — успех, пустые поля,
    повторяющийся номер, отмена, отсутствие аварийного завершения.

"""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from inventory import Equipment, Inventory, STATES
from main import add_equipment, show_inventory


def make(**overrides) -> Equipment:
    """Корректная запись с возможностью точечно переопределить поля."""
    data = dict(
        inventory_number="PC-9001",
        kind="ПК",
        name="Тестовый системный блок",
        room="101",
        state="исправно",
    )
    data.update(overrides)
    return Equipment(**data)


class EquipmentModelTests(unittest.TestCase):
    """Модель записи: обязательные поля и допустимые состояния."""

    def test_valid_record_is_created(self) -> None:
        item = make()
        self.assertEqual(item.inventory_number, "PC-9001")
        self.assertEqual(item.state, "исправно")

    def test_each_required_field_is_mandatory(self) -> None:
        for field in ("inventory_number", "kind", "name", "room", "state"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    make(**{field: ""})

    def test_whitespace_only_field_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            make(name="   ")

    def test_unknown_state_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            make(state="сломано")

    def test_all_states_from_reference_are_accepted(self) -> None:
        for state in STATES:
            with self.subTest(state=state):
                self.assertEqual(make(state=state).state, state)

    def test_received_at_display_formats_iso_date(self) -> None:
        self.assertEqual(make(received_at="2024-03-18").received_at_display,
                         "18.03.2024")

    def test_received_at_display_empty_is_dash(self) -> None:
        self.assertEqual(make().received_at_display, "-")


class InventoryStorageTests(unittest.TestCase):
    """Хранилище в памяти: уникальность, поиск, сортировка."""

    def test_add_increases_length(self) -> None:
        inv = Inventory()
        self.assertEqual(len(inv), 0)
        inv.add(make())
        self.assertEqual(len(inv), 1)

    def test_duplicate_number_is_rejected(self) -> None:
        inv = Inventory([make(inventory_number="PC-0001")])
        with self.assertRaises(ValueError):
            inv.add(make(inventory_number="PC-0001"))
        self.assertEqual(len(inv), 1, "дубликат не должен попасть в хранилище")

    def test_duplicate_check_is_case_insensitive(self) -> None:
        inv = Inventory([make(inventory_number="PC-0001")])
        with self.assertRaises(ValueError):
            inv.add(make(inventory_number="pc-0001"))

    def test_has_number_trims_and_ignores_case(self) -> None:
        inv = Inventory([make(inventory_number="PRN-0007")])
        self.assertTrue(inv.has_number("  prn-0007 "))
        self.assertFalse(inv.has_number("prn-0008"))

    def test_get_by_number_returns_record_or_none(self) -> None:
        inv = Inventory([make(inventory_number="MON-0001")])
        self.assertIsNotNone(inv.get_by_number("mon-0001"))
        self.assertIsNone(inv.get_by_number("nope"))

    def test_all_is_sorted_by_number(self) -> None:
        inv = Inventory([
            make(inventory_number="PC-0003"),
            make(inventory_number="PC-0001"),
            make(inventory_number="PC-0002"),
        ])
        numbers = [item.inventory_number for item in inv.all()]
        self.assertEqual(numbers, ["PC-0001", "PC-0002", "PC-0003"])

    def test_iteration_yields_sorted_records(self) -> None:
        inv = Inventory([make(inventory_number="B"), make(inventory_number="A")])
        self.assertEqual([i.inventory_number for i in inv], ["A", "B"])


class AddEquipmentScenarioTests(unittest.TestCase):
    """Сценарий пункта меню "Добавить запись" (main.add_equipment).

    input() подменяется последовательностью ответов, stdout — буфером,
    чтобы проверить сообщения пользователю и отсутствие исключений.
    """

    # Порядок ответов: номер, тип, наименование, кабинет, состояние,
    # дата поступления, ответственный.
    ANSWERS_OK = ["PC-0100", "1", "Системный блок", "204", "1", "", ""]

    def _run(self, answers: list[str]) -> tuple[Inventory, str]:
        inv = Inventory()
        out = io.StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(out):
            add_equipment(inv)
        return inv, out.getvalue()

    def test_successful_add(self) -> None:
        inv, output = self._run(self.ANSWERS_OK)
        self.assertEqual(len(inv), 1)
        item = inv.get_by_number("PC-0100")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.kind, "ПК")          # выбран по номеру 1 из KINDS
        self.assertEqual(item.state, "исправно")   # выбран по номеру 1 из STATES
        self.assertIn("успешно добавлена", output)

    def test_number_is_uppercased(self) -> None:
        inv, _ = self._run(["pc-0101", "1", "ПК", "204", "1", "", ""])
        self.assertIsNotNone(inv.get_by_number("PC-0101"))

    def test_empty_number_cancels(self) -> None:
        inv, output = self._run([""])
        self.assertEqual(len(inv), 0)
        self.assertIn("Отменено", output)

    def test_duplicate_number_is_reported_not_raised(self) -> None:
        inv = Inventory([make(inventory_number="PC-0100")])
        out = io.StringIO()
        # После отказа по дубликату main сразу выходит из функции,
        # поэтому ответы дальше не читаются.
        with patch("builtins.input", side_effect=["PC-0100"]), redirect_stdout(out):
            add_equipment(inv)  # не должно бросить исключение
        self.assertEqual(len(inv), 1)
        self.assertIn("уже существует", out.getvalue())

    def test_empty_name_cancels(self) -> None:
        inv, output = self._run(["PC-0102", "1", ""])
        self.assertEqual(len(inv), 0)
        self.assertIn("наименование обязательно", output)

    def test_empty_room_cancels(self) -> None:
        inv, output = self._run(["PC-0103", "1", "Системный блок", ""])
        self.assertEqual(len(inv), 0)
        self.assertIn("кабинет обязателен", output)

    def test_custom_kind_by_name(self) -> None:
        inv, _ = self._run(["PC-0104", "сервер", "Сервер", "301", "1", "", ""])
        item = inv.get_by_number("PC-0104")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.kind, "сервер")

    def test_invalid_state_is_reported_not_raised(self) -> None:
        inv, output = self._run(
            ["PC-0105", "1", "ПК", "204", "сломано", "", ""]
        )
        self.assertEqual(len(inv), 0)
        self.assertIn("Ошибка", output)  # ValueError поймано внутри функции

    def test_ctrl_c_does_not_crash(self) -> None:
        inv = Inventory()
        out = io.StringIO()
        with patch("builtins.input", side_effect=KeyboardInterrupt), \
                redirect_stdout(out):
            add_equipment(inv)  # не должно выбросить KeyboardInterrupt наружу
        self.assertEqual(len(inv), 0)

    def test_eof_does_not_crash(self) -> None:
        inv = Inventory()
        out = io.StringIO()
        with patch("builtins.input", side_effect=EOFError), redirect_stdout(out):
            add_equipment(inv)
        self.assertEqual(len(inv), 0)


class ShowInventoryScenarioTests(unittest.TestCase):
    """Пункт меню "Показать оборудование"."""

    def test_empty_inventory_prints_message(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            show_inventory(Inventory())
        self.assertIn("Справочник пуст", out.getvalue())

    def test_records_and_total_are_printed(self) -> None:
        inv = Inventory([make(inventory_number="PC-0001", name="Alpha"),
                         make(inventory_number="PC-0002", name="Beta")])
        out = io.StringIO()
        with redirect_stdout(out):
            show_inventory(inv)
        text = out.getvalue()
        self.assertIn("PC-0001", text)
        self.assertIn("PC-0002", text)
        self.assertIn("Всего записей: 2", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)