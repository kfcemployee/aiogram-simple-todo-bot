import asyncio
import datetime
import logging

from aiogram import Bot
from database.factory import get_db
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.callbacks import cr_edit_callback
from utils.utils import if_str_to_date

db = get_db()

class Reminder:
    """Класс для рассылки упоминаний"""
    def __init__(self, bot: Bot, logger: logging.Logger):
        self.bot = bot  # Бот для отправки сообщений
        self.logger = logger  # Привязываем логгер

    async def start_(self, delay: int):
        self.logger.info('REMINDER STARTED')
        while True:
            r_tasks = await db.get_remind_tasks()

            for task in r_tasks:
                cur_tm = if_str_to_date(task.get("reminder"))

                if cur_tm == datetime.datetime.now().replace(second=0, microsecond=0):
                    cb_data_ready = cr_edit_callback(task['id'], 'upd_task_st')
                    cb_data_pp = cr_edit_callback(task['id'], 'postpone_task_r')

                    await self.bot.send_message(task.get("user_id"),
                                                text=f"Напоминаю вам сделать <b>{task.get("name")}</b>.",
                                                reply_markup=InlineKeyboardMarkup(
                                                    inline_keyboard=[[InlineKeyboardButton(text="Уже готово✅",
                                                                                           callback_data=cb_data_ready),
                                                                      InlineKeyboardButton(text="Отложить",
                                                                                           callback_data=cb_data_pp)
                                                                      ]]
                                                ), parse_mode="HTML")
                    self.logger.info(f"TASK {task.get('id')} WAS REMINDED")
                    await db.upd_sent_reminder(task.get("id"), True)
            await asyncio.sleep(delay)
