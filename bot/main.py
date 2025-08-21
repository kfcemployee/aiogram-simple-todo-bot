import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.utils.fsm_states import (AddTask, EditReminder,
                                  PostponeReminder, get_states_group) # Группа состояний
from db import *  # Импортируем все операции с БД
from bot.utils.utils import *  # Импортируем все инструменты
from reminder import Reminder  # Импортируем класс для напоминаний
from bot.utils.menu import menu  # Импортируем меню
from utils.callbacks import (cr_create_callback, cr_edit_callback,
                             filter_cr_action, val_from_cb,
                             filter_edit_action, task_id_from_edit,
                             action_id_from_edit)  # Импортируем функции для создания коллбэков

load_dotenv()
bt = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher()

create_router = Router()  # Роутер для обработки коллбэков во время создания записи
edit_router = Router()  # Роутер для обработки коллбэков во время редактирования записи
c_router = Router()  # Роутер для обработки коллбэков во время показа чего-либо

reminder_check_delay = 60  # Задержка проверки напоминаний (1 минута)
logging.basicConfig(  # конфиг логгера
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

cancel_fsm_button = InlineKeyboardButton(text='Отмена❌', callback_data=cr_create_callback('cancel_add', ''))

@c_router.message(Command("reminders"))
async def view_reminders(m: Message, user: int = None):
    """Показать напоминания для конкретного юзера."""
    keyboard = InlineKeyboardBuilder()
    edit_ = True
    try:
        if user is None:
            user = m.from_user.id
            edit_ = False

        r_tasks = [task for task in await get_remind_tasks_for_user(user)
                   if task.get('reminder') > datetime.datetime.now() - datetime.timedelta(seconds=1)]
        if r_tasks:
            text = ("Вот список ваших напоминаний.\n"
                    "Нажмите на напоминание, чтобы удалить его.")
            for task in r_tasks:
                keyboard.button(text=f"{task.get('name')} - {task.get('reminder').strftime("%d-%m %H:%M")}",
                                callback_data=cr_edit_callback(task['id'], 'delete_reminder')).adjust(1)
        else:
            text = 'У вас нет напоминаний.'

        if edit_:
            await m.edit_text(text, reply_markup=keyboard.as_markup())
        else:
            await m.answer(text, reply_markup=keyboard.as_markup())
    except Exception as e:
        logger.error(f'Getting user reminders error: {e}')
        await m.answer('Ошибка при получении ваших напоминаний.')

@edit_router.callback_query(F.data.endswith('delete_reminder'))
async def del_reminder(c: CallbackQuery):
    """Удалить напоминание."""
    try:
        await del_reminder_for_task(int(task_id_from_edit(c.data)))
        await c.answer('Успешно удалено.')
        await view_reminders(c.message, user=c.from_user.id)
    except Exception as e:
        logger.error(f'Deleting reminder error: {e}')
        await c.message.answer('Не получилось удалить это напоминание.')

@create_router.message(Command("add"))
async def add_task(m: Message, state: FSMContext):
    """Добавление задания > реакция на команду /add > добавление имени."""
    if await state.get_state() is not None:
        await state.clear()

    await m.answer('Введите название задачи.',
                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[[cancel_fsm_button]]))

    await state.set_state(AddTask.received_name)
    await state.update_data()

@create_router.message(AddTask.received_name)
async def add_desc(m: Message, state: FSMContext):
    """Добавление задания > добавление описания к заданию."""

    await state.update_data({'name': m.text})
    await state.set_state(AddTask.received_desc)

    await m.answer('Введите описание задачи.',
                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[[cancel_fsm_button]]))

@create_router.message(AddTask.received_desc)
async def add_priority(m: Message, state: FSMContext):
    """Добавление задания > добавление приоритета к заданию"""

    await state.update_data({'desc': m.text})
    await state.set_state(AddTask.received_priority)

    await m.answer(text='Установите приоритет (задачи с приоритетом показываются первыми).',
                   reply_markup=InlineKeyboardMarkup(
                       inline_keyboard=[
                           [InlineKeyboardButton(text='Установить приоритет',
                                                 callback_data=cr_create_callback('priority', '1'))],
                           [InlineKeyboardButton(text='Без приоритета',
                                                 callback_data=cr_create_callback('priority', ''))],
                           [cancel_fsm_button],
                       ])
                   )

