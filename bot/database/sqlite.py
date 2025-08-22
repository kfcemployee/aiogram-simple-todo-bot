import pathlib

import aiosqlite
import os
from dotenv import load_dotenv
from datetime import datetime

async def get_connection():
    try:
        load_dotenv()
        db_path = os.getenv('SQLITE_PATH') or 'todo_db.db' # Пробуем получить путь к бд через SQLITE_PATH
        if not os.path.exists(db_path):
            with open('todo_db.db', 'w') as file:
                pass

        conn = await aiosqlite.connect(db_path)
        return conn
    except Exception as e:
        print(e)  # Потом сделаю отдельный логгер для бд

async def init_db():
    base_dir = pathlib.Path(__file__).parent.parent
    sql_path = base_dir / 'database' / 'scripts' / 'create_tasks_table.sql'
    conn = await get_connection()
    try:
        with open(sql_path) as file:
            sql_q = file.read()

        async with conn.cursor() as crs:
            await crs.executescript(
                sql_q
            )
            await conn.commit()
    finally:
        await conn.close()

async def get_tasks(user_id: int):
    conn = await get_connection()
    try:
        conn.row_factory = aiosqlite.Row
        async with conn.cursor() as crs:
            await crs.execute(
                "SELECT * FROM tasks WHERE user_id = ? ORDER BY priority DESC, id",
                (user_id, )
            )

            return [dict(task) for task in await crs.fetchall()]
    except Exception as e:
        print(e)
    finally:
        await conn.close()

async def get_uncompleted_tasks(user_id: int):
    """Получение данных о всех невыполненных заданиях по user id."""
    conn = await get_connection()
    try:
        conn.row_factory = aiosqlite.Row
        async with conn.cursor() as crs:
            await crs.execute(
                "SELECT * FROM tasks WHERE user_id = ? AND is_completed = False ORDER BY priority DESC, id",
                (user_id,)
            )

            return [dict(task) for task in await crs.fetchall()]
    except Exception as e:
        print(e)
    finally:
        await conn.close()

async def cr_task(user_id: int, name: str, desc: str, priority: bool = False, reminder: datetime = None):
    """Создание нового задания."""
    conn = await get_connection()
    try:
        async with conn.cursor() as crs:
            await crs.execute(
                'INSERT INTO tasks (user_id, name, description, priority, reminder)'
                'VALUES (?, ?, ?, ?, ?)',
                (user_id, name, desc, priority, reminder))
            await conn.commit()
    finally:
        await conn.close()


async def del_task_by_id(task_id: int):
    """Удаление задания по его id."""
    conn = await get_connection()

    try:
        async with conn.cursor() as crs:
            await crs.execute(
                'DELETE FROM tasks WHERE id = $1',
                (task_id,)
            )
            await conn.commit()
    except Exception as e:
        print(f'ERROR WITH GETTING A TASK: {e}')
    finally:
        await conn.close()

async def del_reminder_for_task(task_id: int):
    """Удаление напоминания для конкретного задания по id задания."""
    conn = await get_connection()

    try:
        async with conn.cursor() as crs:
            await crs.execute(
                'UPDATE tasks SET reminder = NULL WHERE id = ?',
                (task_id,)
            )
            await conn.commit()
    except Exception as e:
        print(f'ERROR WITH GETTING A TASK: {e}')
    finally:
        await conn.close()

async def upd_ready(task_id: int):
    """Обновить готовность задания по его id."""
    conn = await get_connection()
    try:
        async with conn.cursor() as crs:
            await crs.execute(
                "UPDATE tasks SET is_completed = True, reminder = NULL WHERE id = $1",
                (task_id,)
            )
            await conn.commit()
    except Exception as e:
        print(f'ERROR WITH GETTING A TASK: {e}')
    finally:
        await conn.close()

async def edit_reminder(reminder: datetime, task_id: int):
    """Обновить напоминание задания по его id."""
    conn = await get_connection()

    try:
        async with conn.cursor() as crs:
            await crs.execute(
                'UPDATE tasks SET reminder = ?, reminder_sent = False WHERE id = ?',
                (reminder, task_id,)
            )
            await conn.commit()
    except Exception as e:
        print(f'ERROR WITH GETTING A TASK: {e}')
    finally:
        await conn.close()

async def get_task_by_id(task_id: int):
    """Получить задание по его id."""
    conn = await get_connection()

    try:
        conn.row_factory = aiosqlite.Row
        async with conn.cursor() as crs:
            await crs.execute(
                "SELECT * FROM tasks WHERE id = ? ORDER BY priority DESC, id",
                (task_id, )
            )
            return [dict(task) for task in await crs.fetchall()]
    except Exception as e:
        print(f'ERROR WITH GETTING A TASK: {e}')
    finally:
        await conn.close()

async def get_remind_tasks():
    """Получение заданий, на которые установлены напоминания."""
    conn = await get_connection()
    try:
        conn.row_factory = aiosqlite.Row
        async with conn.cursor() as crs:
            await crs.execute(
                "SELECT * FROM tasks WHERE reminder IS NOT NULL AND reminder_sent = false",
            )
            tasks = await crs.fetchall()
            return [dict(task) for task in tasks]
    finally:
        await conn.close()


async def get_remind_tasks_for_user(user_id: int):
    """Получение напоминаний для конкретного пользователя по его id."""
    conn = await get_connection()
    try:
        conn.row_factory = aiosqlite.Row
        async with conn.cursor() as crs:
            await crs.execute(
                "SELECT * FROM tasks WHERE user_id = ? AND reminder IS NOT NULL AND reminder_sent = false",
                (user_id, ))
            tasks = await crs.fetchall()
            return [dict(task) for task in tasks]
    finally:
        await conn.close()

async def upd_sent_reminder(task_id: int, to: bool = True):
    """Обновить информацию о том, пришло ли напоминание."""
    conn = await get_connection()

    try:
        async with conn.cursor() as crs:
            await crs.execute(
                "UPDATE tasks SET reminder_sent = ? WHERE id = ?",
                (to, task_id,)
            )
            await conn.commit()
    except Exception as e:
        print(f'ERROR WITH GETTING A TASK: {e}')
    finally:
        await conn.close()
