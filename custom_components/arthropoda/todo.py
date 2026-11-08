"""Takenlijst 'Onderhoud': wat vandaag (of eerder) moet gebeuren.

- Afvinken  = de handeling wordt in het dagboek genoteerd (bv. 'Gevoederd').
- Verwijderen = uitstellen tot morgen.
"""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .entity import HubEntity
from .tasks import Task, texts


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    async_add_entities([MaintenanceTodoList(entry.runtime_data.coordinator)])


class MaintenanceTodoList(HubEntity, TodoListEntity):
    """Eén takenlijst voor de hele collectie."""

    _attr_supported_features = (
        TodoListEntityFeature.UPDATE_TODO_ITEM | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "maintenance")

    def _summary(self, task: Task) -> str:
        t = texts(self.hass.config.language)
        if task.enclosure_id is not None:
            return f"{t[task.kind]}: {self.coordinator.task_target_name(task)}"
        snap = self.coordinator.data[task.animal_id]
        species = snap.bundle.species
        name = snap.animal.name
        if species and species.scientific_name not in name:
            name = f"{name} ({species.scientific_name})"
        return f"{t[task.kind]}: {name}"

    def _description(self, task: Task) -> str:
        t = texts(self.hass.config.language)
        days = (dt_util.now().date() - dt_util.as_local(task.due).date()).days
        return t["overdue"].format(days=days) if days > 0 else t["due_today"]

    @property
    def todo_items(self) -> list[TodoItem]:
        return [
            TodoItem(
                summary=self._summary(task),
                uid=task.uid,
                status=TodoItemStatus.NEEDS_ACTION,
                due=dt_util.as_local(task.due).date(),
                description=self._description(task),
            )
            for task in self.coordinator.due_tasks()
            if task.enclosure_id is not None or task.animal_id in self.coordinator.data
        ]

    def _task(self, uid: str | None) -> Task:
        for task in self.coordinator.all_tasks():
            if task.uid == uid:
                return task
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unknown_task")

    async def async_update_todo_item(self, item: TodoItem) -> None:
        task = self._task(item.uid)
        if item.status == TodoItemStatus.COMPLETED:
            await self.coordinator.async_complete_task(task)

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        tomorrow = dt_util.start_of_local_day() + timedelta(days=1)
        for uid in uids:
            task = self._task(uid)
            await self.coordinator.async_snooze_task(task, tomorrow)
