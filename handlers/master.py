from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.keyboards import master_main_kb, order_status_kb, master_orders_kb
from services.order_service import OrderService
from services.master_service import MasterService
from models import OrderStatus, Master
from core.utils import get_status_emoji, format_money
from filters.role import RoleFilter
from config import ADMIN_IDS
from datetime import date

router = Router()

# ==================== FSM States ====================
class MasterStates(StatesGroup):
    waiting_work_amount = State()
    waiting_expenses = State()
    waiting_work_photos = State()
    waiting_work_description = State()
    waiting_admin_message = State()
    waiting_reject_reason = State()

# ==================== Adminlarga xabar yuborish ====================
async def notify_admins(bot: Bot, message: str, photos: list = None):
    """Barcha adminlarga xabar yuborish, shu bilan birga fotolar"""
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, message)
            if photos:
                media_group = [InputMediaPhoto(media=photo_id) for photo_id in photos]
                await bot.send_media_group(admin_id, media_group)
        except Exception:
            continue

# ==================== Главное меню ====================
@router.message(F.text == "/start", RoleFilter("master"))
async def master_start(msg: Message, state: FSMContext, master: Master):
    await state.clear()
    await msg.answer(
        f"🔧 Привет, {master.name}!\n"
        f"Выберите действие:",
        reply_markup=master_main_kb()
    )

# ==================== Мои заявки ====================
@router.message(F.text == "📋 Мои заявки")
async def my_orders(msg: Message, state: FSMContext, master: Master, master_service: MasterService):
    """Список заявок мастера"""
    await state.clear()
    orders = await master_service.get_master_orders(master.id)
   
    if not orders:
        await msg.answer(
            "📋 У вас пока нет заявок.\n"
            "Ожидайте назначения от администратора.",
            reply_markup=master_main_kb()
        )
        return
   
    active = [o for o in orders if o.status in [
        OrderStatus.new,
        OrderStatus.confirmed,
        OrderStatus.in_progress,
        OrderStatus.arrived
    ]]
   
    completed = [o for o in orders if o.status == OrderStatus.completed]
   
    text = "📋 Ваши заявки:\n\n"
   
    if active:
        text += "🔄 Активные:\n"
        for order in active[:5]:
            emoji = get_status_emoji(order.status.value)
            text += (
                f"{emoji} #{order.number}\n"
                f" Клиент: {order.client_name}\n"
                f" Адрес: {order.address}\n"
                f" Время: {order.datetime.strftime('%d.%m %H:%M')}\n\n"
            )
   
    if completed:
        text += f"\n✅ Завершено: {len(completed)}"
   
    await msg.answer(text, reply_markup=master_orders_kb(bool(active)))

# ==================== График ====================
@router.message(F.text == "📅 График")
async def show_schedule(msg: Message, state: FSMContext, master: Master, master_service: MasterService):
    """Показать график работы"""
    await state.clear()
    
    today_orders = await master_service.get_today_orders(master.id)
    
    if not master.schedule or not any(master.schedule.values()):
        text = "📅 Ваш график пуст.\n"
        if not today_orders:
            text += "У вас нет назначенных заказов на сегодня."
        else:
            text += "Но у вас есть заказы на сегодня, проверьте 'Мои заявки'."
        await msg.answer(text, reply_markup=master_main_kb())
        return
    
    text = "📅 Ваш график:\n\n"
    sorted_dates = sorted(master.schedule.keys())
    
    for date_str in sorted_dates[:7]:
        times = master.schedule[date_str]
        if times:
            text += f"📆 {date_str}:\n"
            for time, status in sorted(times.items()):
                status_emoji = "🔴" 
                text += f" • {time} {status_emoji} ({status})\n"
            text += "\n"
    
    await msg.answer(text, reply_markup=master_main_kb())

