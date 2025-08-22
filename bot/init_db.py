# Файл для того, чтобы создать бд, если её нет в зависимости от того, какая субд выбрана в .env

from database.factory import *
import asyncpg
import asyncio

db = get_db()
async def init():
    if db == pg:
        db_conf = {
            "user": os.getenv('DB_USER'),
            "password": os.getenv('DB_PASSWORD'),
            "database": os.getenv('DB_NAME'),
            "host": os.getenv('DB_HOST'),
            "port": os.getenv('DB_PORT')
        }  # параметры соединения
        conn = await asyncpg.connect(**db_conf)
        try:
            await conn.execute('CREATE DATABASE todo_db')
            print("База данных создана!")

        except asyncpg.exceptions.DuplicateDatabaseError:
            print("База данных уже существует!")
        except Exception as e:
            print(f"Ошибка при создании БД: {e}")
        finally:
            await conn.close()
    else:
        db_path = os.getenv('SQLITE_PATH') or 'todo_db.db'  # Пробуем получить путь к бд через SQLITE_PATH
        if not os.path.exists(db_path):
            with open('todo_db.db', 'w') as file:
                pass

asyncio.run(init())
