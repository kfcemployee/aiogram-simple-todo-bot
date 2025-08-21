from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

class AddTask(StatesGroup):
    """Группа состояний для создания нового задания"""
    received_name = State()
    received_desc = State()
    received_priority = State()
    received_reminder_dt = State()
    received_reminder_time = State()
    received_exc = State()

class EditReminder(StatesGroup):
    received_reminder_dt = State()
    received_reminder_time = State()

class PostponeReminder(StatesGroup):
    received_reminder_dt = State()
    received_reminder_time = State()

async def get_states_group(state: FSMContext):

    cur_states = await state.get_state()
    # print(cur_states)

    if cur_states is None:
        return None
    if cur_states.startswith('AddTask'):
        return AddTask
    elif cur_states.startswith('EditReminder'):
        return EditReminder

    return None