# ==================== Текущие работы ====================
@router.callback_query(F.data == "master_current_orders")
async def show_current_orders(callback: CallbackQuery, master: Master, master_service: MasterService, bot: Bot):
    """Показать текущие активные заказы мастера"""
    orders = await master_service.get_current_orders(master.id)
    
    if not orders:
        await callback.message.edit_text(
            "🛠 У вас нет текущих активных работ.",
            reply_markup=master_orders_kb()
        )
        await callback.answer()
        return
    
    text = "🛠 Текущие работы:\n\n"
    for order in orders:
        emoji = get_status_emoji(order.status.value)
        text += (
            f"{emoji} #{order.number}\n"
            f" Клиент: {order.client_name}\n"
            f" Адрес: {order.address}\n"
            f" Время: {order.datetime.strftime('%d.%m %H:%M')}\n"
            f" Статус: {order.status.value}\n\n"
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Изменить #{o.number}", callback_data=f"edit_order_{o.id}")]
            for o in orders
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_orders")]])
    )
    await callback.answer()

# ==================== Работы на сегодня ====================
@router.callback_query(F.data == "master_today_orders")
async def show_today_orders(callback: CallbackQuery, master: Master, master_service: MasterService, bot: Bot):
    """Показать заказы мастера на сегодня"""
    orders = await master_service.get_today_orders(master.id)
    
    if not orders:
        await callback.message.edit_text(
            "📅 На сегодня нет активных заказов.",
            reply_markup=master_orders_kb()
        )
        await callback.answer()
        return
    
    text = "📅 Работы на сегодня:\n\n"
    for order in orders:
        emoji = get_status_emoji(order.status.value)
        text += (
            f"{emoji} #{order.number}\n"
            f" Клиент: {order.client_name}\n"
            f" Адрес: {order.address}\n"
            f" Время: {order.datetime.strftime('%d.%m %H:%M')}\n"
            f" Статус: {order.status.value}\n\n"
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Изменить #{o.number}", callback_data=f"edit_order_{o.id}")]
            for o in orders
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_orders")]])
    )
    await callback.answer()

# ==================== Все работы ====================
@router.callback_query(F.data == "master_all_orders")
async def show_all_orders(callback: CallbackQuery, master: Master, master_service: MasterService, bot: Bot):
    """Показать все заказы мастера"""
    orders = await master_service.get_master_orders(master.id)
    
    if not orders:
        await callback.message.edit_text(
            "📋 У вас нет заказов.",
            reply_markup=master_orders_kb()
        )
        await callback.answer()
        return
    
    text = "📋 Все работы:\n\n"
    for order in orders:
        emoji = get_status_emoji(order.status.value)
        text += (
            f"{emoji} #{order.number}\n"
            f" Клиент: {order.client_name}\n"
            f" Адрес: {order.address}\n"
            f" Время: {order.datetime.strftime('%d.%m %H:%M')}\n"
            f" Статус: {order.status.value}\n\n"
        )
    
    active_orders = [o for o in orders if o.status in [OrderStatus.new, OrderStatus.confirmed, OrderStatus.in_progress, OrderStatus.arrived]]
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Изменить #{o.number}", callback_data=f"edit_order_{o.id}")]
            for o in active_orders
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_orders")]])
    )
    await callback.answer()

# ==================== Архив ====================
@router.callback_query(F.data == "master_orders_archive")
async def show_archive_orders(callback: CallbackQuery, master: Master, master_service: MasterService):
    """Показать завершенные заказы"""
    orders = await master_service.get_master_orders(master.id)
    completed = [o for o in orders if o.status == OrderStatus.completed]
    
    if not completed:
        await callback.message.edit_text(
            "✅ Архив пуст",
            reply_markup=master_orders_kb()
        )
        await callback.answer()
        return
    
    text = "✅ Завершенные заявки:\n\n"
    total_profit = 0
    
    for order in completed[:10]:
        text += (
            f"#{order.number} - {order.client_name}\n"
            f" Прибыль: {format_money(order.profit)}\n"
        )
        total_profit += order.profit
    
    text += f"\n💎 Общая прибыль: {format_money(total_profit)}"
    
    await callback.message.edit_text(text, reply_markup=master_orders_kb())
    await callback.answer()

