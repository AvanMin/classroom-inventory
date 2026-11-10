"""Автотесты спринта 3 (роль QA).

Проверяем:
  * поиск по инвентарному номеру и по кабинету;
  * изменение кабинета и состояния;
  * удаление с подтверждением и отменой;
  * обработку несуществующих номеров;
  * отсутствие аварийного завершения при ошибках ввода.
"""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from inventory import Equipment, Inventory, STATES
from main import (
    show_inventory,
    find_equipment,
    edit_equipment,
    delete_equipment,
)


def make(**overrides) -> Equipment:
    """Корректная запись с возможностью переопределить поля."""
    data = dict(
        inventory_number="PC-9001",
        kind="ПК",
        name="Тестовый системный блок",
        room="101",
        state="исправно",
    )
    data.update(overrides)
    return Equipment(**data)


# ---------------------------------------------------------------------------
# Тесты модели и хранилища
# ---------------------------------------------------------------------------

class InventorySearchTests(unittest.TestCase):
    """Поиск по номеру и по кабинету."""

    def setUp(self) -> None:
        self.inv = Inventory([
            make(inventory_number="PC-0001", room="204", state="исправно"),
            make(inventory_number="MON-0001", room="305", state="требует ремонта"),
            make(inventory_number="PRN-0001", room="204", state="исправно"),
        ])

    def test_get_existing_number(self) -> None:
        item = self.inv.get_by_number("PC-0001")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.room, "204")

    def test_get_number_case_insensitive_and_trimmed(self) -> None:
        item = self.inv.get_by_number("  pc-0001  ")
        self.assertIsNotNone(item)

    def test_get_missing_number_returns_none(self) -> None:
        self.assertIsNone(self.inv.get_by_number("NO-SUCH"))

    def test_get_empty_number_returns_none(self) -> None:
        self.assertIsNone(self.inv.get_by_number(""))
        self.assertIsNone(self.inv.get_by_number("   "))

    def test_search_by_room_exact(self) -> None:
        results = self.inv.search_by_room("204")
        numbers = sorted(item.inventory_number for item in results)
        self.assertEqual(numbers, ["PC-0001", "PRN-0001"])

    def test_search_by_room_case_insensitive(self) -> None:
        results = self.inv.search_by_room("  204  ")
        self.assertEqual(len(results), 2)

    def test_search_by_room_not_found(self) -> None:
        results = self.inv.search_by_room("999")
        self.assertEqual(results, [])

    def test_search_by_room_empty(self) -> None:
        self.assertEqual(self.inv.search_by_room(""), [])
        self.assertEqual(self.inv.search_by_room("   "), [])


class InventoryUpdateTests(unittest.TestCase):
    """Изменение кабинета и состояния."""

    def setUp(self) -> None:
        self.inv = Inventory([
            make(inventory_number="PC-0001", room="204", state="исправно"),
        ])

    def test_update_room(self) -> None:
        updated = self.inv.update("PC-0001", new_room="305")
        self.assertEqual(updated.room, "305")
        self.assertEqual(updated.state, "исправно")
        # Проверяем, что в хранилище тоже обновилось
        item = self.inv.get_by_number("PC-0001")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.room, "305")

    def test_update_state(self) -> None:
        updated = self.inv.update("PC-0001", new_state="требует ремонта")
        self.assertEqual(updated.state, "требует ремонта")
        self.assertEqual(updated.room, "204")

    def test_update_both(self) -> None:
        updated = self.inv.update("PC-0001", new_room="112", new_state="списано")
        self.assertEqual(updated.room, "112")
        self.assertEqual(updated.state, "списано")

    def test_update_missing_number_raises_keyerror(self) -> None:
        with self.assertRaises(KeyError):
            self.inv.update("NO-SUCH", new_room="101")

    def test_update_invalid_state_raises_valueerror(self) -> None:
        with self.assertRaises(ValueError):
            self.inv.update("PC-0001", new_state="сломано")

    def test_update_empty_values_does_nothing(self) -> None:
        original = self.inv.get_by_number("PC-0001")
        updated = self.inv.update("PC-0001", new_room="", new_state="")
        self.assertEqual(updated.room, original.room)
        self.assertEqual(updated.state, original.state)


class InventoryDeleteTests(unittest.TestCase):
    """Удаление записей."""

    def setUp(self) -> None:
        self.inv = Inventory([
            make(inventory_number="PC-0001"),
            make(inventory_number="MON-0001"),
        ])

    def test_delete_existing_returns_true(self) -> None:
        result = self.inv.delete("PC-0001")
        self.assertTrue(result)
        self.assertIsNone(self.inv.get_by_number("PC-0001"))
        self.assertEqual(len(self.inv), 1)

    def test_delete_missing_returns_false(self) -> None:
        result = self.inv.delete("NO-SUCH")
        self.assertFalse(result)
        self.assertEqual(len(self.inv), 2)

    def test_delete_case_insensitive(self) -> None:
        result = self.inv.delete("  pc-0001  ")
        self.assertTrue(result)
        self.assertEqual(len(self.inv), 1)


