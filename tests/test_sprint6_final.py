"""Финальные автотесты Спринта 6 (роль QA).

Покрывают:
  - полный CRUD
  - поиск и фильтрацию
  - сохранение/загрузку JSON
  - обработку ошибок файла
  - регрессию основных сценариев
"""

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from contextlib import redirect_stdout

from inventory import Equipment, Inventory, STATES, demo_inventory
from storage import load_inventory, save_inventory
from main import (
    show_inventory,
    add_equipment,
    find_equipment,
    edit_equipment,
    delete_equipment,
    filter_equipment,
)


def make(**overrides) -> Equipment:
    data = dict(
        inventory_number="PC-9001",
        kind="ПК",
        name="Тестовый системный блок",
        room="101",
        state="исправно",
    )
    data.update(overrides)
    return Equipment(**data)


# =====================================================================
# Модель и хранилище в памяти
# =====================================================================

class InventoryCoreTests(unittest.TestCase):
    def test_add_and_get(self):
        inv = Inventory()
        inv.add(make())
        self.assertEqual(len(inv), 1)
        self.assertIsNotNone(inv.get_by_number("PC-9001"))

    def test_duplicate_rejected(self):
        inv = Inventory([make()])
        with self.assertRaises(ValueError):
            inv.add(make())

    def test_update_room_and_state(self):
        inv = Inventory([make()])
        updated = inv.update("PC-9001", new_room="305", new_state="требует ремонта")
        self.assertEqual(updated.room, "305")
        self.assertEqual(updated.state, "требует ремонта")

    def test_delete_existing(self):
        inv = Inventory([make(), make(inventory_number="MON-0001")])
        self.assertTrue(inv.delete("PC-9001"))
        self.assertIsNone(inv.get_by_number("PC-9001"))
        self.assertEqual(len(inv), 1)

    def test_delete_missing(self):
        inv = Inventory([make()])
        self.assertFalse(inv.delete("NO-SUCH"))

    def test_search_by_room(self):
        inv = Inventory([
            make(inventory_number="A", room="204"),
            make(inventory_number="B", room="305"),
            make(inventory_number="C", room="204"),
        ])
        results = inv.search_by_room("204")
        self.assertEqual(len(results), 2)

    def test_filter_by_state(self):
        inv = Inventory([
            make(inventory_number="A", state="исправно"),
            make(inventory_number="B", state="требует ремонта"),
            make(inventory_number="C", state="исправно"),
        ])
        results = inv.filter_by_state("исправно")
        self.assertEqual(len(results), 2)

    def test_filter_by_room_and_state(self):
        inv = Inventory([
            make(inventory_number="A", room="204", state="исправно"),
            make(inventory_number="B", room="204", state="требует ремонта"),
            make(inventory_number="C", room="305", state="исправно"),
        ])
        results = inv.filter_by_room_and_state(room="204", state="исправно")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].inventory_number, "A")


# =====================================================================
# Хранение JSON
# =====================================================================

