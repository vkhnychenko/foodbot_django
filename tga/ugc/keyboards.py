from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


start_kb = ReplyKeyboardMarkup(
    row_width=1, resize_keyboard=True).add(
    KeyboardButton('Сделать заказ'), KeyboardButton('Открыть корзину')
)
admin_kb = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True).add(
    KeyboardButton('Добавить товар'),
    KeyboardButton('Удалить товар'),
    KeyboardButton('Сообщить о времени доставки'),
    KeyboardButton('Отмена'),
    KeyboardButton('Сделать рассылку'),
    KeyboardButton('Сделать заказ'),
    KeyboardButton('Открыть корзину')
)

pizza_btn = InlineKeyboardButton('Шаверма', switch_inline_query_current_chat='Шаверма')
burger_btn = InlineKeyboardButton('Закуски', switch_inline_query_current_chat='Закуски')
snack_btn = InlineKeyboardButton('Соусы', switch_inline_query_current_chat='Соусы')
drink_btn = InlineKeyboardButton('Напитки', switch_inline_query_current_chat='Напитки')
position_kb = InlineKeyboardMarkup(row_width=3)
position_kb.row(pizza_btn, burger_btn)
position_kb.row(snack_btn, drink_btn)


basket_kb = InlineKeyboardMarkup(row_width=1)
basket_kb.row(pizza_btn, burger_btn)
basket_kb.row(snack_btn, drink_btn)
delete = InlineKeyboardButton('✖️', callback_data='del')
left = InlineKeyboardButton('⬅️', callback_data='left')
right = InlineKeyboardButton('➡️', callback_data='right')
menu = InlineKeyboardButton('menu', callback_data='menu')

del_kb = InlineKeyboardMarkup(row_width=1)
del_kb.add(InlineKeyboardButton('Да, точно удалить!', callback_data='yes'))
del_kb.add(InlineKeyboardButton('Отмена', callback_data='no'))

method = InlineKeyboardMarkup(row_width=1)
method.row(
    InlineKeyboardButton('Доставка', callback_data='Доставка'),
    InlineKeyboardButton('Самовывоз', callback_data='Самовывоз'),
)

time = InlineKeyboardMarkup(row_width=1)
time.row(
    InlineKeyboardButton('Прямо сейчас', callback_data='Прямо сейчас'),
    InlineKeyboardButton('Ко времени', callback_data='Ко времени'),
)

pay_kb = InlineKeyboardMarkup(row_width=1)
pay_kb.add(InlineKeyboardButton('Картой прямо сейчас', callback_data='Онлайн'),
           InlineKeyboardButton('Наличные', callback_data='Наличные'),
           InlineKeyboardButton('Картой курьеру', callback_data='Терминал'))

confirm_kb = InlineKeyboardMarkup()
confirm_kb.row(InlineKeyboardButton(text='Да', callback_data='yes'),
               InlineKeyboardButton(text='Нет', callback_data='no'))

delivery_time_kb = InlineKeyboardMarkup()
delivery_time_kb.add(InlineKeyboardButton(text='Сообщить время доставки', callback_data='delivery_time'))


def confirm(price):
    btn = InlineKeyboardButton(f'Оформить заказ({price})', callback_data='pay')
    return btn


basket_kb.add(delete)
basket_kb.add(confirm)


def pizza_keyboard(text_btn1 = '⚪200гр', text_btn2='400гр', quantity=1):
    pizza_kb = InlineKeyboardMarkup(row_width=1)
    quantity_btn = InlineKeyboardButton(f'{quantity} шт.', callback_data='None')
    pizza_kb.row(InlineKeyboardButton(text_btn1, callback_data='200'), InlineKeyboardButton(text_btn2, callback_data='400'))
    pizza_kb.add(InlineKeyboardButton('Дополним? ', switch_inline_query_current_chat='Добавки'))
    pizza_kb.row(InlineKeyboardButton('⬇️', callback_data='down'), quantity_btn,
                 InlineKeyboardButton('⬆️', callback_data='up'), InlineKeyboardButton('Отмена', callback_data='cancel'))
    pizza_kb.add(InlineKeyboardButton('Добавить в корзину', callback_data='add'))
    return pizza_kb


def items_keyboard(quantity = 1):
    items_kb = InlineKeyboardMarkup(row_width=1)
    quantity_btn = InlineKeyboardButton(f'{quantity} шт.', callback_data='None')
    items_kb.row(InlineKeyboardButton('⬇️', callback_data='down'), quantity_btn,
                 InlineKeyboardButton('⬆️', callback_data='up'), InlineKeyboardButton('Отмена', callback_data='cancel'))
    items_kb.add(InlineKeyboardButton('Добавить в корзину', callback_data='add'))
    return items_kb


def additives_keyboard(quantity = 1):
    items_kb = InlineKeyboardMarkup(row_width=1)
    quantity_btn = InlineKeyboardButton(f'{quantity} шт.', callback_data='None')
    items_kb.row(quantity_btn, InlineKeyboardButton('Отмена', callback_data='cancel'))
    items_kb.add(InlineKeyboardButton('Дополним? ', switch_inline_query_current_chat='Добавки'))
    items_kb.add(InlineKeyboardButton('Добавить в корзину', callback_data='add'))
    return items_kb


async def cart_keyboard(cart, lenght,  i):
    prices = 0
    for item_cart in cart:
        prices += item_cart.price
    if lenght == 1:
        items_kb = InlineKeyboardMarkup(row_width=3)
        items_kb.add(delete)
        items_kb.add(menu)
        items_kb.add(confirm(prices))
        return items_kb
    else:
        items_kb = InlineKeyboardMarkup(row_width=3)
        items_kb.row(left, InlineKeyboardButton(text=f'{i+1} / {lenght}', callback_data='None'), right)
        items_kb.add(delete)
        items_kb.add(menu)
        items_kb.add(confirm(prices))
        return items_kb

