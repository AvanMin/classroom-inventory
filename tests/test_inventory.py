import pytest
from inventory import Equipment, Inventory, demo_inventory, STATES, KINDS


def test_demo_inventory_dod_count():
    """Проверка Definition of Done: в демонстрационных данных должно быть не менее 5 записей."""
    inv = demo_inventory()
    assert len(inv) >= 5
    assert len(inv.all()) >= 5


def test_demo_inventory_sorting():
    """Проверка сортировки по инвентарному номеру."""
    inv = demo_inventory()
    records = inv.all()
    numbers = [item.inventory_number for item in records]
    assert numbers == sorted(numbers)


def test_equipment_valid_creation():
    """Проверка создания корректной записи оборудования."""
    item = Equipment(
        inventory_number="TEST-001",
        kind="ПК",
        name="Тестовый системник",
        room="101",
        state="исправно",
        received_at="2023-01-01",
        responsible="Иванов И. И.",
    )
    assert item.inventory_number == "TEST-001"
    assert item.received_at_display == "01.01.2023"


def test_equipment_empty_required_fields_raises_error():
    """Проверка, что пустые обязательные поля вызывают ValueError."""
    with pytest.raises(ValueError, match="Поле 'name' обязательно"):
        Equipment(
            inventory_number="TEST-002",
            kind="ПК",
            name="   ",  # пробелы вместо имени
            room="101",
            state="исправно",
        )


def test_equipment_invalid_state_raises_error():
    """Проверка, что недопустимый статус вызывает ValueError."""
    with pytest.raises(ValueError, match="Недопустимое состояние"):
        Equipment(
            inventory_number="TEST-003",
            kind="ПК",
            name="Монитор",
            room="101",
            state="сломано_совсем",
        )


def test_equipment_serialization_dict():
    """Проверка сериализации в словарь и десериализации (from_dict / to_dict)."""
    original = Equipment(
        inventory_number="PC-9999",
        kind="ПК",
        name="Сервер",
        room="Серверная",
        state="исправно",
        received_at="2022-10-15",
        responsible="Админ А. А.",
    )
    data_dict = original.to_dict()
    restored = Equipment.from_dict(data_dict)

    assert restored.inventory_number == original.inventory_number
    assert restored.name == original.name
    assert restored.state == original.state