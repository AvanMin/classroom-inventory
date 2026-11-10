import json
import pytest
from pathlib import Path

from inventory import Equipment, Inventory
from storage import load_inventory, save_inventory


@pytest.fixture
def temp_json(tmp_path: Path) -> Path:
    """Фикстура, предоставляющая изолированный временный файл для каждого теста."""
    return tmp_path / "test_inventory.json"


@pytest.fixture
def sample_equipment() -> Equipment:
    return Equipment(
        inventory_number="QA-001",
        kind="ПК",
        name="Тестовый стенд QA",
        room="404",
        state="исправно"
    )


def test_load_missing_file(temp_json: Path):
    """Проверка: если файла нет, загружается пустой справочник без ошибок."""
    inventory = load_inventory(temp_json)
    assert len(inventory) == 0


def test_load_empty_file(temp_json: Path):
    """Проверка: если файл существует, но пуст, загружается пустой справочник."""
    temp_json.write_text("")
    inventory = load_inventory(temp_json)
    assert len(inventory) == 0


def test_load_corrupted_json(temp_json: Path):
    """Проверка: если JSON испорчен, программа не падает, а возвращает пустой справочник."""
    temp_json.write_text("{это_не_json: 123, broken")
    inventory = load_inventory(temp_json)
    assert len(inventory) == 0


def test_load_invalid_structure(temp_json: Path):
    """Проверка: если JSON валидный, но структура не соответствует ожиданиям (нет 'records')."""
    temp_json.write_text(json.dumps({"wrong_key": []}))
    inventory = load_inventory(temp_json)
    assert len(inventory) == 0


def test_save_and_load_success(temp_json: Path, sample_equipment: Equipment):
    """Проверка: успешное сохранение записи и её последующее чтение."""
    inv_write = Inventory()
    inv_write.add(sample_equipment)
    save_inventory(inv_write, temp_json)

    assert temp_json.exists(), "Файл данных должен быть создан после сохранения"

    inv_read = load_inventory(temp_json)
    assert len(inv_read) == 1

    loaded_item = inv_read.get_by_number("QA-001")
    assert loaded_item is not None
    assert loaded_item.name == "Тестовый стенд QA"
    assert loaded_item.room == "404"