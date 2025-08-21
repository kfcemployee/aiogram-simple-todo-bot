import asyncio
import datetime
import logging

from aiogram import Bot
from db import get_remind_tasks, upd_sent_reminder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.callbacks import cr_edit_callback

class Reminder:
    """Класс для рассылки упоминаний"""
    def __init__(self, bot: Bot, logger: logging.Logger):
        self.bot = bot  # Бот для отправки сообщений
        self.logger = logger  # Привязываем логгер

    async def start_(self, delay: int):
        self.logger.info('REMINDER STARTED')
        while True:
            r_tasks = await get_remind_tasks()

            for task in r_tasks:
                if task.get("reminder") == datetime.datetime.now().replace(second=0, microsecond=0):
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
                    await upd_sent_reminder(task.get("id"), True)
            await asyncio.sleep(delay)