class StorageTests(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.json"
            inv = Inventory([
                make(inventory_number="PC-0001"),
                make(inventory_number="MON-0001", kind="монитор", name="Монитор"),
            ])
            save_inventory(inv, path)
            loaded = load_inventory(path)
            self.assertEqual(len(loaded), 2)
            self.assertIsNotNone(loaded.get_by_number("PC-0001"))
            self.assertIsNotNone(loaded.get_by_number("MON-0001"))

    def test_load_missing_file(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "no_file.json"
            inv = load_inventory(path)
            self.assertEqual(len(inv), 0)

    def test_load_empty_file(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.json"
            path.write_text("", encoding="utf-8")
            inv = load_inventory(path)
            self.assertEqual(len(inv), 0)

    def test_load_broken_json(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text("{not valid json", encoding="utf-8")
            inv = load_inventory(path)
            self.assertEqual(len(inv), 0)

    def test_load_skips_bad_records(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "partial.json"
            payload = {
                "records": [
                    {
                        "inventory_number": "PC-0001",
                        "type": "ПК",
                        "name": "Нормальный",
                        "room": "101",
                        "state": "исправно",
                    },
                    {
                        "inventory_number": "BAD",
                        "type": "ПК",
                        "name": "",          # пустое имя — ошибка
                        "room": "101",
                        "state": "исправно",
                    },
                ]
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            inv = load_inventory(path)
            self.assertEqual(len(inv), 1)
            self.assertIsNotNone(inv.get_by_number("PC-0001"))


# =====================================================================
# Сценарии меню
# =====================================================================

class MenuScenarioTests(unittest.TestCase):
    def test_show_inventory(self):
        inv = Inventory([make(inventory_number="PC-0001", name="Alpha")])
        out = io.StringIO()
        with redirect_stdout(out):
            show_inventory(inv)
        text = out.getvalue()
        self.assertIn("PC-0001", text)
        self.assertIn("Alpha", text)

    def test_add_equipment_success(self):
        inv = Inventory()
        answers = ["PC-0100", "1", "Системный блок", "204", "1", "", ""]
        out = io.StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(out):
            # data_file не сохраняем реально — подменяем
            with patch("main.save_inventory"):
                add_equipment(inv, Path("dummy.json"))
        self.assertEqual(len(inv), 1)
        self.assertIn("успешно добавлена", out.getvalue())

    def test_find_by_number(self):
        inv = Inventory([make(inventory_number="PC-0001", name="Системник")])
        out = io.StringIO()
        with patch("builtins.input", side_effect=["1", "PC-0001"]), redirect_stdout(out):
            find_equipment(inv)
        self.assertIn("Найдено оборудование", out.getvalue())
        self.assertIn("Системник", out.getvalue())

    def test_find_missing(self):
        inv = Inventory()
        out = io.StringIO()
        with patch("builtins.input", side_effect=["1", "NO-SUCH"]), redirect_stdout(out):
            find_equipment(inv)
        self.assertIn("не найдена", out.getvalue())

    def test_edit_equipment(self):
        inv = Inventory([make(inventory_number="PC-0001", room="204")])
        out = io.StringIO()
        with patch("builtins.input", side_effect=["PC-0001", "305", ""]), \
             patch("main.save_inventory"), redirect_stdout(out):
            edit_equipment(inv, Path("dummy.json"))
        item = inv.get_by_number("PC-0001")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.room, "305")

    def test_delete_confirmed(self):
        inv = Inventory([make(inventory_number="PC-0001")])
        out = io.StringIO()
        with patch("builtins.input", side_effect=["PC-0001", "да"]), \
             patch("main.save_inventory"), redirect_stdout(out):
            delete_equipment(inv, Path("dummy.json"))
        self.assertIsNone(inv.get_by_number("PC-0001"))
        self.assertIn("успешно удалена", out.getvalue())

    def test_delete_cancelled(self):
        inv = Inventory([make(inventory_number="PC-0001")])
        out = io.StringIO()
        with patch("builtins.input", side_effect=["PC-0001", "нет"]), redirect_stdout(out):
            delete_equipment(inv, Path("dummy.json"))
        self.assertIsNotNone(inv.get_by_number("PC-0001"))
        self.assertIn("отменено", out.getvalue().lower())

    def test_filter_equipment(self):
        inv = Inventory([
            make(inventory_number="A", room="204", state="исправно"),
            make(inventory_number="B", room="305", state="исправно"),
        ])
        out = io.StringIO()
        with patch("builtins.input", side_effect=["204", "1"]), redirect_stdout(out):
            filter_equipment(inv)
        text = out.getvalue()
        self.assertIn("Найдено записей: 1", text)
        self.assertIn("A", text)


# =====================================================================
# Регрессия демо-данных
# =====================================================================

class DemoDataTests(unittest.TestCase):
    def test_demo_has_enough_records(self):
        inv = demo_inventory()
        self.assertGreaterEqual(len(inv), 5)

    def test_demo_sorted(self):
        inv = demo_inventory()
        numbers = [item.inventory_number for item in inv.all()]
        self.assertEqual(numbers, sorted(numbers))


if __name__ == "__main__":
    unittest.main(verbosity=2)