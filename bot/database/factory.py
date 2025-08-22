import os
from bot.database import pg, sqlite


def get_db():
    db_type = os.getenv('DB_TYPE', 'sqlite').lower()

    if db_type == 'postgres':
        return pg

    return sqlite