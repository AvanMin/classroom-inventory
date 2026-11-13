#!/usr/bin/env python3
"""Консольное приложение учёта инвентаря.

Спринт 4 (роль LD): данные загружаются из data/inventory.json при старте
и сохраняются после каждой мутирующей операции (add / update / delete).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from inventory import Equipment, Inventory, KINDS, STATES, demo_inventory
from storage import DEFAULT_DATA_FILE, load_inventory, save_inventory

#: Пункты меню: (клавиша, название, спринт реализации).
MENU: tuple[tuple[str, str, str | None], ...] = (
    ("1", "Показать оборудование", None),
    ("2", "Добавить запись", None),
    ("3", "Найти оборудование", None),
    ("4", "Изменить запись", None),
    ("5", "Удалить запись", None),
    ("6", "Фильтр по кабинету/состоянию", None),
    ("0", "Выход", None),
)

MENU_BY_KEY = {key: (title, sprint) for key, title, sprint in MENU}

#: Колонки таблицы: (заголовок, атрибут модели, ширина).
COLUMNS: tuple[tuple[str, str, int], ...] = (
    ("Номер", "inventory_number", 10),
    ("Тип", "kind", 19),
    ("Наименование", "name", 30),
    ("Кабинет", "room", 8),
    ("Состояние", "state", 16),
    ("Поступление", "received_at_display", 12),
    ("Ответственный", "responsible", 20),
)

LINE = "-" * 95


def shrink(text: str, width: int) -> str:
    value = " ".join(str(text).split())
    if len(value) <= width:
        return value.ljust(width)
    return (value[: width - 3].rstrip() + "...").ljust(width)


def render_table(records: list[Equipment]) -> list[str]:
    header = "  ".join(shrink(title, width) for title, _, width in COLUMNS)
    lines = [header, "-" * len(header)]
    for record in records:
        row = "  ".join(
            shrink(str(getattr(record, attribute)), width)
            for _, attribute, width in COLUMNS
        )
        lines.append(row)
    return lines


def print_equipment_card(item: Equipment) -> None:
    print("  +---------------------------------------------------")
    print(f"  | Номер:         {item.inventory_number}")
    print(f"  | Тип:           {item.kind}")
    print(f"  | Наименование:  {item.name}")
    print(f"  | Кабинет:       {item.room}")
    print(f"  | Состояние:     {item.state}")
    print(f"  | Поступление:   {item.received_at_display}")
    print(f"  | Ответственный: {item.responsible or 'Не назначен'}")
    print("  +---------------------------------------------------")


def _show_search_results(results: list[Equipment]) -> None:
    """1 совпадение — карточкой, много — таблицей, 0 — сообщением."""
    print()
    if not results:
        print("Ничего не найдено.")
        return
    if len(results) == 1:
        print("Найдено оборудование:")
        print_equipment_card(results[0])
        return
    print(f"Найдено записей: {len(results)}")
    for line in render_table(results):
        print(line)


def print_banner(inventory: Inventory, data_file: Path) -> None:
    print("=" * 95)
    print("  СИСТЕМА УЧЁТА ИНВЕНТАРЯ КОМПЬЮТЕРНЫХ КЛАССОВ")
    print("=" * 95)
    print(f"  Записей в справочнике: {len(inventory)}")
    print(f"  Файл данных: {data_file}")


def print_menu() -> None:
    print()
    print(LINE)
    for key, title, sprint in MENU:
        note = f"  (будет в {sprint})" if sprint else ""
        print(f"  {key}. {title}{note}")
    print(LINE)


def show_inventory(inventory: Inventory) -> None:
    records = inventory.all()
    print()
    print("СПРАВОЧНИК ОБОРУДОВАНИЯ")
    print()
    if not records:
        print("Справочник пуст.")
        return
    for line in render_table(records):
        print(line)
    print()
    print(f"Всего записей: {len(records)}")


def _read_received_at() -> str:
    """Запросить дату поступления с проверкой формата ГГГГ-ММ-ДД."""
    while True:
        raw = input(
            "Дата поступления (ГГГГ-ММ-ДД, можно пусто): "
        ).strip()
        if not raw:
            return ""
        try:
            date.fromisoformat(raw)
        except ValueError:
            print("  Неверный формат даты. Пример: 2024-09-01. "
                  "Оставьте пусто, если дата неизвестна.")
            continue
        return raw


def _read_responsible() -> str:
    """Запросить ответственного; цифры в значении запрещены."""
    while True:
        raw = input(
            "Ответственный (только буквы, можно пусто): "
        ).strip()
        if not raw:
            return ""
        if any(ch.isdigit() for ch in raw):
            print("  Ответственный не должен содержать цифры. "
                  "Введите ФИО без цифр или оставьте пусто.")
            continue
        return raw


def add_equipment(inventory: Inventory, data_file: Path) -> None:
    print()
    print("ДОБАВЛЕНИЕ НОВОЙ ЗАПИСИ")
    print("Пустое поле или Ctrl+C — отмена.")
    print()

    try:
        print("Доступные типы:")
        for i, kind in enumerate(KINDS, 1):
            print(f"  {i}. {kind}")
        kind_input = input("Тип оборудования (номер или название): ").strip()
        if not kind_input:
            print("Отменено.")
            return
        if kind_input.isdigit() and 1 <= int(kind_input) <= len(KINDS):
            kind = KINDS[int(kind_input) - 1]
        else:
            kind = kind_input

        suggested_number = inventory.suggest_next_number(kind)
        number = input(
            f"Инвентарный номер [Enter для {suggested_number}]: "
        ).strip()
        if not number:
            number = suggested_number

        if inventory.has_number(number):
            print(f"Ошибка: запись с номером {number!r} уже существует.")
            return

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

        received_at = _read_received_at()
        responsible = _read_responsible()

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
        save_inventory(inventory, data_file)
        print()
        print(f"Запись {equipment.inventory_number} успешно добавлена и сохранена.")
    except ValueError as e:
        print(f"Ошибка: {e}")
    except (EOFError, KeyboardInterrupt):
        print("\nОтменено.")


def find_equipment(inventory: Inventory) -> None:
    """Пункт 3: поиск по номеру (умный) и по кабинету."""
    print()
    print("ПОИСК ОБОРУДОВАНИЯ")
    print("  1. Поиск по номеру (точный/частичный, при отсутствии — по всем полям)")
    print("  2. Поиск по кабинету")
    print("  0. Назад в меню")

    try:
        sub_choice = input("Выберите режим поиска: ").strip()
        if sub_choice in {"0", ""}:
            return
        if sub_choice not in {"1", "2"}:
            print("Неверный режим поиска.")
            return

        if sub_choice == "1":
            query = input("Что ищем: ").strip()
            if not query:
                print("Пустой запрос.")
                return
            # 1) точное совпадение по номеру → карточка
            exact = inventory.get_by_number(query)
            if exact is not None:
                print("\nНайдено оборудование:")
                print_equipment_card(exact)
                return
            # 2) частичное совпадение по номеру → таблица
            by_number = inventory.search_by_number(query)
            if by_number:
                _show_search_results(by_number)
                return
            # 3) не нашли по номеру — ищем по всем полям
            _show_search_results(inventory.search(query))
            return

        # sub_choice == "2" — по кабинету
        room = input("Введите номер или название кабинета: ").strip()
        if not room:
            print("Кабинет не указан.")
            return
        _show_search_results(inventory.search_by_room(room))
    except (EOFError, KeyboardInterrupt):
        print("\nОтменено.")


def edit_equipment(inventory: Inventory, data_file: Path) -> None:
    print()
    print("ИЗМЕНЕНИЕ ЗАПИСИ ОБОРУДОВАНИЯ")
    try:
        number = input("Введите инвентарный номер для изменения: ").strip()
        if not number:
            print("Номер не указан.")
            return
        item = inventory.get_by_number(number)
        if item is None:
            print(f"Запись с номером {number!r} не найдена.")
            return

        print("\nТекущие данные:")
        print_equipment_card(item)
        print("\n(Нажмите Enter, чтобы оставить значение без изменений)")

        new_room = input(f"Новый кабинет (сейчас: {item.room}): ").strip()

        print("\nДопустимые состояния:")
        for i, s in enumerate(STATES, 1):
            print(f"  {i}. {s}")
        state_input = input(f"Новое состояние (сейчас: {item.state}): ").strip().lower()

        new_state = None
        if state_input:
            if state_input.isdigit() and 1 <= int(state_input) <= len(STATES):
                new_state = STATES[int(state_input) - 1]
            else:
                new_state = state_input

        if not new_room and not new_state:
            print("Изменения не внесены.")
            return

        updated = inventory.update(
            number=item.inventory_number,
            new_room=new_room or None,
            new_state=new_state or None,
        )
        save_inventory(inventory, data_file)
        print("\nЗапись успешно обновлена и сохранена:")
        print_equipment_card(updated)
    except (ValueError, KeyError) as e:
        print(f"Ошибка при обновлении: {e}")
    except (EOFError, KeyboardInterrupt):
        print("\nОтменено.")


def delete_equipment(inventory: Inventory, data_file: Path) -> None:
    print()
    print("УДАЛЕНИЕ ЗАПИСИ ОБОРУДОВАНИЯ")
    try:
        number = input("Введите инвентарный номер для удаления: ").strip()
        if not number:
            print("Номер не указан.")
            return
        item = inventory.get_by_number(number)
        if item is None:
            print(f"Запись с номером {number!r} не найдена.")
            return

        print("\nЗапись для удаления:")
        print_equipment_card(item)

        confirm = input(
            "\nВы уверены, что хотите удалить эту запись? (y/n / да/нет): "
        ).strip().lower()
        if confirm in {"y", "yes", "да", "д"}:
            if inventory.delete(number):
                save_inventory(inventory, data_file)
                print(f"Запись {item.inventory_number} успешно удалена и сохранена.")
            else:
                print("Не удалось удалить запись.")
        else:
            print("Удаление отменено пользователем.")
    except (EOFError, KeyboardInterrupt):
        print("\nОтменено.")


def filter_equipment(inventory: Inventory) -> None:
    """Пункт 6: фильтр по кабинету и/или состоянию."""
    print()
    print("ФИЛЬТР ОБОРУДОВАНИЯ")
    print("Можно указать только кабинет, только состояние или оба параметра.")
    print("Пустое значение — не учитывать этот критерий.")
    print()

    try:
        room = input("Кабинет (можно пусто): ").strip()

        print("\nДоступные состояния:")
        for i, s in enumerate(STATES, 1):
            print(f"  {i}. {s}")
        state_input = input("Состояние (номер, название или пусто): ").strip().lower()

        state = None
        if state_input:
            if state_input.isdigit() and 1 <= int(state_input) <= len(STATES):
                state = STATES[int(state_input) - 1]
            else:
                state = state_input

        if not room and not state:
            print("Не указан ни один критерий фильтрации.")
            return

        results = inventory.filter_by_room_and_state(
            room=room or None,
            state=state,
        )

        print()
        if not results:
            print("По заданным условиям ничего не найдено.")
            return

        print(f"Найдено записей: {len(results)}")
        for line in render_table(results):
            print(line)

    except (EOFError, KeyboardInterrupt):
        print("\nОтменено.")
    except ValueError as e:
        print(f"Ошибка: {e}")


def main(argv: list[str] | None = None) -> int:
    """Точка входа. Возвращает код завершения."""
    del argv

    data_file = DEFAULT_DATA_FILE
    inventory = load_inventory(data_file)

    if len(inventory) == 0:
        print("[main] Файл данных пуст. Заполняем демонстрационным справочником.")
        inventory = demo_inventory()
        try:
            save_inventory(inventory, data_file)
        except OSError:
            print("[main] Не удалось сохранить демо-данные — работаем только в памяти.")

    print_banner(inventory, data_file)

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

        if choice == "1":
            show_inventory(inventory)
            continue
        if choice == "2":
            add_equipment(inventory, data_file)
            continue
        if choice == "3":
            find_equipment(inventory)
            continue
        if choice == "4":
            edit_equipment(inventory, data_file)
            continue
        if choice == "5":
            delete_equipment(inventory, data_file)
            continue
        if choice == "6":
            filter_equipment(inventory)
            continue

        item = MENU_BY_KEY.get(choice)
        if item is None:
            print("Такого пункта нет. Введите число из меню.")
            continue

        title, sprint = item
        print(f'Раздел "{title}" ещё не реализован: он появится в {sprint}.')


if __name__ == "__main__":
    sys.exit(main())