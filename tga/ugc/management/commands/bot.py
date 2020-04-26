import logging
import aiohttp
import re
from asyncio import sleep
from aiogram import types, Bot
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext, Dispatcher, filters
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, PreCheckoutQuery
from aiogram.types import InlineQuery, InputTextMessageContent, InlineQueryResultArticle, CallbackQuery, InputMediaPhoto
from aiogram.utils.executor import start_polling
from django.core.management.base import BaseCommand
from django.conf import settings
from ugc.models import Users, Items, Cart
from asgiref.sync import sync_to_async
import ugc.keyboards as kb
from ugc.states import NewBasket, Confirm, Delete, Order, NewItem, Mailing, DelItem, Delivery
import requests
import base64

storage = MemoryStorage()

logging.basicConfig(level=logging.INFO)

PROXY_AUTH = aiohttp.BasicAuth(login=settings.PROXY_LOGIN, password=settings.PROXY_PASS)

bot = Bot(token=settings.BOT_TOKEN,
          proxy=settings.PROXY_URL,
          proxy_auth=PROXY_AUTH,
          parse_mode="HTML")

dp = Dispatcher(bot, storage=storage)
"""
Логика работы с базой данных
"""


@sync_to_async
def add_new_user(message):
    Users.objects.get_or_create(
        user_id=message.chat.id,
        defaults={
            'name': message.from_user.full_name,
            'username': message.from_user.username
        }
    )


@sync_to_async
def get_all_user():
    return Users.objects.all()


def check_admin(message):
    p, _ = Users.objects.get_or_create(
        user_id=message.chat.id,
        defaults={
            'name': message.from_user.full_name,
            'username': message.from_user.username
        }
    )


@sync_to_async
def get_all_items(category):
    return Items.objects.all().filter(category__icontains=category)


@sync_to_async
def get_item(name):
    return Items.objects.get(name=name)


@sync_to_async
def save_cart(name, user_id, quantity, size, price):
    cart = Cart(product=Items.objects.get(name=name), user_id=user_id, quantity=quantity, size=size, price=price)
    cart.save()


@sync_to_async
def get_cart(user_id):
    return Cart.objects.all().filter(user_id__icontains=user_id)


@sync_to_async
def del_cart(product_id):
    return Cart.objects.get(pk=product_id).delete()


"""
Логика работы с админом
"""


@dp.message_handler(filters.IDFilter(user_id=settings.ADMIN_ID), text='Отмена', state='*')
async def cancel(message: types.Message, state: FSMContext):
    await message.answer('Вы отменили текущее действие')
    await state.reset_state()


@dp.message_handler(filters.IDFilter(user_id=settings.ADMIN_ID), text='Удалить товар')
async def del_item(message: types.Message):
    category_kb = InlineKeyboardMarkup()
    category_kb.add(InlineKeyboardButton('Шаверма', callback_data='Шаверма'),
                    InlineKeyboardButton('Закуски', callback_data='Закуски'),
                    InlineKeyboardButton('Соусы', callback_data='Соусы'),
                    InlineKeyboardButton('Напитки', callback_data='Напитки'),
                    InlineKeyboardButton('Добавки', callback_data='Добавки'))
    await message.answer('Выберите категорию в которой нужно удалить товар', reply_markup=category_kb)
    await DelItem.choice.set()


@dp.callback_query_handler(filters.IDFilter(user_id=settings.ADMIN_ID), state=DelItem.choice)
async def choise(call: types.CallbackQuery):
    category = call.data
    kb = InlineKeyboardMarkup(row_width=3)
    items = await Items.query.where(Items.category == category).gino.all()
    if not items:
        await call.message.answer('В этой категории нет товаров', reply_markup=kb)
    else:
        for item in items:
            kb.add(InlineKeyboardButton(text=f'{item.name}', callback_data=f'{item.name}'))
        await call.message.answer('Выберите товар для удаления', reply_markup=kb)
        await DelItem.confirm.set()


