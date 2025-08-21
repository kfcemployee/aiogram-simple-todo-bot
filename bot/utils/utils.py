import datetime
import asyncpg

def handle_task(task: asyncpg.Record) -> str:
    """Работа с asyncpg записью и её вывод в виде отформатированной строки."""
    opts = [f'<b>{task.get("name")}</b>',
            f'<i>{task.get("description")}</i>',
            f'Статус: {("\u274C", "\u2705")[task.get("is_completed")]}',
            f'Приоритет: {("\u274C", "\u2705")[task.get("priority")]}',
            f'Дата создания: {task.get("created_at").strftime("%d.%m.%Y %H:%M")}']

    if task.get('reminder') and task['reminder'] >= datetime.datetime.now():
        opts += [f"Напоминание: {task['reminder'].strftime('%d-%m %H:%M')}{("\u274C", "\u2705")[task.get("reminder_sent")]}"]
    else:
        opts += [
            "Напоминание: не установлено"]

    return '\n'.join(opts)


class InvalidDateError(Exception):
    pass

def validate_date(tm: datetime.datetime):
    if datetime.datetime.now() > tm:
        raise InvalidDateError()

def validate_date_in(tm: str):
    from re import fullmatch
    if not fullmatch(r'[0-9]{2}:[0-9]{2}', tm):
        raise ValueError()
