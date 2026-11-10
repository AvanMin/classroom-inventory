#!/usr/bin/env python3

from __future__ import annotations

import sys

from inventory import Equipment, Inventory, demo_inventory, KINDS, STATES

#: Пункты меню: (клавиша, название, спринт реализации).
#: Пункты 1, 2, 3, 4, 5 активны в Спринте 3.
MENU: tuple[tuple[str, str, str | None], ...] = (
    ("1", "Показать оборудование", None),
    ("2", "Добавить запись", None),
    ("3", "Найти оборудование", None),
    ("4", "Изменить запись", None),
    ("5", "Удалить запись", None),
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
    """Собрать строки простой ASCII-таблицы."""
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
    """Подробный вывод одной карточки оборудования."""
    print("  +---------------------------------------------------")
    print(f"  | Номер:         {item.inventory_number}")
    print(f"  | Тип:           {item.kind}")
    print(f"  | Наименование:  {item.name}")
    print(f"  | Кабинет:       {item.room}")
    print(f"  | Состояние:     {item.state}")
    print(f"  | Поступление:   {item.received_at_display}")
    print(f"  | Ответственный: {item.responsible or 'Не назначен'}")
    print("  +---------------------------------------------------")


def print_banner(inventory: Inventory) -> None:
    print("=" * 95)
    print("  СИСТЕМА УЧЁТА ИНВЕНТАРЯ КОМПЬЮТЕРНЫХ КЛАССОВ")
    print("  Спринт 3 - полный CRUD и поиск (роль LD)")
    print("=" * 95)
    print(f"  Записей в справочнике: {len(inventory)}")
    print("  Постоянное хранилище JSON появится в спринте 4.")


def print_menu() -> None:
    print()
    print(LINE)
    for key, title, sprint in MENU:
        note = f"  (будет в {sprint})" if sprint else ""
        print(f"  {key}. {title}{note}")
    print(LINE)


def show_inventory(inventory: Inventory) -> None:
    """Пункт 1: показать все записи."""
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


def add_equipment(inventory: Inventory) -> None:
    """Пункт 2: добавить новую запись."""
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


def find_equipment(inventory: Inventory) -> None:
    """Пункт 3: поиск по инвентарному номеру или кабинету."""
    print()
    print("ПОИСК ОБОРУДОВАНИЯ")
    print("  1. По инвентарному номеру")
    print("  2. По кабинету")
    print("  0. Назад в меню")

    try:
        sub_choice = input("Выберите режим поиска: ").strip()
        if sub_choice == "1":
            number = input("Введите инвентарный номер: ").strip()
            if not number:
                print("Номер не указан.")
                return
            item = inventory.get_by_number(number)
            if item is None:
                print(f"Запись с номером {number!r} не найдена.")
            else:
                print("\nНайдено оборудование:")
                print_equipment_card(item)

        elif sub_choice == "2":
            room = input("Введите номер или название кабинета: ").strip()
            if not room:
                print("Кабинет не указан.")
                return
            results = inventory.search_by_room(room)
            if not results:
                print(f"В кабинете {room!r} ничего не найдено.")
            else:
                print(f"\nНайдено записей: {len(results)}")
                for line in render_table(results):
                    print(line)
        elif sub_choice in {"0", ""}:
            return
        else:
            print("Неверный режим поиска.")
    except (EOFError, KeyboardInterrupt):
        print("\nОтменено.")


def edit_equipment(inventory: Inventory) -> None:
    """Пункт 4: изменение кабинета и/или состояния оборудования."""
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
        print("\nЗапись успешно обновлена:")
        print_equipment_card(updated)

    except (ValueError, KeyError) as e:
        print(f"Ошибка при обновлении: {e}")
    except (EOFError, KeyboardInterrupt):
        print("\nОтменено.")


def delete_equipment(inventory: Inventory) -> None:
    """Пункт 5: удаление записи с подтверждением."""
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

        confirm = input("\nВы уверены, что хотите удалить эту запись? (y/n / да/нет): ").strip().lower()
        if confirm in {"y", "yes", "да", "д"}:
            if inventory.delete(number):
                print(f"Запись {item.inventory_number} успешно удалена.")
            else:
                print("Не удалось удалить запись.")
        else:
            print("Удаление отменено пользователем.")

    except (EOFError, KeyboardInterrupt):
        print("\nОтменено.")


def main(argv: list[str] | None = None) -> int:
    """Точка входа приложения. Возвращает код завершения."""
    del argv
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

        if choice == "1":
            show_inventory(inventory)
            continue

        if choice == "2":
            add_equipment(inventory)
            continue

        if choice == "3":
            find_equipment(inventory)
            continue

        if choice == "4":
            edit_equipment(inventory)
            continue

        if choice == "5":
            delete_equipment(inventory)
            continue

        item = MENU_BY_KEY.get(choice)
        if item is None:
            print("Такого пункта нет. Введите число из меню.")
            continue

        title, sprint = item
        print(f'Раздел "{title}" ещё не реализован: он появится в {sprint}.')


if __name__ == "__main__":
    sys.exit(main())