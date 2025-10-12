from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.keyboards import master_main_kb, order_status_kb, master_orders_kb
from services.services import OrderService, MasterService
from models import OrderStatus, Master
from core.utils import get_status_emoji, format_money
from filters.role import RoleFilter
from config import ADMIN_IDS
router = Router()
# ==================== FSM States ====================
class MasterStates(StatesGroup):
    waiting_work_amount = State()
    waiting_expenses = State()
    waiting_work_photos = State()
    waiting_work_description = State()
    waiting_admin_message = State()
    waiting_reject_reason = State() # НОВОЕ: ожидание причины отказа
# ==================== Adminlarga xabar yuborish ====================
async def notify_admins(bot: Bot, message: str, photos: list = None):
    """Barcha adminlarga xabar yuborish, shu bilan birga fotolar"""
    for admin_id in ADMIN_IDS:
        try:
            # Avval matn yuboramiz
            await bot.send_message(admin_id, message)
           
            # Agar fotolar bo'lsa, media group sifatida yuboramiz
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
   
    # Разделяем на активные и завершенные
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
# ==================== Управление статусом ====================
@router.callback_query(F.data.startswith("confirm_"))
async def confirm_order(
    callback: CallbackQuery,
    master: Master,
    order_service: OrderService,
    master_service: MasterService,  # ДОБАВЛЕНО
    bot: Bot
):
    """Подтверждение заявки мастером"""
    order_id = int(callback.data.split("_")[1])
    
    # Обновляем статус на confirmed
    order = await order_service.update_status(order_id, OrderStatus.confirmed)
    
    # ВАЖНО: Теперь резервируем время мастера
    await master_service.update_schedule(master.id, order.datetime, "busy")
    await order_service.session.commit()
    
    # Adminlarga xabar
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
   
    # Adminlarga xabar
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
   
    # Adminlarga xabar
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
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n",
        f"Начинайте работу.\n"
        f"После завершения нажмите 'Завершить'.",
        reply_markup=order_status_kb(order.id, order.status)
    )
    await callback.answer("🏠 Прибыли")
@router.callback_query(F.data.startswith("complete_"))
async def complete_order_start(
    callback: CallbackQuery,
    state: FSMContext
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
   
    # Сохраняем file_id самого большого фото
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
   
    # Adminlarga xabar va fotolar
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
# ==================== НОВОЕ: Отказ с причиной ====================
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
        "- Проблема не по моей специализации"
    )
    await callback.answer()
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
   
    # Получаем заказ с навыками
    order = await order_service.order_repo.get_with_skills(order_id)
    if not order:
        await msg.answer("❌ Заявка не найдена!", reply_markup=master_main_kb())
        await state.clear()
        return
   
    # Обновляем статус на rejected
    order.status = OrderStatus.rejected
   
    # Удаляем назначение на текущего мастера
    assignment = await order_service.assignment_repo.get_by_order(order_id)
    if assignment:
        await order_service.assignment_repo.delete(assignment.id)
   
    # Освобождаем время в графике мастера
    await master_service.update_schedule(master.id, order.datetime, "free")
   
    await order_service.session.commit()
   
    # Сохраняем причину отказа в комментарий или отдельное поле
    # (если нужно, добавьте поле reject_reason в модель Order)
   
    # Пытаемся найти другого мастера автоматически
    skill_ids = [s.id for s in order.required_skills] if order.required_skills else []
    new_master = await master_service.find_available_master(
        datetime=order.datetime,
        skill_ids=skill_ids,
        exclude_master_id=master.id
    )
   
    if new_master:
        # Назначаем новому мастеру
        await order_service.assignment_repo.create(order_id=order_id, master_id=new_master.id)
        order.status = OrderStatus.confirmed
        await master_service.update_schedule(new_master.id, order.datetime, "busy")
        await order_service.session.commit()
       
        # Уведомляем нового мастера
        await bot.send_message(
            new_master.telegram_id,
            f"🆕 Новая заявка #{order.number}!\n\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📞 Телефон: {order.phone}\n"
            f"📍 Адрес: {order.address}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
            f"🔧 Техника: {order.type} {order.brand} {order.model}\n"
            f"💬 Проблема: {order.comment}",
            reply_markup=order_status_kb(order.id, order.status)
        )
       
        # Уведомляем админа об успешном переназначении
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
            f"✅ Заявка автоматически назначена другому мастеру.",
            reply_markup=master_main_kb()
        )
    else:
        # Не найден свободный мастер - требуется ручное назначение админом
        from core.keyboards import manual_master_selection_kb
       
        admin_kb = await manual_master_selection_kb(order.id)
       
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
            f"👇 Назначьте мастера вручную:"
        )
       
        # Отправляем клавиатуру для ручного назначения админу
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"Выберите мастера для заявки #{order.number}:",
                    reply_markup=admin_kb
                )
            except Exception:
                continue
       
        await msg.answer(
            f"❌ Вы отказались от заявки #{order.number}\n\n"
            f"⚠️ Заявка требует назначения администратором.",
            reply_markup=master_main_kb()
        )
   
    await state.clear()
# ==================== График ====================
@router.message(F.text == "📅 График")
async def show_schedule(msg: Message, state: FSMContext, master: Master):
    """Показать график работы"""
    await state.clear()
    if not master.schedule:
        await msg.answer(
            "📅 Ваш график пуст.\n"
            "График автоматически заполняется при назначении заявок.",
            reply_markup=master_main_kb()
        )
        return
   
    text = "📅 Ваш график:\n\n"
   
    sorted_dates = sorted(master.schedule.keys())
   
    for date_str in sorted_dates[:7]:
        times = master.schedule[date_str]
        if times:
            text += f"📆 {date_str}:\n"
            for time in sorted(times):
                text += f" • {time}\n"
            text += "\n"
   
    await msg.answer(text, reply_markup=master_main_kb())
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
@router.callback_query(F.data == "master_orders_active")
async def show_active_orders(
    callback: CallbackQuery,
    master: Master,
    master_service: MasterService
):
    """Показать только активные заявки"""
    orders = await master_service.get_master_orders(master.id)
   
    active = [o for o in orders if o.status in [
        OrderStatus.new,
        OrderStatus.confirmed,
        OrderStatus.in_progress,
        OrderStatus.arrived
    ]]
   
    if not active:
        await callback.message.edit_text(
            "📋 Нет активных заявок",
            reply_markup=master_orders_kb()
        )
        await callback.answer()
        return
   
    text = "🔄 Активные заявки:\n\n"
    for order in active:
        emoji = get_status_emoji(order.status.value)
        text += (
            f"{emoji} #{order.number}\n"
            f" Клиент: {order.client_name}\n"
            f" Адрес: {order.address}\n"
            f" Время: {order.datetime.strftime('%d.%m %H:%M')}\n"
            f" Статус: {order.status.value}\n\n"
        )
   
    await callback.message.edit_text(text, reply_markup=master_orders_kb())
    await callback.answer()
@router.callback_query(F.data == "master_orders_archive")
async def show_archive_orders(
    callback: CallbackQuery,
    master: Master,
    master_service: MasterService
):
    orders = await master_service.get_master_orders(master.id)
   
    completed = [o for o in orders if o.status == OrderStatus.completed]
   
    if not completed:
        await callback.message.edit_text(
            "📋 Архив пуст",
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