@edit_router.callback_query(filter_edit_action('edit_r'))
@create_router.callback_query(AddTask.received_priority, filter_cr_action('priority'))
async def add_reminder(c: CallbackQuery | Message, state: FSMContext):
    """Добавление задания > добавление напоминания к заданию."""
    cs = await get_states_group(state)

    if cs and cs == AddTask:
        txt = ("Введите дату, если хотите получать уведомления.\n"
                  "Дата должна быть в формате <i>день.месяц</i> (например 01.06)")
        mk = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text='Сегодня',
                                      callback_data=cr_create_callback('reminder', 'today')),
                 InlineKeyboardButton(text='Завтра', callback_data=cr_create_callback('reminder', 'tomorrow'))],
                [InlineKeyboardButton(text="Не создавать напоминание",
                                      callback_data=cr_create_callback('cancel_reminder', ' '))],
                [cancel_fsm_button]
            ]
        )

        priority = await state.get_value('priority')

        if priority is None:
            priority = bool(val_from_cb(c.data))
            c = c.message

        await state.update_data({'priority': priority})
        await state.set_state(AddTask.received_reminder_dt)
    else:
        txt = ("Введите новую дату напоминания.\n"
                  "Дата должна быть в формате <i>день.месяц</i> (например 01.06)")
        mk = InlineKeyboardBuilder()

        task_id = await state.get_value('task_id')

        if task_id is None:
            task_id = task_id_from_edit(c.data)
            c = c.message

        old_rem = (await get_task_by_id(task_id))[-1].get('reminder')

        if old_rem:
            mk.button(text='Оставить тот же день.', callback_data=cr_edit_callback(
                int(task_id), 'leave_day'))
        mk.button(text='Сегодня', callback_data=cr_edit_callback(
            int(task_id),"today"))
        mk.button(text='Завтра', callback_data=cr_edit_callback(
            int(task_id),"tomorrow"))
        mk.button(text='Отменить редактирование', callback_data=cancel_fsm_button.callback_data)

        mk = mk.adjust(1, 2, 1).as_markup()

        await state.set_state(EditReminder.received_reminder_dt)
        await state.update_data({'old_reminder': old_rem,
                                 'task_id': task_id})

    await c.answer(text=txt, reply_markup=mk, parse_mode="HTML")

@create_router.callback_query(AddTask.received_reminder_dt, filter_cr_action('reminder'))
@edit_router.callback_query(EditReminder.received_reminder_dt)
async def user_rem_date_from_temp(c: CallbackQuery, state: FSMContext):
    """Добавление задания > обработка сегодня/завтра."""

    date = None
    match c.data.split(':')[-1]:
        case 'today':
            date = datetime.datetime.today().replace(year=datetime.datetime.now().year)
        case 'tomorrow':
            date = datetime.datetime.today().replace(year=datetime.datetime.now().year) + datetime.timedelta(days=1)
        case 'leave_day':
            date = await state.get_value('old_reminder')
            if date:
                date = datetime.datetime(date.year, date.month, date.day)

    await user_rem_date(c.message, state, date)

@create_router.message(AddTask.received_reminder_dt)
@edit_router.message(EditReminder.received_reminder_dt)
async def user_rem_date(c: Message, state: FSMContext, templ=None):
    """Добавление задания > добавление времени для напоминания и внесение его в fsm."""
    cs = await get_states_group(state)
    try:
        if templ is None:
            templ = datetime.datetime(datetime.datetime.now().year, *map(int, c.text.split('.')))

        await state.update_data({'reminder': templ})
        await state.set_state(cs.received_reminder_time)
        await c.answer(text='Введите время напоминания.\n'
                            'Время должно быть в формате часы:минуты (например 15:30)')
    except ValueError:
        await c.answer('Неверная дата или формат.\nПопробуйте снова.')
        await state.set_state(cs.received_reminder_dt)
    except Exception as e:
        logger.error(e)

@create_router.callback_query(AddTask.received_reminder_dt, filter_cr_action('cancel_reminder'))
async def finish_with_no_reminder(c: CallbackQuery, state: FSMContext):
    try:
        await cr_task(user_id=c.from_user.id, **await state.get_data())
    except Exception as e:
        logger.error(f'ERROR WITH INSERT INTO DB, NO REMINDER : {e}')

    await c.message.answer(text=r'Задача <b>успешно</b> создана! Введите /list чтобы увидеть ваши задачи.',
                           parse_mode='HTML')
    await state.clear()

