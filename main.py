#!/usr/bin/env python3
"""Система учёта инвентаря компьютерных классов.

Спринт 1 (роль LD): каркас приложения - запуск, главное меню, вывод
демонстрационного справочника. Остальные пункты меню зарезервированы
и подключаются в следующих спринтах, чтобы структура проекта не
менялась при переходе от спринта к спринту.

Запуск:  python main.py
"""

from __future__ import annotations

import sys

from inventory import Equipment, Inventory, demo_inventory, KINDS, STATES

#: Пункты меню: (клавиша, название, спринт реализации).
#: ``None`` в третьем элементе означает, что пункт реализован.
MENU: tuple[tuple[str, str, str | None], ...] = (
    ("1", "Показать оборудование", None),
    ("2", "Добавить запись", None),
    ("3", "Найти оборудование", "спринте 3"),
    ("4", "Изменить запись", "спринте 3"),
    ("5", "Удалить запись", "спринте 3"),
    ("6", "Фильтр по кабинету/состоянию", "спринте 5"),
    ("0", "Выход", None),
)

MENU_BY_KEY = {key: (title, sprint) for key, title, sprint in MENU}

#: Колонки таблицы: (заголовок, атрибут записи, ширина).
COLUMNS: tuple[tuple[str, str, int], ...] = (
    ("Номер", "inventory_number", 10),
    ("Тип", "kind", 19),
    ("Наименование", "name", 34),
    ("Кабинет", "room", 8),
    ("Состояние", "state", 16),
)

LINE = "-" * 95


def shrink(text: str, width: int) -> str:
    """Обрезать значение до ширины колонки, сохранив выравнивание."""
    value = " ".join(str(text).split())
    if len(value) <= width:
        return value.ljust(width)
    return (value[: width - 3].rstrip() + "...").ljust(width)


def render_table(records: list[Equipment]) -> list[str]:
    """Собрать строки простой ASCII-таблицы (работает в любой кодировке)."""
    header = "  ".join(shrink(title, width) for title, _, width in COLUMNS)
    lines = [header, "-" * len(header)]
    for record in records:
        row = "  ".join(
            shrink(str(getattr(record, attribute)), width)
            for _, attribute, width in COLUMNS
        )
        lines.append(row)
    return lines


def print_banner(inventory: Inventory) -> None:
    print("=" * 95)
    print("  СИСТЕМА УЧЁТА ИНВЕНТАРЯ КОМПЬЮТЕРНЫХ КЛАССОВ")
    print("  Спринт 1 - каркас приложения (роль LD)")
    print("=" * 95)
    print(f"  Записей в демонстрационном справочнике: {len(inventory)}")
    print("  Источник данных: список DEMO_RECORDS в inventory.py")
    print("  Постоянное хранение в data/inventory.json появится в спринте 4.")


def print_menu() -> None:
    print()
    print(LINE)
    for key, title, sprint in MENU:
        note = f"  (будет в {sprint})" if sprint else ""
        print(f"  {key}. {title}{note}")
    print(LINE)


def show_inventory(inventory: Inventory) -> None:
    """Пункт 1: показать все записи на демонстрационных данных."""
    records = inventory.all()
    print()
    print("СПРАВОЧНИК ОБОРУДОВАНИЯ (демонстрационные данные)")
    print()
    if not records:
        print("Справочник пуст.")
        return
    for line in render_table(records):
        print(line)
    print()
    print(f"Всего записей: {len(records)}")

def add_equipment(inventory: Inventory) -> None:
    """Пункт 2: добавить новую запись с проверками."""
    print()
    print("ДОБАВЛЕНИЕ НОВОЙ ЗАПИСИ")
    print("Пустое поле или Ctrl+C — отмена.")
    print()

    try:
        number = input("Инвентарный номер: ").strip()
        if not number:
            print("Отменено: номер не может быть пустым.")
            return

        if inventory.has_number(number):
            print(f"Ошибка: запись с номером {number!r} уже существует.")
            return

        print("\nДоступные типы:")
        for i, kind in enumerate(KINDS, 1):
            print(f"  {i}. {kind}")
        kind_input = input("Тип оборудования (номер или название): ").strip()
        if not kind_input:
            print("Отменено.")
            return

        # Можно ввести номер из списка или название
        if kind_input.isdigit() and 1 <= int(kind_input) <= len(KINDS):
            kind = KINDS[int(kind_input) - 1]
        else:
            kind = kind_input

        name = input("Наименование: ").strip()
        if not name:
            print("Отменено: наименование обязательно.")
            return

        room = input("Кабинет: ").strip()
        if not room:
            print("Отменено: кабинет обязателен.")
            return

        print("\nДоступные состояния:")
        for i, state in enumerate(STATES, 1):
            print(f"  {i}. {state}")
        state_input = input("Состояние (номер или название): ").strip().lower()
        if not state_input:
            print("Отменено.")
            return

        if state_input.isdigit() and 1 <= int(state_input) <= len(STATES):
            state = STATES[int(state_input) - 1]
        else:
            state = state_input

        # Дополнительные поля (необязательные)
        received_at = input("Дата поступления (ГГГГ-ММ-ДД, можно пусто): ").strip()
        responsible = input("Ответственный (можно пусто): ").strip()

        equipment = Equipment(
            inventory_number=number.upper(),
            kind=kind,
            name=name,
            room=room,
            state=state,
            received_at=received_at,
            responsible=responsible,
        )

        inventory.add(equipment)
        print()
        print(f"Запись {equipment.inventory_number} успешно добавлена.")

    except ValueError as e:
        print(f"Ошибка: {e}")
    except (EOFError, KeyboardInterrupt):
        print("\nОтменено.")

def main(argv: list[str] | None = None) -> int:
    """Точка входа приложения. Возвращает код завершения."""
    del argv  # аргументы командной строки появятся в следующих спринтах
    inventory = demo_inventory()
    print_banner(inventory)

    while True:
        print_menu()
        try:
            choice = input("Выберите пункт: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            return 0

        if choice.lower() in {"0", "q", "выход"}:
            print("До встречи!")
            return 0

        if choice == "2":
            add_equipment(inventory)
            continue

        item = MENU_BY_KEY.get(choice)
        if item is None:
            print("Такого пункта нет. Введите число из меню.")
            continue

        title, sprint = item
        print(f'Раздел "{title}" ещё не реализован: он появится в {sprint}.')


if __name__ == "__main__":
    sys.exit(main())