# ==================== Изменение статуса заказа ====================
@router.callback_query(F.data.startswith("edit_order_"))
async def edit_order(callback: CallbackQuery, master: Master, order_service: OrderService, master_service: MasterService, bot: Bot):
    """Изменение статуса заказа"""
    order_id = int(callback.data.split("_")[2])
    order = await order_service.order_repo.get(order_id)
    
    if not order:
        await callback.message.edit_text(
            "❌ Заявка не найдена!",
            reply_markup=master_orders_kb()
        )
        await callback.answer()
        return
    
    if order.status == OrderStatus.completed:
        await callback.message.edit_text(
            f"✅ Заявка #{order.number} завершена и не может быть изменена.\n\n"
            f"👥 Клиент: {order.client_name}\n"
            f"📞 Телефон: {order.phone}\n"
            f"📍 Адрес: {order.address}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m %H:%M')}\n"
            f"💬 Проблема: {order.comment}",
            reply_markup=master_orders_kb()
        )
        await callback.answer()
        return
    
    text = (
        f"📋 Заявка #{order.number}\n"
        f"👥 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m %H:%M')}\n"
        f"💬 Проблема: {order.comment}\n"
        f"🔄 Статус: {order.status.value}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=order_status_kb(order.id, order.status)
    )
    await callback.answer()

# ==================== Управление статусом ====================
@router.callback_query(F.data.startswith("confirm_"))
async def confirm_order(
    callback: CallbackQuery,
    master: Master,
    order_service: OrderService,
    master_service: MasterService,
    bot: Bot
):
    """Подтверждение заявки мастером"""
    order_id = int(callback.data.split("_")[1])
    order = await order_service.update_status(order_id, OrderStatus.confirmed)
    
    await master_service.update_schedule(master.id, order.datetime, "надо сделать")
    await order_service.session.commit()
    
    await notify_admins(
        bot,
        f"✅ Мастер принял заказ!\n\n"
        f"👤 Мастер: {master.name}\n"
        f"📋 Заказ: #{order.number}\n"
        f"👥 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}"
    )
    
    await callback.message.edit_text(
        f"✅ Вы подтвердили заявку #{order.number}!\n\n"
        f"👥 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"💬 Проблема: {order.comment}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n",
        reply_markup=order_status_kb(order.id, order.status)
    )
    await callback.answer("✅ Заявка подтверждена")

@router.callback_query(F.data.startswith("depart_"))
async def depart_order(
    callback: CallbackQuery,
    master: Master,
    order_service: OrderService,
    bot: Bot
):
    """Выезд к клиенту"""
    order_id = int(callback.data.split("_")[1])
    order = await order_service.update_status(order_id, OrderStatus.in_progress)
   
    await notify_admins(
        bot,
        f"🚗 Мастер выехал на заказ!\n\n"
        f"👤 Мастер: {master.name}\n"
        f"📋 Заказ: #{order.number}\n"
        f"👥 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}"
    )
    await callback.message.edit_text(
        f"🚗 Вы выехали на заявку #{order.number}!\n\n"
        f"👥 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"💬 Проблема: {order.comment}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n",
        reply_markup=order_status_kb(order.id, order.status)
    )
    await callback.answer("🚗 В пути")

@router.callback_query(F.data.startswith("arrive_"))
async def arrive_order(
    callback: CallbackQuery,
    master: Master,
    order_service: OrderService,
    bot: Bot
):
    """Прибытие на место"""
    order_id = int(callback.data.split("_")[1])
    order = await order_service.update_status(order_id, OrderStatus.arrived)
   
    await notify_admins(
        bot,
        f"🏠 Мастер прибыл на место!\n\n"
        f"👤 Мастер: {master.name}\n"
        f"📋 Заказ: #{order.number}\n"
        f"👥 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}"
    )
   
    await callback.message.edit_text(
        f"🏠 Вы прибыли на заявку #{order.number}!\n\n"
        f"👥 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"💬 Проблема: {order.comment}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"Начинайте работу.\n"
        f"После завершения нажмите 'Завершить'.",
        reply_markup=order_status_kb(order.id, order.status)
    )
    await callback.answer("🏠 Прибыли")

@router.callback_query(F.data.startswith("complete_"))
async def complete_order_start(
    callback: CallbackQuery,
    state: FSMContext,
    master_service: MasterService
):
    """Начало завершения заявки"""
    order_id = int(callback.data.split("_")[1])
    await state.update_data(order_id=order_id)
    await state.set_state(MasterStates.waiting_work_amount)
   
    await callback.message.edit_text(
        "💰 Введите сумму работы (в ₽):\n"
        "Например: 1500"
    )
    await callback.answer()