@create_router.message(AddTask.received_reminder_time)
@edit_router.message(EditReminder.received_reminder_time)
async def finish_creation(c: Message, state: FSMContext):
    cs = await get_states_group(state)
    try:
        validate_date_in(c.text)
        cin = [*map(int, c.text.split(':'))]
        tm : datetime.datetime = (await state.get_value('reminder')).replace(hour=cin[0], minute=cin[1],
                                                                             second=0,
                                                                             microsecond=0)
        validate_date(tm)
        await state.update_data({'reminder': tm})
        if cs == AddTask:
            await cr_task(user_id=c.from_user.id, **await state.get_data())
            await c.answer(text=r'Задача <b>успешно</b> создана! Введите /list чтобы увидеть ваши задачи.',
                           parse_mode='HTML')
            logger.info(f'USER {c.from_user.id} CREATED TASK.')
        else:
            await edit_reminder(reminder=await state.get_value('reminder'),
                                task_id=await state.get_value('task_id'))
            await upd_sent_reminder(await state.get_value('task_id'), False)
            await c.answer('Напоминание успешно отредактировано.')
        await state.clear()
    except InvalidDateError:
        await c.answer('Ошибка добавления: дата вашего напоминания раньше текущей даты.'
                       '\nПопробуйте снова.')
        await add_reminder(c, state)
    except ValueError:
        await c.answer('Неверное время или формат.\nПопробуйте снова.')
        await add_reminder(c, state)
    except Exception as e:
        logger.error(e)

@c_router.callback_query(filter_cr_action('cancel_add'))
async def cancel_add(c: CallbackQuery, state: FSMContext):
    if await state.get_state():
        await state.clear()

    logger.info(f"USER {c.from_user.id} CANCELLED CREATING A TASK")
    await c.message.answer('Вы отменили создание задачи.')

@c_router.message(Command("list"))
async def show_list(m: Message, from_: bool = False,  state: FSMContext = None,):
    if state and await state.get_state():
        if not from_:
            cs = get_states_group(state)
            if cs == AddTask:
                text = 'добавление задачи.'
            else:
                text = 'редактирование задачи.'

            await m.answer(f'Вы отменили {text}')
        await state.clear()

    tasks = await get_tasks(m.chat.id)

    if not tasks:
        text = "Вы ещё не создали ни одной задачи, введите /add, чтобы начать создание."
        keyboard = None
    else:
        text = 'Вот список ваших задач:'
        keyboard = InlineKeyboardBuilder()
        for task in tasks:
            txt = (task.get("name"), ("\u2705", "❌")[not task.get("is_completed")])
            keyboard.button(text=' '.join(txt), callback_data=cr_edit_callback(task['id'], 'c_show_task'))
        keyboard.adjust(1)

    if from_:
        await m.edit_text(text, reply_markup=keyboard.as_markup()) if keyboard else await m.edit_text(text)
    else:
        await m.answer(text, reply_markup=keyboard.as_markup()) if keyboard else await m.answer(text)


@c_router.message(Command("listuncompleted"))
async def show_unc_tasks(m: Message, from_: bool = False):
    tasks = await get_uncompleted_tasks(m.chat.id)

    if not tasks:
        text = ("У вас пока нет невыполненных задач.\n"
                "Введите /list, чтобы посмотреть все задачи или /add, чтобы добавить задачу.")
        keyboard = None
    else:
        text = 'Вот список ваших невыполненных задач:'
        keyboard = InlineKeyboardBuilder()
        for task in tasks:
            txt = (task.get("name"), "❌")
            keyboard.button(text=' '.join(txt), callback_data=cr_edit_callback(task['id'], 'u_show_task'))
        keyboard.adjust(1)

    if from_:
        await m.edit_text(text, reply_markup=keyboard.as_markup()) if keyboard else await m.edit_text(text)
    else:
        await m.answer(text, reply_markup=keyboard.as_markup()) if keyboard else await m.answer(text)


