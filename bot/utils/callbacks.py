from aiogram.filters.callback_data import CallbackData
from aiogram import F
from aiogram.filters.callback_data import CallbackQueryFilter


class CreateTaskCB(CallbackData, prefix='cr_task'):
    """
    Класс для всех коллбэков, они строятся по следующему принципу: action:val:flag, где
        action: то, что добавляем во время коллбэка (reminder, priority, ...);
        val: выставляемое значение 0 или 1.
    """
    action: str
    val: str

class EditTaskCB(CallbackData, prefix='edit_task'):
    task_id: int
    action: str

def cr_create_callback(action: str, val: str) -> str:
    """Вспомогательная функция для создания коллбэка во время создания задачи"""
    return CreateTaskCB(action=action, val=val).pack()

def cr_edit_callback(task_id: int, action: str) -> str:
    """Вспомогательная функция для создания коллбэка во время редактирования задачи"""
    return EditTaskCB(task_id=task_id, action=action).pack()

def val_from_cb(c: str):
    return CreateTaskCB.unpack(c).val

def filter_cr_action(my: str) -> CallbackQueryFilter:
    return CreateTaskCB.filter(F.action.startswith(my))

def filter_edit_action(my: str) -> CallbackQueryFilter:
    return EditTaskCB.filter(F.action.endswith(my))

def task_id_from_edit(c: str):
    return EditTaskCB.unpack(c).task_id

def action_id_from_edit(c: str):
    return EditTaskCB.unpack(c).action