@router.message(MasterStates.waiting_work_amount)
async def process_work_amount(msg: Message, state: FSMContext):
    """Обработка суммы работы"""
    try:
        work_amount = float(msg.text.strip())
        if work_amount < 0:
            await msg.answer("❌ Сумма не может быть отрицательной. Попробуйте снова:")
            return
       
        await state.update_data(work_amount=work_amount)
        await state.set_state(MasterStates.waiting_expenses)
        await msg.answer(
            "💵 Введите расходы (запчасти и т.д.):\n"
            "Или отправьте '0' если расходов не было"
        )
    except ValueError:
        await msg.answer("❌ Неверный формат. Введите число, например: 150000")

@router.message(MasterStates.waiting_expenses)
async def process_expenses(msg: Message, state: FSMContext):
    """Обработка расходов"""
    try:
        expenses = float(msg.text.strip())
        if expenses < 0:
            await msg.answer("❌ Расходы не могут быть отрицательными. Попробуйте снова:")
            return
       
        await state.update_data(expenses=expenses, work_photos=[])
        await state.set_state(MasterStates.waiting_work_photos)
        await msg.answer(
            "📸 Отправьте фото выполненных работ:\n"
            "Можете отправить несколько фото.\n\n"
            "Когда закончите, нажмите кнопку 'Готово' или отправьте /done",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="✅ Готово")]],
                resize_keyboard=True
            )
        )
    except ValueError:
        await msg.answer("❌ Неверный формат. Введите число, например: 50000")

@router.message(MasterStates.waiting_work_photos, F.photo)
async def receive_work_photo(msg: Message, state: FSMContext):
    """Получение фото работ"""
    data = await state.get_data()
    photos = data.get("work_photos", [])
   
    photos.append(msg.photo[-1].file_id)
    await state.update_data(work_photos=photos)
   
    await msg.answer(
        f"✅ Фото получено! Всего: {len(photos)}\n"
        f"Отправьте еще фото или нажмите 'Готово'"
    )