# ---------------------------------------------------------------------------
# Сценарные тесты интерфейса (main.py)
# ---------------------------------------------------------------------------

class FindEquipmentScenarioTests(unittest.TestCase):
    """Пункт меню «Найти оборудование»."""

    def setUp(self) -> None:
        self.inv = Inventory([
            make(inventory_number="PC-0001", room="204", name="Системник"),
            make(inventory_number="MON-0001", room="305", name="Монитор"),
        ])

    def _run(self, answers: list[str]) -> str:
        out = io.StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(out):
            find_equipment(self.inv)
        return out.getvalue()

    def test_find_by_number_existing(self) -> None:
        output = self._run(["1", "PC-0001"])
        self.assertIn("Найдено оборудование", output)
        self.assertIn("PC-0001", output)
        self.assertIn("Системник", output)

    def test_find_by_number_missing(self) -> None:
        output = self._run(["1", "NO-SUCH"])
        self.assertIn("не найдена", output)

    def test_find_by_number_empty(self) -> None:
        output = self._run(["1", ""])
        self.assertIn("Номер не указан", output)

    def test_find_by_room_existing(self) -> None:
        output = self._run(["2", "204"])
        self.assertIn("Найдено записей: 1", output)
        self.assertIn("PC-0001", output)

    def test_find_by_room_missing(self) -> None:
        output = self._run(["2", "999"])
        self.assertIn("ничего не найдено", output)

    def test_find_cancel(self) -> None:
        output = self._run(["0"])
        self.assertNotIn("Найдено", output)


class EditEquipmentScenarioTests(unittest.TestCase):
    """Пункт меню «Изменить запись»."""

    def setUp(self) -> None:
        self.inv = Inventory([
            make(inventory_number="PC-0001", room="204", state="исправно"),
        ])

    def _run(self, answers: list[str]) -> str:
        out = io.StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(out):
            edit_equipment(self.inv)
        return out.getvalue()

    def test_edit_room_success(self) -> None:
        # номер, новый кабинет, состояние (Enter = без изменений)
        output = self._run(["PC-0001", "305", ""])
        self.assertIn("успешно обновлена", output)
        item = self.inv.get_by_number("PC-0001")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.room, "305")

    def test_edit_state_success(self) -> None:
        output = self._run(["PC-0001", "", "2"])  # 2 = "требует ремонта"
        self.assertIn("успешно обновлена", output)
        item = self.inv.get_by_number("PC-0001")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.state, "требует ремонта")

    def test_edit_missing_number(self) -> None:
        output = self._run(["NO-SUCH"])
        self.assertIn("не найдена", output)

    def test_edit_no_changes(self) -> None:
        output = self._run(["PC-0001", "", ""])
        self.assertIn("Изменения не внесены", output)


class DeleteEquipmentScenarioTests(unittest.TestCase):
    """Пункт меню «Удалить запись»."""

    def setUp(self) -> None:
        self.inv = Inventory([
            make(inventory_number="PC-0001", name="Системник"),
            make(inventory_number="MON-0001"),
        ])

    def _run(self, answers: list[str]) -> str:
        out = io.StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(out):
            delete_equipment(self.inv)
        return out.getvalue()

    def test_delete_confirmed(self) -> None:
        output = self._run(["PC-0001", "да"])
        self.assertIn("успешно удалена", output)
        self.assertIsNone(self.inv.get_by_number("PC-0001"))
        self.assertEqual(len(self.inv), 1)

    def test_delete_cancelled(self) -> None:
        output = self._run(["PC-0001", "нет"])
        self.assertIn("отменено", output.lower())
        self.assertIsNotNone(self.inv.get_by_number("PC-0001"))
        self.assertEqual(len(self.inv), 2)

    def test_delete_missing_number(self) -> None:
        output = self._run(["NO-SUCH"])
        self.assertIn("не найдена", output)
        self.assertEqual(len(self.inv), 2)

    def test_delete_empty_number(self) -> None:
        output = self._run([""])
        self.assertIn("Номер не указан", output)


class RegressionTests(unittest.TestCase):
    """Регрессия: просмотр продолжает работать."""

    def test_show_inventory(self) -> None:
        inv = Inventory([
            make(inventory_number="PC-0001", name="Alpha"),
            make(inventory_number="PC-0002", name="Beta"),
        ])
        out = io.StringIO()
        with redirect_stdout(out):
            show_inventory(inv)
        text = out.getvalue()
        self.assertIn("PC-0001", text)
        self.assertIn("PC-0002", text)
        self.assertIn("Всего записей: 2", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)