@c_router.callback_query(filter_edit_action('show_task'))
async def show_exact_task(c: CallbackQuery):
    task = await get_task_by_id(task_id := int(task_id_from_edit(c.data)))

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text='Удалить задачу🗑️', callback_data=cr_edit_callback(task_id, 'del_task'))
    if not task[-1].get('is_completed'):
        keyboard.button(text='Задача выполнена✅', callback_data=cr_edit_callback(task_id, 'upd_task_st'))
    keyboard.button(text='Назад⬅️', callback_data=f'back-to-list_{action_id_from_edit(c.data).split('_')[0]}')

    if (not task[-1].get('is_completed')) and task[-1].get('reminder_sent') == False:
        keyboard.button(text='Редактировать напоминание🕔', callback_data=cr_edit_callback(task_id, 'edit_r'))

    await c.message.edit_text(handle_task(*task), reply_markup=keyboard.adjust(2, 1, 1).as_markup(), parse_mode='HTML')


@c_router.callback_query(F.data.startswith("back-to-list"))
async def back_to_list(c: CallbackQuery):
    if c.data.split('_')[-1] == 'u':
        await show_unc_tasks(c.message, True)
    else:
        await show_list(c.message, True)

@edit_router.callback_query(filter_edit_action('del_task'))
async def del_task(c: CallbackQuery):
    try:
        await del_task_by_id(int(task_id_from_edit(c.data)))
        await c.answer('Успешно удалено✅')
        await show_list(c.message, True)
    except Exception as e:
        logger.warning(e)

@edit_router.callback_query(filter_edit_action('upd_task_st'))
async def ready_task(c: CallbackQuery):
    try:
        await upd_ready(int(task_id_from_edit(c.data)))
        await c.answer('Успешно обновлено✅')
        await show_exact_task(c)
    except Exception as e:
        logger.warning(e)

@edit_router.callback_query(filter_edit_action('postpone_task_r'))
async def postpone_task(c: CallbackQuery, state: FSMContext):
    if await state.get_state():
        await state.clear()

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text='На час', callback_data=cr_edit_callback(task_id_from_edit(c.data), 'postpone_hr'))
    keyboard.button(text='На день', callback_data=cr_edit_callback(task_id_from_edit(c.data), 'postpone_day'))
    keyboard.button(text='Изменить напоминание', callback_data=cr_edit_callback(task_id_from_edit(c.data), 'edit_r'))

    await state.set_state(PostponeReminder.received_reminder_dt)
    await state.update_data({'old_reminder': (await get_task_by_id(task_id_from_edit(c.data)))[-1].get('reminder'),
                             'task_id': task_id_from_edit(c.data)})
    await c.message.answer(text='Выберите, что вам нужно:', reply_markup=keyboard.adjust(2, 1).as_markup())

@edit_router.callback_query(PostponeReminder.received_reminder_dt)
async def pp_reminder_temp(c: CallbackQuery, state: FSMContext):
    delta = action_id_from_edit(c.data).split('_')[-1]
    date = await state.get_value('old_reminder')

    match delta:
        case 'hr':
            date += datetime.timedelta(hours=1)
        case 'day':
            date += datetime.timedelta(days=1)

    await edit_reminder(reminder=date, task_id=int(await state.get_value('task_id')))
    await bt.delete_message(c.message.chat.id, c.message.message_id)
    await upd_sent_reminder(task_id=int(await state.get_value('task_id')), to=False)
    await c.message.answer('Напоминание отложено.')

@c_router.message(CommandStart())
async def start(m: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()

    await m.answer('Это простой To-Do бот с уведомлениями.\n'
                   'Введите /add чтобы добавить новую задачу.')

@c_router.message()
async def any_message(m: Message, state: FSMContext):
    if await state.get_state():
        await m.answer('Неверный ввод. Попробуйте снова.')
        await state.set_state(await state.get_state())
    else:
        await m.reply('Не понимаю, что вы написали.\n'
                      'Введите / чтобы увидеть меню или /start, чтобы перезапустить бота.')

async def start_reminder():
    await Reminder(bt, logger).start_(reminder_check_delay)

async def start_bt():
    dp.include_routers(edit_router, create_router, c_router)
    await bt.set_my_commands(menu)
    await dp.start_polling(bt)

async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(start_bt())
        tg.create_task(start_reminder())

asyncio.run(main())