from aiogram.dispatcher.filters.state import StatesGroup, State


class NewItem(StatesGroup):
    category = State()
    name = State()
    photo = State()
    description = State()
    caption = State()
    price = State()
    confirm = State()


class Order(StatesGroup):
    order = State()


class DelItem(StatesGroup):
    choice = State()
    confirm = State()
    finish = State()


class Delete(StatesGroup):
    confirm = State()


class NewBasket(StatesGroup):
    append = State()
    add_additives = State()
    additives = State()
    confirm_additives = State()


class Confirm(StatesGroup):
    start = State()
    method = State()
    time = State()
    confirm_time = State()
    phone = State()
    phone_confirm = State()
    address = State()
    address_confirm = State()
    pay = State()
    cash = State()
    payments = State()


class Mailing(StatesGroup):
    append = State()
    finish = State()


class Delivery(StatesGroup):
    time = State()
    confirm = State()