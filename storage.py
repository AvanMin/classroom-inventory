"""Постоянное хранение инвентаря в JSON-файле.

Спринт 4 (роль LD): загрузка и сохранение данных, обработка
отсутствующего, пустого и повреждённого файла.
"""

from __future__ import annotations

import json
from pathlib import Path

from inventory import Equipment, Inventory

#: Путь к файлу данных по умолчанию.
DEFAULT_DATA_FILE = Path("data/inventory.json")


def _ensure_data_dir(filepath: Path) -> None:
    """Создать родительскую папку файла, если её нет."""
    filepath.parent.mkdir(parents=True, exist_ok=True)


def load_inventory(filepath: Path = DEFAULT_DATA_FILE) -> Inventory:
    """Загрузить инвентарь из JSON-файла.

    Правила:
    - файла нет → пустой Inventory (без ошибок);
    - файл пустой или повреждён → пустой Inventory + предупреждение;
    - некорректная запись → пропускается с предупреждением, остальные
      корректные записи загружаются.
    """
    if not filepath.exists():
        print(f"[storage] Файл {filepath} не найден — создаём пустой справочник.")
        return Inventory()

    try:
        raw_text = filepath.read_text(encoding="utf-8").strip()
    except OSError as exc:
        print(f"[storage] Не удалось прочитать {filepath}: {exc}. Используем пустой справочник.")
        return Inventory()

    if not raw_text:
        print(f"[storage] Файл {filepath} пуст — используем пустой справочник.")
        return Inventory()

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print(f"[storage] Ошибка формата JSON в {filepath}: {exc}. Данные не загружены.")
        return Inventory()

    if not isinstance(payload, dict) or "records" not in payload:
        print(f"[storage] Неожиданная структура файла {filepath}. Данные не загружены.")
        return Inventory()

    records_raw = payload["records"]
    if not isinstance(records_raw, list):
        print(f"[storage] Поле 'records' должно быть списком. Данные не загружены.")
        return Inventory()

    records: list[Equipment] = []
    for index, item in enumerate(records_raw, 1):
        try:
            records.append(Equipment.from_dict(item))
        except ValueError as exc:
            print(f"[storage] Пропущена запись #{index}: {exc}")

    return Inventory(records)


def save_inventory(
    inventory: Inventory,
    filepath: Path = DEFAULT_DATA_FILE,
) -> None:
    """Сохранить инвентарь в JSON-файл (атомарно через временный файл)."""
    _ensure_data_dir(filepath)

    payload = {"records": [item.to_dict() for item in inventory.all()]}
    tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")

    try:
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(filepath)
    except OSError as exc:
        print(f"[storage] Не удалось сохранить данные в {filepath}: {exc}")
        # Убираем временный файл, если он остался.
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise