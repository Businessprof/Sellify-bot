from aiogram.fsm.state import State, StatesGroup


class AdminStockStates(StatesGroup):
    waiting_for_stock_items = State()  # Admin sends keys/accounts line-by-line


class AdminPriceStates(StatesGroup):
    waiting_for_new_price = State()


class AdminBroadcastStates(StatesGroup):
    waiting_for_broadcast_text = State()