@router.message(MasterStates.waiting_work_photos, F.text.in_(["✅ Готово", "/done"]))
async def photos_done(msg: Message, state: FSMContext):
    """Завершение приема фото"""
    data = await state.get_data()
    photos = data.get("work_photos", [])
   
    if not photos:
        await msg.answer(
            "⚠️ Вы не отправили ни одного фото.\n"
            "Отправьте хотя бы одно фото или нажмите 'Пропустить'",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="⏭️ Пропустить")],
                    [KeyboardButton(text="✅ Готово")]
                ],
                resize_keyboard=True
            )
        )
        return
   
    await state.set_state(MasterStates.waiting_work_description)
    await msg.answer(
        "📝 Опишите выполненные работы:\n"
        "Например: Замена компрессора, заправка фреоном, проверка системы",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(MasterStates.waiting_work_photos, F.text == "⏭️ Пропустить")
async def skip_photos(msg: Message, state: FSMContext):
    """Пропустить фото"""
    await state.update_data(work_photos=[])
    await state.set_state(MasterStates.waiting_work_description)
    await msg.answer(
        "📝 Опишите выполненные работы:\n"
        "Например: Замена компрессора, заправка фреоном, проверка системы",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(MasterStates.waiting_work_photos)
async def invalid_photo_input(msg: Message):
    """Неверный ввод при ожидании фото"""
    await msg.answer(
        "❌ Пожалуйста, отправьте фото или нажмите 'Готово'\n"
        "Если не хотите отправлять фото, нажмите 'Пропустить'"
    )

@router.message(MasterStates.waiting_work_description)
async def complete_order_finish(
    msg: Message,
    state: FSMContext,
    master: Master,
    order_service: OrderService,
    master_service: MasterService,
    bot: Bot
):
    """Завершение заявки с расчетом"""
    work_description = msg.text.strip()
   
    if len(work_description) < 5:
        await msg.answer("❌ Описание слишком короткое. Опишите подробнее выполненные работы:")
        return
   
    data = await state.get_data()
    work_photos = data.get("work_photos", [])
   
    order = await order_service.update_status(
        order_id=data["order_id"],
        status=OrderStatus.completed,
        work_amount=data["work_amount"],
        expenses=data["expenses"],
        work_description=work_description,
        work_photos=work_photos
    )
   
    # Графикни yangilash
    try:
        await master_service.update_schedule(master.id, order.datetime, "завершено")
    except Exception as e:
        await bot.send_message(
            ADMIN_IDS[0],
            f"⚠️ Графикни yangilashda xatolik yuz berdi (Master ID: {master.id}): {str(e)}"
        )
    
    await order_service.session.commit()
   
    admin_message = (
        f"✅ Заказ завершён!\n\n"
        f"👤 Мастер: {master.name}\n"
        f"📋 Заказ: #{order.number}\n"
        f"👥 Клиент: {order.client_name}\n\n"
        f"📝 Выполненные работы:\n{work_description}\n\n"
        f"💰 Сумма работы: {format_money(order.work_amount)}\n"
        f"💵 Расходы: {format_money(order.expenses)}\n"
        f"💎 Прибыль: {format_money(order.profit)}"
    )
   
    await notify_admins(
        bot,
        admin_message,
        work_photos
    )
   
    await msg.answer(
        f"✅ Заявка #{order.number} завершена!\n\n"
        f"📝 Работы: {work_description}\n\n"
        f"💰 Сумма работы: {format_money(order.work_amount)}\n"
        f"💵 Расходы: {format_money(order.expenses)}\n"
        f"💎 Прибыль: {format_money(order.profit)}\n\n"
        f"Отличная работа! 👏",
        reply_markup=master_main_kb()
    )
    await state.clear()

# ==================== Отказ с причиной ====================
@router.callback_query(F.data.startswith("reject_"))
async def reject_order_ask_reason(
    callback: CallbackQuery,
    state: FSMContext
):
    """Запрос причины отказа"""
    order_id = int(callback.data.split("_")[1])
    await state.update_data(reject_order_id=order_id)
    await state.set_state(MasterStates.waiting_reject_reason)
    
    await callback.message.edit_text(
        "❌ Укажите причину отказа от заявки:\n\n"
        "Например:\n"
        "- Занят на другом объекте\n"
        "- Слишком далеко\n"
        "- Нет нужных запчастей\n"
        "- Проблема не по моей специализации\n\n"
        "Или отправьте /cancel для отмены"
    )
    await callback.answer()

@router.message(MasterStates.waiting_reject_reason, F.text == "/cancel")
async def cancel_reject(msg: Message, state: FSMContext):
    """Бекор қилиш"""
    await state.clear()
    await msg.answer(
        "❌ Отказ отменён",
        reply_markup=master_main_kb()
    )

@router.message(MasterStates.waiting_reject_reason)
async def reject_order_with_reason(
    msg: Message,
    state: FSMContext,
    master: Master,
    order_service: OrderService,
    master_service: MasterService,
    bot: Bot
):
    """Отказ от заявки с причиной и попытка переназначения"""
    reject_reason = msg.text.strip()
    
    if len(reject_reason) < 5:
        await msg.answer("❌ Причина слишком короткая. Укажите более подробно:")
        return
    
    data = await state.get_data()
    order_id = data["reject_order_id"]
    
    order = await order_service.order_repo.get_with_skills(order_id)
    if not order:
        await msg.answer("❌ Заявка не найдена!", reply_markup=master_main_kb())
        await state.clear()
        return
    
    assignment = await order_service.assignment_repo.get_by_order(order_id)
    if assignment:
        await order_service.assignment_repo.delete(assignment.id)
    
    await master_service.update_schedule(master.id, order.datetime, "отменено")
    order = await order_service.update_status(order_id, OrderStatus.rejected)
    
    await order_service.session.commit()
    
    skill_ids = [s.id for s in order.required_skills] if order.required_skills else []
    new_master = await master_service.find_available_master(
        datetime=order.datetime,
        skill_ids=skill_ids,
        exclude_master_id=master.id
    )
    
    if new_master:
        await order_service.assign_master_to_order(order_id, new_master.id)
        order = await order_service.update_status(order_id, OrderStatus.new)
        await order_service.session.commit()
        
        await bot.send_message(
            new_master.telegram_id,
            f"🆕 Новая заявка #{order.number}!\n\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📞 Телефон: {order.phone}\n"
            f"📍 Адрес: {order.address}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
            f"🔧 Техника: {order.type} {order.brand} {order.model}\n"
            f"💬 Проблема: {order.comment}",
            reply_markup=order_status_kb(order.id, OrderStatus.new)
        )
        
        await notify_admins(
            bot,
            f"❌ Мастер отказался от заказа\n\n"
            f"👤 Отказался: {master.name}\n"
            f"💬 Причина: {reject_reason}\n\n"
            f"✅ Заказ автоматически переназначен:\n"
            f"👤 Новый мастер: {new_master.name}\n"
            f"📋 Заказ: #{order.number}\n"
            f"👥 Клиент: {order.client_name}\n"
            f"📍 Адрес: {order.address}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}"
        )
        
        await msg.answer(
            f"❌ Вы отказались от заявки #{order.number}\n\n"
            f"✅ Заявка автоматически назначена другому мастеру: {new_master.name}",
            reply_markup=master_main_kb()
        )
    else:
        await notify_admins(
            bot,
            f"❌ Мастер отказался от заказа!\n\n"
            f"👤 Отказался: {master.name}\n"
            f"💬 Причина: {reject_reason}\n\n"
            f"⚠️ Свободный мастер не найден!\n"
            f"📋 Заказ: #{order.number}\n"
            f"👥 Клиент: {order.client_name}\n"
            f"📍 Адрес: {order.address}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Назначьте мастера вручную через меню 'Заявки'"
        )
        
        await msg.answer(
            f"❌ Вы отказались от заявки #{order.number}\n\n"
            f"⚠️ Свободный мастер не найден.\n"
            f"Заявка будет назначена администратором.",
            reply_markup=master_main_kb()
        )
    
    try:
        await bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id - 1)
    except:
        pass
    
    await state.clear()

# ==================== Назад к списку заявок ====================
@router.callback_query(F.data == "back_to_orders")
async def back_to_orders(callback: CallbackQuery, master: Master, master_service: MasterService):
    """Вернуться к списку заявок"""
    orders = await master_service.get_master_orders(master.id)
    
    if not orders:
        await callback.message.edit_text(
            "📋 У вас пока нет заявок.\n"
            "Ожидайте назначения от администратора.",
            reply_markup=master_orders_kb()
        )
        await callback.answer()
        return
    
    text = "📋 Ваши заявки:\n\n"
    active = [o for o in orders if o.status in [OrderStatus.new, OrderStatus.confirmed, OrderStatus.in_progress, OrderStatus.arrived]]
    
    if active:
        text += "🔄 Активные:\n"
        for order in active[:5]:
            emoji = get_status_emoji(order.status.value)
            text += (
                f"{emoji} #{order.number}\n"
                f" Клиент: {order.client_name}\n"
                f" Адрес: {order.address}\n"
                f" Время: {order.datetime.strftime('%d.%m %H:%M')}\n\n"
            )
    
    completed = [o for o in orders if o.status == OrderStatus.completed]
    if completed:
        text += f"\n✅ Завершено: {len(completed)}"
    
    await callback.message.edit_text(text, reply_markup=master_orders_kb(bool(active)))
    await callback.answer()

# ==================== Сообщение админу ====================
@router.message(F.text == "💬 Админу")
async def message_admin_start(msg: Message, state: FSMContext):
    """Начало отправки сообщения админу"""
    await state.clear()
    await state.set_state(MasterStates.waiting_admin_message)
    await msg.answer(
        "💬 Напишите сообщение администратору:\n"
        "(или отправьте /cancel для отмены)"
    )

@router.message(MasterStates.waiting_admin_message)
async def send_message_to_admin(msg: Message, state: FSMContext, master: Master, bot: Bot):
    """Отправка сообщения админу"""
    admin_message = (
        f"📨 Сообщение от мастера:\n\n"
        f"👤 {master.name} (ID: {master.telegram_id})\n"
        f"💬 {msg.text}"
    )
    
    success_count = 0
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_message)
            success_count += 1
        except Exception:
            continue
    
    if success_count > 0:
        await msg.answer(
            "✅ Сообщение отправлено администратору!",
            reply_markup=master_main_kb()
        )
    else:
        await msg.answer(
            "❌ Не удалось отправить сообщение.\n"
            "Попробуйте позже.",
            reply_markup=master_main_kb()
        )
    
    await state.clear()