@dp.callback_query_handler(filters.IDFilter(user_id=settings.ADMIN_ID), state=DelItem.confirm)
async def confirm(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer('Подтвердите удаление товара', reply_markup=kb.del_kb)
    await state.update_data(item=call.data)
    await DelItem.finish.set()


@dp.callback_query_handler(filters.IDFilter(user_id=settings.ADMIN_ID), text_contains="yes", state=DelItem.finish)
async def del_yes(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        item = data['item']
    await Items.delete.where(Items.name == item).gino.first()
    await call.message.answer('Товар удачно удален')
    await state.reset_state()


@dp.callback_query_handler(filters.IDFilter(user_id=settings.ADMIN_ID), text_contains="no", state=DelItem.finish)
async def del_no(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Удаление товара отменено")
    await state.reset_state()


@dp.message_handler(filters.IDFilter(user_id=settings.ADMIN_ID), text='Добавить товар')
async def add_item(message: types.Message):
    await message.answer('Заполните, как пользователь будет видеть ваш товар. Можно использовать смайлы')
    markup = types.InlineKeyboardMarkup(
        inline_keyboard=
        [
            [types.InlineKeyboardButton(text='Шаверма', callback_data='Шаверма')],
            [types.InlineKeyboardButton(text='Кускуски', callback_data='Кускуски')],
            [types.InlineKeyboardButton(text='Соусы', callback_data='Соусы')],
            [types.InlineKeyboardButton(text='Напитки', callback_data='Напитки')],
            [types.InlineKeyboardButton(text='Добавки', callback_data='Добавки')]
        ]
    )
    await message.answer("Выберите категорию товара", reply_markup=markup)
    await NewItem.category.set()


@dp.callback_query_handler(filters.IDFilter(user_id=settings.ADMIN_ID), state=NewItem.category)
async def choice_category(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    category = call.data
    print(category)
    item = Items()
    item.category = category
    await call.message.answer(f'Вы выбрали категорию: {category}'
                              '\nВведите название товара')
    await NewItem.name.set()
    await state.update_data(item=item)


@dp.message_handler(filters.IDFilter(user_id=settings.ADMIN_ID), state=NewItem.name)
async def enter_name(message: types.Message, state: FSMContext):
    name = message.text
    data = await state.get_data()
    item: Items = data.get('item')
    item.name = name
    await message.answer(f'Название товара: {name}'
                         '\nОтправьте фото товара или ссылку на фотографию url')
    await NewItem.photo.set()
    await state.update_data(item=item)


@dp.message_handler(filters.IDFilter(user_id=settings.ADMIN_ID), content_types=['photo'], state=NewItem.photo)
async def handle_docs_photo(message: types.Message, state: FSMContext):
    file_info = await bot.get_file(message.photo[len(message.photo)-1].file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    img = base64.b64encode(downloaded_file.getvalue())
    url = f'https://api.imgbb.com/1/upload?key={settings.TOKEN_imgbb}'
    data = {
        "image": img}
    r = requests.post(url, data=data).json()
    url = r['data']['url']
    data = await state.get_data()
    item: Items = data.get('item')
    item.photo_url = url
    await message.answer(f'Название товара: {item.name}\n'
                         f'{url}', parse_mode='HTML')
    await message.answer('Введите краткое описание для меню.\n'
                         'В формате: 100гр - 100руб\n'
                         'Для шавермы формат:\n'
                         '200гр - 100руб\n'
                         '400гр - 200руб\n'
                         'или нажмите Отмена')
    await NewItem.description.set()
    await state.update_data(item=item)


@dp.message_handler(filters.IDFilter(user_id=settings.ADMIN_ID), content_types=['text'], state=NewItem.photo)
async def add_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    item: Items = data.get('item')
    try:
        item.photo_url = message.text
    except IndexError:
        await message.answer('введи url')
        return
    await message.answer(f'Название товара: {item.name}\n'
                         f'{message.text}', parse_mode='HTML')
    await message.answer('Введите краткое описание для меню.\n'
                         'В формате: 100гр - 100руб\n'
                         'Для шавермы формат:\n'
                         '200гр - 100руб\n'
                         '400гр - 200руб\n'
                         'или нажмите Отмена')
    await NewItem.description.set()
    await state.update_data(item=item)


@dp.message_handler(filters.IDFilter(user_id=settings.ADMIN_ID), state=NewItem.description)
async def enter_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    item: Items = data.get('item')
    item.description = message.text
    print(item.category)
    if item.category in ['Кускуски', 'Добавки']:
        item.size = message.text.split('-')[0]
        print(item.size)
    await message.answer('Пришлите состав или описание товара. Пример: Сыр, помидоры, лук, специи\n')
    await NewItem.caption.set()
    await state.update_data(item=item)


@dp.message_handler(filters.IDFilter(user_id=settings.ADMIN_ID), state=NewItem.caption)
async def enter_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    item: Items = data.get('item')
    item.caption = message.text
    await NewItem.price.set()
    await state.update_data(item=item)
    await message.answer('Пришлите цену товара.\n'
                         'Для шавермы формат: 150,250')


@dp.message_handler(filters.IDFilter(user_id=settings.ADMIN_ID), state=NewItem.price)
async def enter_price(message: types.Message, state: FSMContext):
    data = await state.get_data()
    item: Items = data.get('item')
    try:
        if item.category == 'Шаверма':
            prices = message.text.split(',')
            item.price = (int(prices[0]))
            item.price1 = (int(prices[1]))
        else:
            item.price = int(message.text)
    except ValueError:
        await message.answer("Неверное значение, введите число")
        return
    markup = types.InlineKeyboardMarkup(
        inline_keyboard=
        [
            [types.InlineKeyboardButton(text='Да', callback_data='confirm')],
            [types.InlineKeyboardButton(text='Ввести заново', callback_data='change')],
        ]
    )
    await message.answer(f'Цена {item.price, item.price1}'
                         '\n Подтверждаете?',
                         reply_markup=markup)
    await state.update_data(item=item)
    await NewItem.confirm.set()


@dp.callback_query_handler(filters.IDFilter(user_id=settings.ADMIN_ID), text_contains="change", state=NewItem.confirm)
async def change_price(call: types.CallbackQuery):
    await call.message.edit_reply_markup()
    await call.message.answer("Введите заново цену товара")
    await NewItem.price.set()


@dp.callback_query_handler(filters.IDFilter(user_id=settings.ADMIN_ID), text_contains="confirm", state=NewItem.confirm)
async def confirm(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    data = await state.get_data()
    item: Items = data.get('item')
    await item.create()
    await call.message.answer('Товар удачно создан')
    await state.reset_state()


@dp.message_handler(filters.IDFilter(user_id=settings.ADMIN_ID), text='Сделать рассылку')
async def mailing(message: types.Message):
    await message.answer("Пришлите текст рассылки")
    await Mailing.append.set()


@dp.message_handler(filters.IDFilter(user_id=settings.ADMIN_ID), state=Mailing.append)
async def enter_text(message: types.Message, state: FSMContext):
    await message.answer(f"Текст рассылки:{message.text}.\n\nОтправить всем пользователям?", reply_markup=kb.confirm_kb)
    await Mailing.finish.set()
    await state.update_data(text=message.text)


@dp.callback_query_handler(filters.IDFilter(user_id=settings.ADMIN_ID), state=Mailing.finish)
async def confirm(call: types.CallbackQuery, state: FSMContext):
    if call.data == 'yes':
        data = await state.get_data()
        text = data.get('text')
        all_users = await User.query.gino.all()
        for user in all_users:
            try:
                await bot.send_message(chat_id=user.user_id, text=text)
                await sleep(0.3)
            except Exception:
                pass
        await call.message.answer('Рассылка выполнена')
        await state.reset_state()
    if call.data == 'no':
        await call.message.answer('Введите новый текст рассылки')
        await Mailing.append.set()


@dp.message_handler(filters.IDFilter(user_id=settings.ADMIN_ID), text='Сообщить о времени доставки')
async def delivery_time(message: types.Message):
    await message.answer('Выберите заказ',)
    await Delivery.time.set()


@dp.message_handler(filters.IDFilter(user_id=settings.ADMIN_ID), state=Delivery.time)
async def mailing(message: types.Message, state: FSMContext):
    data = await state.get_data()
    print(data)
    # chat_id = data.get('chat_id')
    # print(chat_id)
    await message.answer(f'Отправить пользователю это сообщение?\n {message.text}', reply_markup=kb.confirm_kb)
    await Delivery.confirm.set()
    await state.update_data(delivery_text=message.text)


@dp.callback_query_handler(filters.IDFilter(user_id=settings.ADMIN_ID), state=Delivery.confirm)
async def confirm_delivery_time(call: types.CallbackQuery, state: FSMContext):
    if call.data == 'yes':
        data = await state.get_data()
        text = data.get('delivery_text')
        chat_id = data.get('chat_id')
        await bot.send_message(chat_id=chat_id, text=text)
        await call.message.answer('Сообщение отправлено')
        await state.reset_state()

    if call.data == 'no':
        await call.message.answer('Введите другое время')
        await Delivery.time.set()


"""
Логика работы с пользователем
"""
@dp.message_handler(commands=['start'], state='*')
async def send_welcome(message: types.Message):
    await add_new_user(message)
    if message.from_user.id in settings.ADMIN_ID:
        await bot.send_message(
            message.chat.id,
            text='В этом меню вы можете:\n\n'
                 '<b>Добавить товар</b>\n'
                 '<b>Удалить товар</b>\n'
                 '<b>Сделать рассылку</b>\n'
                 '<b>Сделать тестовый заказ</b>\n\n'
                 'Кнопка <b>Отмена</b> служит для отмены создания или удаления товара',
            reply_markup=kb.admin_kb
        )
    else:
        await bot.send_message(
            message.chat.id,
            text='Привет:hand: Добро пожаловать в Just Drink Bar! Нажми на кнопку <b>"Сделать заказ"</b> :point_down:',
            reply_markup=kb.start_kb
        )


@dp.message_handler(text='Сделать заказ', state='*')
async def start_handler(message: types.Message, state: FSMContext):
    await message.answer(
        'Выбирай что ты хочешь, количество и размер выберем позже\n'
        '👆Протяни вверх, чтобы смотреть всё меню👆',
        reply_markup=kb.position_kb
    )


@dp.message_handler(text='Открыть корзину', state='*')
async def open_cart(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    cart = await get_cart(user_id)
    if not cart:
        await message.answer('Корзина пуста. Нажмите кнопку *Сделать заказ*')
    else:
        items_kb = await kb.cart_keyboard(cart, len(cart), 0)
        await bot.send_photo(
            message.chat.id,
            cart[0].product.photo_url,
            caption=f'<b>{cart[0].product.name} {cart[0].size}.'
                    f'{cart[0].quantity}шт {cart[0].price * cart[0].quantity} руб.</b>',
            reply_markup=items_kb
        )
    await state.update_data(cart=cart, i=0)


@dp.inline_handler(state='*')
async def inline_categories(inline_query: InlineQuery):
    text = inline_query.query
    print(text)
    items = await get_all_items(text)
    print(items)
    result = []
    for item in items:
        result.append(InlineQueryResultArticle(
            id=item.id,
            thumb_url=item.photo_url,
            title=item.name + '(' + item.caption + ')',
            description=item.description,
            input_message_content=InputTextMessageContent(item.name)
        ))
    await bot.answer_inline_query(inline_query.id, results=result, cache_time=1)
    if text == 'Добавки':
        await NewBasket.additives.set()
    else:
        await NewBasket.append.set()


@dp.message_handler(state=NewBasket.append)
async def hand_product(message: types.Message, state: FSMContext):
    item = await get_item(message.text)
    if item.category == 'Шаверма':
        item.size = '200гр'
        await message.answer(
            'Хороший выбор. Теперь выбери количество и размер, кнопки находятся ниже.'
            'Как определишься нажми на кнопку <b>"Добавить в корзину"</b>'
        )
        await message.answer_photo(
            photo=item.photo_url,
            caption=f'<b>{item.name} {item.size}. {item.price} руб.</b>\n{item.caption}',
            reply_markup=kb.pizza_keyboard()
        )
        item.text_btn1 = '⚪200гр'
        item.text_btn2 = '400гр'
    else:
        if item.size == None:
            await message.answer(
                'Хороший выбор. Теперь выбери количество, кнопки находятся ниже.'
                'Как определишься нажми на кнопку <b>"Добавить в корзину"</b>'
            )
            await message.answer_photo(
                photo=item.photo_url,
                caption=f'<b>{item.name}. {item.price} руб.</b>\n{item.caption}',
                reply_markup=kb.items_keyboard()
            )
        else:
            await message.answer(
                'Хороший выбор. Теперь выбери количество, кнопки находятся ниже.'
                'Как определишься нажми на кнопку <b>"Добавить в корзину"</b>'
            )
            await message.answer_photo(
                photo=item.photo_url,
                caption=f'<b>{item.name} {item.size}. {item.price} руб.</b>\n{item.caption}',
                reply_markup=kb.items_keyboard()
            )
    item.quantity = 1
    await state.update_data(item=item, price=item.price)


@dp.callback_query_handler(lambda call: call.data in ['200', '400', 'up', 'down', 'add', 'cancel'], state='*')
async def items_handler(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item = data.get('item')
    price = data.get('price')
    print(price)
    print(item.category)
    if item.category == "Шаверма":
        if call.data == '200':
            item.text_btn1 = '⚪200гр'
            item.text_btn2 = '400гр'
            price = item.price
            item.size = '200гр'
            await bot.answer_callback_query(call.id)
            await call.message.edit_caption(
                f'<b>{item.name} {item.size}. {item.price} руб.</b>\n{item.caption}',
                reply_markup=kb.pizza_keyboard(item.text_btn1, item.text_btn2, item.quantity)
            )
            await state.update_data(item=item, price=price)
        if call.data == '400':
            item.size = '400гр'
            price = item.price1
            item.text_btn1 = '200гр'
            item.text_btn2 = '⚪400гр'
            await bot.answer_callback_query(call.id)
            await call.message.edit_caption(
                f'<b>{item.name} {item.size}. {item.price1} руб.</b>\n{item.caption}',
                reply_markup=kb.pizza_keyboard(item.text_btn1, item.text_btn2, item.quantity)
            )
            await state.update_data(item=item, price=price)
        if call.data == 'up':
            await bot.answer_callback_query(call.id)
            await call.message.edit_reply_markup(
                kb.pizza_keyboard(item.text_btn1, item.text_btn2, item.quantity + 1)
            )
            item.quantity = item.quantity + 1
            await state.update_data(item=item)
        if call.data == 'down':
            await bot.answer_callback_query(call.id)
            await call.message.edit_reply_markup(
                kb.pizza_keyboard(item.text_btn1, item.text_btn2, item.quantity - 1)
            )
            item.quantity = item.quantity - 1
            await state.update_data(item=item)
    else:
        if call.data == 'up':
            await bot.answer_callback_query(call.id)
            await call.message.edit_reply_markup(
                kb.items_keyboard(item.quantity + 1)
            )
            item.quantity = item.quantity + 1
            await state.update_data(item=item)
        if call.data == 'down':
            await bot.answer_callback_query(call.id)
            await call.message.edit_reply_markup(
                kb.items_keyboard(item.quantity - 1)
            )
            item.quantity = item.quantity - 1
            await state.update_data(item=item)
    if call.data == 'add':
        user_id = call.message.chat.id
        await save_cart(item.name, user_id, item.quantity, item.size, price)
        await state.reset_state()
        await bot.send_message(
            call.message.chat.id,
            'Вот твоя корзина.\nЕсли все в порядке,жми <b>Оформить заказ</b>'
        )
        cart = await get_cart(user_id)
        items_kb = await kb.cart_keyboard(cart, len(cart), 0)
        item.price = price
        await state.update_data(item=item, cart=cart, i=0)
        await bot.send_photo(
            call.message.chat.id,
            item.photo_url,
            caption=f'<b>{item.name} {item.size}. {item.quantity}шт {price * item.quantity} руб.</b>',
            reply_markup=items_kb
        )
        await bot.answer_callback_query(call.id)
    if call.data == 'cancel':
        await call.message.edit_reply_markup()
        await call.message.delete()
        await state.reset_state()
        await bot.edit_message_text(
            'Выбирай что ты хочешь, количество и размер выберем позже',
            call.message.chat.id, call.message.message_id - 1,
            reply_markup=kb.position_kb
        )


@dp.callback_query_handler(lambda call: call.data in ['left', 'right'], state='*')
async def items_handler(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get('cart')
    print(cart)
    if call.data == 'right':
        await bot.answer_callback_query(call.id)
        i = data.get('i')
        if i != len(cart) - 1:
            i = i + 1
            items_kb = await kb.cart_keyboard(cart, len(cart), i)
            await call.message.edit_media(
                media=InputMediaPhoto(
                    media=cart[i].product.photo_url,
                    caption=f'<b>{cart[i].product.name} {cart[i].size}.{cart[i].quantity}шт'
                            f' {cart[i].price * cart[i].quantity}</b>'),
                reply_markup=items_kb
            )
            await state.update_data(i=i)
    if call.data == 'left':
        await bot.answer_callback_query(call.id)
        i = data.get('i')
        if i != 0:
            i = i-1
            items_kb = await kb.cart_keyboard(cart, len(cart), i)
            await call.message.edit_media(
                media=InputMediaPhoto(
                    media=cart[i].product.photo_url,
                    caption=f'<b>{cart[i].product.name} {cart[i].size}.{cart[i].quantity}шт'
                            f' {cart[i].price * cart[i].quantity}</b>'),
                reply_markup=items_kb
            )
            await state.update_data(i=i)


@dp.message_handler(state=NewBasket.additives)
async def additives(message: types.Message, state: FSMContext):
    await message.answer(f'Добавить {message.text}?', reply_markup=kb.confirm_kb)
    await NewBasket.confirm_additives.set()
    await state.update_data(additives=message.text)

#TODO
@dp.callback_query_handler(state=NewBasket.confirm_additives)
async def confirm_additives(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item = data.get('item')
    if call.data == 'yes':
        additives = data.get('additives')
        price = data.get('price')
        item_db = await get_item(additives)
        item.name = f'{item.name} + {additives}'
        price = price + item_db.price
        item.size = f'{item.size} + {item_db.size}'
        await state.update_data(item=item, price=price)
        await call.message.answer_photo(
            photo=item.photo_url,
            caption=f'<b>{item.name} {item.size}.\n{price} руб.</b>\n{item.caption}',
            reply_markup=kb.additives_keyboard(item.quantity)
        )
        await NewBasket.add_additives.set()
    if call.data == 'no':
        await call.message.answer_photo(
            photo=item.photo_url,
            caption=f'<b>{item.name} {item.size}.\n{item.price} руб.</b>\n{item.caption}',
            reply_markup=kb.pizza_keyboard()
        )
        await NewBasket.add_additives.set()


@dp.callback_query_handler(lambda call: call.data in ['menu'], state='*')
async def menu_handler(call: CallbackQuery):
    await call.message.answer(
        'Выбирай что ты хочешь, количество и размер выберем позже\n'
        '👆Протяни вверх, чтобы смотреть всё меню👆',
        reply_markup=kb.position_kb
    )


@dp.callback_query_handler(lambda call: call.data in ['del', 'pay'], state='*')
async def pay_del_handler(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if call.data == 'del':
        await bot.answer_callback_query(call.id)
        await call.message.edit_reply_markup(reply_markup=kb.del_kb)
        await Delete.confirm.set()
    if call.data == 'pay':
        text = 'Ваш заказ:\n\n'
        cart = data.get('cart')
        prices = 0
        for purchase in cart:
            text += f'{purchase.product.name} {purchase.quantity} шт. - {purchase.price * purchase.quantity} руб.\n'
            prices += purchase.price * purchase.quantity
        text += f'\nИтоговая стоимость заказа: {prices} руб'
        kb_confirm = InlineKeyboardMarkup()
        kb_confirm.row(
            InlineKeyboardButton(text='Подтвердить заказ', callback_data='confirm'),
            InlineKeyboardButton(text='Назад в корзину', callback_data='back')
        )
        await bot.send_message(
            call.message.chat.id,
            text, reply_markup=kb_confirm
        )
        await state.update_data(cart=cart)
        await Confirm.start.set()


@dp.callback_query_handler(lambda call: call.data in ['yes', 'no'], state=Delete.confirm)
async def confirm_delete(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    i = data.get('i')
    cart = data.get('cart')
    if call.data == 'yes':
        await bot.answer_callback_query(call.id)
        await del_cart(cart[i].id)
        cart = await get_cart(call.message.chat.id)
        items_kb = await kb.cart_keyboard(cart, len(cart), 0)
        if not cart:
            await call.message.answer(
                'Выбирай что ты хочешь, количество и размер выберем позже',
                reply_markup=kb.position_kb
            )
        else:
            await bot.send_photo(
                call.message.chat.id,
                cart[0].product.photo_url,
                caption=f'<b>{cart[0].product.name} {cart[0].size}. '
                        f'{cart[0].quantity}шт {cart[0].price * cart[0].quantity} руб.</b>',
                reply_markup=items_kb
            )
            await state.update_data(cart=cart, items_kb=items_kb, i=0)
    if call.data == 'no':
        items_kb = await kb.cart_keyboard(cart, len(cart), i)
        await bot.answer_callback_query(call.id)
        await call.message.edit_reply_markup(reply_markup=items_kb)


@dp.callback_query_handler(lambda call: call.data in ['confirm', 'back'], state=Confirm.start)
async def confirm_handler(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if call.data == 'back':
        await bot.answer_callback_query(call.id)
        cart = data.get('cart')
        items_kb = await kb.cart_keyboard(cart, len(cart), 0)
        await bot.send_photo(
            call.message.chat.id,
            cart[0].product.photo_url,
            caption=f'<b>{cart[0].product.name} {cart[0].size}. '
                    f'{cart[0].quantity}шт {cart[0].price * cart[0].quantity} руб.</b>',
            reply_markup=items_kb
        )
        await bot.answer_callback_query(call.id)
    await state.update_data(i=0)
    if call.data == 'confirm':
        await bot.answer_callback_query(call.id)
        await call.message.answer(
            'Отлично! Выбери способ получения товара',
            reply_markup=kb.method
        )
        await Confirm.method.set()


@dp.callback_query_handler(lambda call: call.data in ['Доставка', 'Самовывоз'], state=Confirm.method)
async def confirm_handler(call: CallbackQuery, state: FSMContext):
    if call.data == 'Доставка':
        await bot.answer_callback_query(call.id)
        await call.message.answer('Отлично! Теперь введите номер телефона в формате 89130000000')
        await Confirm.phone.set()
    if call.data == 'Самовывоз':
        await bot.answer_callback_query(call.id)
        await call.message.answer('Отлично! Когда начинать готовить?', reply_markup=kb.time)
        await Confirm.time.set()
    await state.update_data(method=call.data)


@dp.message_handler(state=Confirm.phone)
async def hand_phone(message: types.Message, state: FSMContext):
    phone = message.text
    if re.search(r'^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$', phone):
        await message.answer(
            f'Твой номер телефона {message.text} ,верно?',
            reply_markup=kb.confirm_kb
        )
        await Confirm.phone_confirm.set()
        await state.update_data(phone=message.text)
    else:
        await message.answer('Неправильный формат.Введите реальный номер,чтобы мы могли с вязаться с вами')


@dp.callback_query_handler(state=Confirm.phone_confirm)
async def confirm_phone(call: CallbackQuery):
    if call.data == 'yes':
        await bot.answer_callback_query(call.id)
        await call.message.answer('Теперь введите куда вести заказ')
        await Confirm.address.set()
    if call.data == 'no':
        await bot.answer_callback_query(call.id)
        await call.message.answer('Введите заново')
        await Confirm.phone.set()


@dp.message_handler(state=Confirm.address)
async def hand_address(message: types.Message, state: FSMContext):
    await message.answer(
        f'Твой адрес {message.text} ,верно?',
        reply_markup=kb.confirm_kb
    )
    await Confirm.address_confirm.set()
    await state.update_data(address=message.text)


@dp.callback_query_handler(state=Confirm.address_confirm)
async def confirm_phone(call: CallbackQuery):
    if call.data == 'yes':
        await call.message.answer('Отлично! Когда начинать готовить?', reply_markup=kb.pay_kb)
        await Confirm.time.set()
    if call.data == 'no':
        await call.message.answer('Введите заново')
        await Confirm.address.set()


@dp.callback_query_handler(lambda call: call.data in ['Ко времени', 'Прямо сейчас'], state=Confirm.time)
async def confirm_handler(call: CallbackQuery, state: FSMContext):
    if call.data == 'Ко времени':
        await call.message.answer('Напишите к какому времени нужен заказ')
        await Confirm.confirm_time.set()
    if call.data == 'Прямо сейчас':
        await call.message.answer('Отлично! Теперь выберите способ оплаты', reply_markup=kb.pay_kb)
        await Confirm.pay.set()
    await state.update_data(time=call.data)


@dp.message_handler(state=Confirm.confirm_time)
async def hand_address(message: types.Message, state: FSMContext):
    await state.update_data(time_zone=message.text)
    await message.answer('Отлично! Теперь выберите способ оплаты', reply_markup=kb.pay_kb)
    await Confirm.pay.set()


@dp.callback_query_handler(state=Confirm.pay)
async def pay(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if call.data == 'Наличные':
        await call.message.answer('С какой суммы подготовить сдачу?')
        await Confirm.cash.set()
    if call.data == 'Терминал':
        await call.message.answer(
            'Заказ принят! Приедем к вам с терминалом.\n'
            'Скоро с вами свяжемся и сообщим время доставки'
        )
        await information_admin(state=state, chat_id=call.message.chat.id, payment_method=call.data)
        await state.update_data(chat_id=call.message.chat.id)
    if call.data == 'Онлайн':
        cart = data.get('cart')
        text = 'Ваш заказ:\n\n'
        prices = 0
        for purchase in cart:
            text += f'{purchase.product.name} {purchase.quantity} шт. - {purchase.price * purchase.quantity} руб.\n'
            prices += purchase.price * purchase.quantity
        text += f'\nИтоговая стоимость заказа: {prices} руб'
        PRICE = types.LabeledPrice(label='Покупка', amount=prices * 100)
        await bot.send_invoice(
            call.message.chat.id,
            title='Ваша корзина',
            description=text,
            provider_token=settings.PAYMENTS_PROVIDER_TOKEN,
            currency='rub',
            is_flexible=False,  # True если конечная цена зависит от способа доставки
            prices=[PRICE],
            start_parameter='time-machine-example',
            payload='some-invoice-payload-for-our-internal-use')
        await Confirm.payments.set()


@dp.message_handler(state=Confirm.cash)
async def hand_cash(message: types.Message, state: FSMContext):
    await information_admin(state=state, chat_id=message.chat.id, payment_method='Наличные', balance=message.text)
    await message.answer(
        'Заказ принят!\nСкоро с вами свяжемся и сообщим время доставки'
    )
    await state.update_data(chat_id=message.chat.id)


@dp.pre_checkout_query_handler(state=Confirm.payments)
async def checkout(query: PreCheckoutQuery, state: FSMContext):
    print(query)
    await bot.answer_pre_checkout_query(query.id, True)
    data = await state.get_data()
    cart = data.get("cart")
    success = await check_payment(cart)
    if success:
        await information_admin(state=state, chat_id=query.from_user.id, payment_method='Онлайн')
        await state.update_data(chat_id=query.from_user.id)
        await bot.send_message(
            query.from_user.id,
            "Заказ принят! Спасибо за покупку.\nСкоро с вами свяжемся и сообщим время доставки"
        )
    else:
        await bot.send_message(
            query.from_user.id,
            "Покупка не была подтверждена, попробуйте позже..."
        )


async def check_payment(cart):
    return True


async def information_admin(state: FSMContext, chat_id, payment_method, balance=''):
    text = 'Поступил заказ:\n\n'
    async with state.proxy() as data:
        cart = data['cart']
    prices = 0
    for purchase in cart:
        text += f'{purchase.product.name} {purchase.quantity}шт - {purchase.price * purchase.quantity}\n'
        prices += purchase.price * purchase.quantity
    if data.get('method') == 'Доставка':
        text += f'Итоговая стоимость заказа: {prices} руб\nНомер телефона клиента: {data.get("phone")}\n' \
                f'Адрес доставки: {data.get("address")}\n' \
                f'Способ оплаты:{payment_method} {balance}\n' \
                f'Способ получения товара: {data.get("method")}\n' \
                f'{data.get("time")} {data.get("time_zone")}'
    else:
        text += f'Итоговая стоимость заказа: {prices} руб\n' \
                f'Способ получения товара: {data.get("method")} ' \
                f'{data.get("time")} {data.get("time_zone")}\n' \
                f'Способ оплаты:{payment_method} {balance}'
    for i in settings.ADMIN_ID:
        await bot.send_message(i, text)
        await sleep(0.3)
    await state.update_data(chat_id=chat_id)


class Command(BaseCommand):
    """
    Класс для запуска бота в management commands Django
    """
    help = 'Телеграм-бот'

    def handle(self, *args, **options):
        start_polling(dp, skip_updates=True)


