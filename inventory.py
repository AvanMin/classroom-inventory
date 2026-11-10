"""Модель инвентарной записи и демонстрационные данные.

Спринт 3 (роль LD): реализованы методы поиска по кабинету,
редактирования состояния/кабинета и удаления записей.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Iterable, Iterator

#: Допустимые состояния оборудования (согласовано с PO).
STATES: tuple[str, ...] = ("исправно", "требует ремонта", "списано")

#: Допустимые типы оборудования.
KINDS: tuple[str, ...] = (
    "ПК",
    "ноутбук",
    "монитор",
    "принтер",
    "МФУ",
    "сканер",
    "проектор",
    "интерактивная доска",
    "ИБП",
    "коммутатор",
    "другое",
)

#: Поля, без которых запись не имеет смысла.
REQUIRED_FIELDS: tuple[str, ...] = (
    "inventory_number",
    "kind",
    "name",
    "room",
    "state",
)


@dataclass(frozen=True, slots=True)
class Equipment:
    """Одна инвентарная запись.

    Объект неизменяемый: редактирование создаёт новую запись через replace.
    """

    inventory_number: str
    kind: str
    name: str
    room: str
    state: str
    received_at: str = ""  # дата в формате ISO (YYYY-MM-DD)
    responsible: str = ""

    def __post_init__(self) -> None:
        for field_name in REQUIRED_FIELDS:
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Поле {field_name!r} обязательно")
        if self.state not in STATES:
            raise ValueError(
                f"Недопустимое состояние {self.state!r}; "
                f"ожидается одно из: {', '.join(STATES)}"
            )

    @property
    def received_at_display(self) -> str:
        """Дата поступления в привычном виде ДД.ММ.ГГГГ."""
        if not self.received_at:
            return "-"
        try:
            return date.fromisoformat(self.received_at).strftime("%d.%m.%Y")
        except ValueError:
            return self.received_at

    def to_dict(self) -> dict[str, str]:
        """Запись в формате будущего JSON-файла (спринт 4)."""
        return {
            "inventory_number": self.inventory_number,
            "type": self.kind,
            "name": self.name,
            "room": self.room,
            "state": self.state,
            "received_at": self.received_at,
            "responsible": self.responsible,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Equipment":
        """Создать запись из словаря JSON-файла (спринт 4)."""
        if not isinstance(payload, dict):
            raise ValueError("Запись должна быть объектом JSON")

        def text(key: str) -> str:
            value = payload.get(key, "")
            if value is None:
                return ""
            if not isinstance(value, str):
                raise ValueError(f"Поле {key!r} должно быть строкой")
            return " ".join(value.split())

        number = text("inventory_number").upper()
        kind = text("type")
        name = text("name")
        room = text("room")
        state = text("state").lower()
        if not all((number, kind, name, room, state)):
            raise ValueError("Не заполнены обязательные поля записи")

        return cls(
            inventory_number=number,
            kind=kind,
            name=name,
            room=room,
            state=state,
            received_at=text("received_at"),
            responsible=text("responsible"),
        )


class Inventory:
    """Набор инвентарных записей в памяти."""

    def __init__(self, records: Iterable[Equipment] = ()) -> None:
        self._records: list[Equipment] = list(records)

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterator[Equipment]:
        return iter(self.all())

    def has_number(self, number: str) -> bool:
        """Проверить, существует ли запись с таким инвентарным номером."""
        normalized = number.strip().upper()
        return any(item.inventory_number.upper() == normalized for item in self._records)

    def get_by_number(self, number: str) -> Equipment | None:
        """Найти запись по инвентарному номеру. None — если не найдена."""
        normalized = number.strip().upper()
        if not normalized:
            return None
        for item in self._records:
            if item.inventory_number.upper() == normalized:
                return item
        return None

    def search_by_room(self, room: str) -> list[Equipment]:
        """Поиск записей по номеру/названию кабинета (без учета регистра)."""
        target = room.strip().lower()
        if not target:
            return []
        return [
            item for item in self._records
            if target in item.room.strip().lower()
        ]

    def add(self, equipment: Equipment) -> None:
        """Добавить новую запись. Если номер уже существует — ValueError."""
        if self.has_number(equipment.inventory_number):
            raise ValueError(
                f"Запись с номером {equipment.inventory_number!r} уже существует"
            )
        self._records.append(equipment)

    def update(
        self,
        number: str,
        new_room: str | None = None,
        new_state: str | None = None,
    ) -> Equipment:
        """Изменить кабинет и/или состояние записи.

        Создаёт обновлённую копию записи (frozen=True) и заменяет её в списке.
        """
        item = self.get_by_number(number)
        if item is None:
            raise KeyError(f"Оборудование с номером {number!r} не найдено")

        updates: dict[str, str] = {}
        if new_room is not None and new_room.strip():
            updates["room"] = new_room.strip()

        if new_state is not None and new_state.strip():
            state_clean = new_state.strip().lower()
            if state_clean not in STATES:
                raise ValueError(
                    f"Недопустимое состояние {new_state!r}. Ожидается: {', '.join(STATES)}"
                )
            updates["state"] = state_clean

        if not updates:
            return item

        updated_item = replace(item, **updates)
        idx = self._records.index(item)
        self._records[idx] = updated_item
        return updated_item

    def delete(self, number: str) -> bool:
        """Удалить запись по инвентарному номеру.

        Возвращает True в случае успеха, False если запись не найдена.
        """
        item = self.get_by_number(number)
        if item is not None:
            self._records.remove(item)
            return True
        return False

    def all(self) -> list[Equipment]:
        """Все записи, отсортированные по инвентарному номеру."""
        return sorted(self._records, key=lambda item: item.inventory_number)


DEMO_RECORDS: tuple[Equipment, ...] = (
    Equipment(
        inventory_number="PC-0001",
        kind="ПК",
        name="Системный блок Dell OptiPlex 3070",
        room="204",
        state="исправно",
        received_at="2021-09-01",
        responsible="Иванов И. И.",
    ),
    Equipment(
        inventory_number="PC-0002",
        kind="ПК",
        name="Системный блок HP ProDesk 400 G6",
        room="204",
        state="требует ремонта",
        received_at="2020-11-12",
        responsible="Иванов И. И.",
    ),
    Equipment(
        inventory_number="MON-0001",
        kind="монитор",
        name="Монитор Dell P2219H, 22 дюйма",
        room="204",
        state="исправно",
        received_at="2021-09-01",
        responsible="Иванов И. И.",
    ),
    Equipment(
        inventory_number="PRN-0001",
        kind="принтер",
        name="Принтер HP LaserJet Pro M404dn",
        room="305",
        state="исправно",
        received_at="2022-02-14",
        responsible="Петрова А. С.",
    ),
    Equipment(
        inventory_number="MFP-0001",
        kind="МФУ",
        name="МФУ Kyocera ECOSYS M2040dn",
        room="101",
        state="требует ремонта",
        received_at="2019-09-02",
        responsible="Сидоров В. П.",
    ),
    Equipment(
        inventory_number="PRJ-0001",
        kind="проектор",
        name="Проектор Epson EB-X51",
        room="305",
        state="исправно",
        received_at="2023-01-10",
        responsible="Петрова А. С.",
    ),
    Equipment(
        inventory_number="NB-0001",
        kind="ноутбук",
        name="Ноутбук Lenovo ThinkPad E14",
        room="112",
        state="исправно",
        received_at="2024-03-18",
        responsible="Кузнецова М. В.",
    ),
    Equipment(
        inventory_number="IWB-0001",
        kind="интерактивная доска",
        name="Интерактивная доска Smart SB680",
        room="101",
        state="списано",
        received_at="2015-09-01",
        responsible="Сидоров В. П.",
    ),
)


def demo_inventory() -> Inventory:
    """Справочник на демонстрационных данных."""
    return Inventory(DEMO_RECORDS)