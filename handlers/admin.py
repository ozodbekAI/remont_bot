from datetime import datetime, date, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import pandas as pd
import io
from core.keyboards import (
    admin_main_kb, order_status_kb, filters_kb, masters_menu_kb,
    skills_checkbox_kb, master_update_selection_kb, master_delete_selection_kb,
    master_update_menu_kb, master_delete_confirm_kb, reports_menu_kb,
    period_selection_kb, manual_master_selection_kb
)
from core.utils import validate_phone
from services.services import (
    OrderService, MasterService,
    SkillService, ReportService
)
from models import OrderStatus
from filters.role import RoleFilter
router = Router()
# ==================== FSM States ====================
class AdminStates(StatesGroup):
    # Новая заявка
    waiting_client_name = State()
    waiting_phone = State()
    waiting_address = State()
    waiting_datetime = State()
    waiting_skills = State() # НОВОЕ: выбор навыков
    waiting_type = State()
    waiting_brand = State()
    waiting_model = State()
    waiting_comment = State()
    manual_master_selection = State() # НОВОЕ: ручное назначение мастера
   
    # Добавление навыка
    adding_skill_name = State()
    adding_skill_description = State()
   
    # Добавление мастера
    adding_master_name = State()
    adding_master_phone = State()
    adding_master_telegram = State()
    adding_master_skills = State()
   
    # Обновление мастера
    selecting_master_to_update = State()
    updating_master_name = State()
    updating_master_phone = State()
    updating_master_telegram = State()
    updating_master_skills = State()
   
    # Удаление мастера
    selecting_master_to_delete = State()
    confirming_delete = State()
    # Отчеты (новые состояния)
    selecting_report_type = State()
    selecting_period = State()
    waiting_date_from = State()
    waiting_date_to = State()
    selecting_master_filter = State() # Фильтр по мастеру для отчетов
# ==================== Главное меню ====================
@router.message(F.text == "/start", RoleFilter("admin"))
async def admin_start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "👋 Добро пожаловать, админ!\n"
        "Выберите действие:",
        reply_markup=admin_main_kb()
    )
# ==================== Новая заявка ====================
@router.message(F.text == "🆕 Новая заявка")
async def new_order_start(msg: Message, state: FSMContext):
    await state.clear() # Clear any previous state
    await state.set_state(AdminStates.waiting_client_name)
    await msg.answer("📝 Введите имя клиента:")
@router.message(AdminStates.waiting_client_name)
async def process_client_name(msg: Message, state: FSMContext):
    await state.update_data(client_name=msg.text.strip())
    await state.set_state(AdminStates.waiting_phone)
    await msg.answer("📞 Введите телефон (например: +79181234567):")
@router.message(AdminStates.waiting_phone)
async def process_phone(msg: Message, state: FSMContext):
    phone = msg.text.strip()
    if not validate_phone(phone):
        await msg.answer(
            "❌ Неверный формат телефона.\n"
            "Пример: +79181234567\n"
            "Попробуйте снова:"
        )
        return
   
    await state.update_data(phone=phone)
    await state.set_state(AdminStates.waiting_address)
    await msg.answer("📍 Введите адрес (например: Мирабадский район, ул. Авиасозлар 12):")
@router.message(AdminStates.waiting_address)
async def process_address(msg: Message, state: FSMContext):
    await state.update_data(address=msg.text.strip())
    await state.set_state(AdminStates.waiting_datetime)
    await msg.answer(
        "📅 Введите дату и время визита\n"
        "Формат: YYYY-MM-DD HH:MM\n"
        "Например: 2025-10-15 14:00"
    )
@router.message(AdminStates.waiting_datetime)
async def process_datetime(msg: Message, state: FSMContext, skill_service: SkillService):
    dt_str = msg.text.strip()
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        if dt < datetime.now():
            await msg.answer("❌ Дата не может быть в прошлом. Попробуйте снова:")
            return
       
        await state.update_data(datetime=dt)
       
        # НОВОЕ: Выбор навыков
        await state.set_state(AdminStates.waiting_skills)
        kb = await skills_checkbox_kb()
        await msg.answer(
            "🔧 Выберите необходимые навыки для заявки:\n"
            "(можно несколько)",
            reply_markup=kb
        )
    except ValueError:
        await msg.answer(
            "❌ Неверный формат.\n"
            "Пример: 2025-10-15 14:00\n"
            "Попробуйте снова:"
        )
@router.callback_query(F.data.startswith("skill_toggle_"), AdminStates.waiting_skills)
async def toggle_order_skill(callback: CallbackQuery, state: FSMContext):
    """Переключение навыка при создании заявки"""
    skill_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    selected = data.get("selected_skills", [])
   
    if skill_id in selected:
        selected.remove(skill_id)
    else:
        selected.append(skill_id)
   
    await state.update_data(selected_skills=selected)
   
    # Обновляем клавиатуру
    kb = await skills_checkbox_kb(selected)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()
@router.callback_query(F.data == "skills_done", AdminStates.waiting_skills)
async def skills_done(callback: CallbackQuery, state: FSMContext):
    """Завершение выбора навыков"""
    data = await state.get_data()
    if not data.get("selected_skills"):
        await callback.answer("❌ Выберите хотя бы один навык!", show_alert=True)
        return
   
    await state.set_state(AdminStates.waiting_type)
    await callback.message.edit_text("🔧 Введите тип техники (например: стиральная машина, холодильник):")
    await callback.answer()
@router.message(AdminStates.waiting_type)
async def process_type(msg: Message, state: FSMContext):
    await state.update_data(type=msg.text.strip())
    await state.set_state(AdminStates.waiting_brand)
    await msg.answer("🏷️ Введите бренд (например: Samsung, LG, Artel):")
@router.message(AdminStates.waiting_brand)
async def process_brand(msg: Message, state: FSMContext):
    await state.update_data(brand=msg.text.strip())
    await state.set_state(AdminStates.waiting_model)
    await msg.answer("📱 Введите модель:")
@router.message(AdminStates.waiting_model)
async def process_model(msg: Message, state: FSMContext):
    await state.update_data(model=msg.text.strip())
    await state.set_state(AdminStates.waiting_comment)
    await msg.answer("💬 Опишите проблему:")
# Admin.py faylidagi create_order handlerini tekshiring va to'g'rilang:
@router.message(AdminStates.waiting_comment)
async def create_order(msg: Message, state: FSMContext, order_service: OrderService, bot: Bot, master_service: MasterService):
    """Создание заявки с назначением мастера"""
    data = await state.get_data()
   
    # Создаем заявку и пытаемся назначить
    order, assigned = await order_service.create_order(
        client_name=data["client_name"],
        phone=data["phone"],
        address=data["address"],
        datetime=data["datetime"],
        type=data["type"],
        brand=data["brand"],
        model=data["model"],
        comment=msg.text.strip(),
        skill_ids=data.get("selected_skills", [])
    )
   
    if assigned:
        # Получаем мастера для уведомления (после commit в сервисе)
        assignment = await order_service.assignment_repo.get_by_order(order.id)
        master = assignment.master if assignment else None
        if master:
            await msg.answer(
                f"✅ Заявка #{order.number} создана!\n"
                f"👤 Назначен мастер: {master.name}\n"
                f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}",
                reply_markup=admin_main_kb()
            )
           
            # Уведомление мастеру - ИСПРАВЛЕНО: используем order.id вместо order_id
            await bot.send_message(
                master.telegram_id,
                f"🆕 Новая заявка #{order.number}!\n\n"
                f"👤 Клиент: {order.client_name}\n"
                f"📞 Телефон: {order.phone}\n"
                f"📍 Адрес: {order.address}\n"
                f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
                f"🔧 Техника: {order.type} {order.brand} {order.model}\n"
                f"💬 Проблема: {order.comment}",
                reply_markup=order_status_kb(order.id, order.status) # ИСПРАВЛЕНО
            )
            await state.clear() # ИСПРАВЛЕНО: очищаем state после успешного создания
    else:
        # НОВОЕ: Если не назначен автоматически, предлагаем ручное назначение
        await state.update_data(order_id=order.id, order_number=order.number, order_datetime=order.datetime)
        await state.set_state(AdminStates.manual_master_selection)
        kb = await manual_master_selection_kb(order.id)
        await msg.answer(
            f"⚠️ Заявка #{order.number} создана, но нет свободного мастера!\n"
            f"Выберите мастера для ручного назначения:",
            reply_markup=kb
        )
# Также проверьте manual_assign_master_from_creation handler:
@router.callback_query(F.data.startswith("assign_manual_"), AdminStates.manual_master_selection)
async def manual_assign_master_from_creation(
    callback: CallbackQuery,
    state: FSMContext,
    order_service: OrderService,
    master_service: MasterService,
    bot: Bot
):
    """Ручное назначение мастера при создании заявки"""
    parts = callback.data.split("_")
    master_id = int(parts[2])
    order_id = int(parts[3])
   
    master = await master_service.master_repo.get(master_id)
    if not master:
        await callback.answer("❌ Мастер не найден!")
        return
   
    # Проверяем что заказ не назначен уже
    existing = await order_service.assignment_repo.get_by_order(order_id)
    if existing:
        await callback.answer("❌ Заявка уже назначена!", show_alert=True)
        await state.clear()
        return
   
    # Назначаем
    await order_service.assignment_repo.create(order_id=order_id, master_id=master_id)
    order = await order_service.order_repo.get(order_id)
    order.status = OrderStatus.confirmed
    await master_service.update_schedule(master_id, order.datetime, "busy")
    await order_service.session.commit()
   
    data = await state.get_data()
    await callback.message.edit_text(
        f"✅ Мастер {master.name} назначен на заявку #{data.get('order_number', order.number)}!\n"
        f"📅 Время: {data.get('order_datetime', order.datetime).strftime('%d.%m.%Y %H:%M')}"
    )
   
    # Уведомление мастеру - ИСПРАВЛЕНО: используем order.id и order.status
    await bot.send_message(
        master.telegram_id,
        f"🆕 Новая заявка #{order.number}!\n\n"
        f"👤 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔧 Техника: {order.type} {order.brand} {order.model}\n"
        f"💬 Проблема: {order.comment}",
        reply_markup=order_status_kb(order.id, order.status) # ИСПРАВLЕНО
    )
   
    await callback.message.answer("Выберите действие:", reply_markup=admin_main_kb())
    await state.clear()
    await callback.answer()
# Shuningdek manual_assign_master_from_reject handlerini ham tekshiring:
@router.callback_query(F.data.startswith("assign_manual_"))
async def manual_assign_master_from_reject(
    callback: CallbackQuery,
    order_service: OrderService,
    master_service: MasterService,
    bot: Bot
):
    """Ручное назначение мастера после отказа (БЕЗ STATE)"""
    parts = callback.data.split("_")
    master_id = int(parts[2])
    order_id = int(parts[3])
   
    master = await master_service.master_repo.get(master_id)
    if not master:
        await callback.answer("❌ Мастер не найден!")
        return
   
    # Проверяем что заказ еще не назначен
    existing = await order_service.assignment_repo.get_by_order(order_id)
    if existing:
        await callback.answer("❌ Заявка уже назначена другому мастеру!", show_alert=True)
        await callback.message.edit_text(
            f"⚠️ Заявка #{order_id} уже назначена.\n"
            f"Мастер: {existing.master.name}"
        )
        return
   
    # Получаем заказ
    order = await order_service.order_repo.get(order_id)
    if not order:
        await callback.answer("❌ Заявка не найдена!")
        return
   
    # Назначаем
    await order_service.assignment_repo.create(order_id=order_id, master_id=master_id)
    order.status = OrderStatus.confirmed
    await master_service.update_schedule(master_id, order.datetime, "busy")
    await order_service.session.commit()
   
    await callback.message.edit_text(
        f"✅ Мастер {master.name} назначен на заявку #{order.number}!\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"Уведомление отправлено мастеру."
    )
   
    # Уведомление мастеру - ИСПРАВЛЕНО: order.id va order.status
    await bot.send_message(
        master.telegram_id,
        f"🆕 Новая заявка #{order.number}!\n\n"
        f"👤 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔧 Техника: {order.type} {order.brand} {order.model}\n"
        f"💬 Проблема: {order.comment}",
        reply_markup=order_status_kb(order.id, order.status) # ИСПРАВЛЕНО
    )
   
    await callback.answer("✅ Мастер назначен!")
# Shuningdek cancel_manual_ uchun ham STATE SETSIZ handler qo'shing:
@router.callback_query(F.data.startswith("cancel_manual_"), AdminStates.manual_master_selection)
async def cancel_manual_assignment_with_state(callback: CallbackQuery, state: FSMContext):
    """Отмена при создании заявки"""
    await state.clear()
    await callback.message.answer(
        "⚠️ Заявка создана без мастера. Система попробует назначить позже.",
        reply_markup=admin_main_kb()
    )
    await callback.answer()
@router.callback_query(F.data.startswith("cancel_manual_"))
async def cancel_manual_assignment_no_state(callback: CallbackQuery):
    """Отмена после отказа мастера"""
    await callback.message.edit_text(
        "❌ Назначение отменено.\n"
        "Заявка осталась без мастера."
    )
    await callback.answer()
# ==================== Список заявок ====================
@router.message(F.text == "📋 Заявки")
async def list_orders(msg: Message, state: FSMContext):
    await state.clear() # Ensure state is cleared for menu actions
    kb = filters_kb()
    await msg.answer("📋 Выберите фильтр:", reply_markup=kb)
@router.callback_query(F.data.startswith("filter_"))
async def filter_orders(callback: CallbackQuery, order_service: OrderService):
    filter_type = callback.data.split("_")[1]
   
    if filter_type == "all":
        orders = await order_service.get_orders_by_filter()
    elif filter_type == "new":
        orders = await order_service.get_orders_by_filter(status=OrderStatus.new)
    elif filter_type == "work":
        orders = await order_service.get_orders_by_filter(
            status=OrderStatus.in_progress
        )
    elif filter_type == "done":
        orders = await order_service.get_orders_by_filter(
            status=OrderStatus.completed
        )
    else:
        orders = []
   
    if not orders:
        await callback.message.edit_text(
            f"📋 Нет заявок ({filter_type})",
            reply_markup=filters_kb()
        )
        await callback.answer()
        return
   
    text = f"📋 Заявки ({filter_type}):\n\n"
    builder = InlineKeyboardBuilder()
   
    for order in orders[:10]:
        # Получаем информацию о мастере
        assignment = await order_service.assignment_repo.get_by_order(order.id)
        assigned_master = assignment.master.name if assignment and assignment.master else "Не назначен"
       
        text += (
            f"#{order.number} - {order.client_name}\n"
            f"🔧 Тип: {order.type} {order.brand} {order.model}\n"
            f"👤 Мастер: {assigned_master}\n"
            f"Статус: {order.status.value}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
            f"📍 Адрес: {order.address}\n"
            f"💬 Проблема: {order.comment[:50]}{'...' if len(order.comment) > 50 else ''}\n\n"
        )
       
        # НОВОЕ: Добавляем кнопку назначения для всех незаназначенных или отклоненных заявок
        if assigned_master == "Не назначен" and order.status in [OrderStatus.new, OrderStatus.rejected]:
            builder.row(
                InlineKeyboardButton(
                    text=f"👤 Назначить мастера #{order.number}",
                    callback_data=f"assign_order_{order.id}"
                )
            )
   
    # Добавляем кнопки фильтров
    builder.row(
        InlineKeyboardButton(text="📋 Все", callback_data="filter_all"),
        InlineKeyboardButton(text="🆕 Новые", callback_data="filter_new")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ В работе", callback_data="filter_work"),
        InlineKeyboardButton(text="✅ Готовые", callback_data="filter_done")
    )
   
    markup = builder.as_markup()
   
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()
# НОВОЕ: Обновленный start_assign_existing_order handler
@router.callback_query(F.data.startswith("assign_order_"))
async def start_assign_existing_order(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Начало ручного назначения для существующей незанятой заявки"""
    order_id = int(callback.data.split("_")[2])
    order = await order_service.order_repo.get(order_id)
    if not order:
        await callback.answer("❌ Заявка не найдена!")
        return
   
    # ИЗМЕНЕНО: Разрешаем назначать не только новые, но и отклоненные заявки
    if order.status not in [OrderStatus.new, OrderStatus.rejected]:
        await callback.answer("❌ Можно назначать только новые или отклоненные заявки!", show_alert=True)
        return
   
    # Проверяем, назначен ли уже
    assignment = await order_service.assignment_repo.get_by_order(order_id)
    if assignment:
        await callback.answer("❌ Заявка уже назначена!", show_alert=True)
        return
   
    await state.update_data(
        order_id=order.id,
        order_number=order.number,
        order_datetime=order.datetime
    )
    await state.set_state(AdminStates.manual_master_selection)
   
    kb = await manual_master_selection_kb(order.id)
   
    # НОВОЕ: Более информативное сообщение
    status_text = "🆕 Новая заявка" if order.status == OrderStatus.new else "❌ Отклоненная заявка"
   
    await callback.message.edit_text(
        f"{status_text}\n\n"
        f"📋 Заявка #{order.number}\n"
        f"👤 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔧 Техника: {order.type} {order.brand} {order.model}\n"
        f"💬 Проблема: {order.comment}\n\n"
        f"Выберите мастера для назначения:",
        reply_markup=kb
    )
    await callback.answer()
# ==================== Мастера и навыки ====================
@router.message(F.text == "👥 Мастера и навыки")
async def masters_menu(msg: Message, state: FSMContext):
    await state.clear() # Ensure state is cleared for menu actions
    kb = masters_menu_kb()
    await msg.answer("👥 Управление мастерами и навыками:", reply_markup=kb)
@router.callback_query(F.data == "list_skills")
async def list_skills(callback: CallbackQuery, skill_service: SkillService):
    """Список всех навыков"""
    skills = await skill_service.get_all_skills()
   
    if not skills:
        text = "📚 Навыков пока нет. Добавьте первый!"
    else:
        text = "📚 Список навыков:\n\n"
        for skill in skills:
            text += f"• {skill.name}\n"
            if skill.description:
                text += f" {skill.description}\n"
   
    await callback.message.edit_text(text, reply_markup=masters_menu_kb())
    await callback.answer()
@router.callback_query(F.data == "add_skill")
async def add_skill_start(callback: CallbackQuery, state: FSMContext):
    await state.clear() # Clear previous states
    await state.set_state(AdminStates.adding_skill_name)
    await callback.message.edit_text("📚 Введите название навыка:")
    await callback.answer()
@router.message(AdminStates.adding_skill_name)
async def process_skill_name(msg: Message, state: FSMContext):
    await state.update_data(skill_name=msg.text.strip())
    await state.set_state(AdminStates.adding_skill_description)
    await msg.answer("📝 Введите описание (или отправьте '-' чтобы пропустить):")
@router.message(AdminStates.adding_skill_description)
async def save_skill(msg: Message, state: FSMContext, skill_service: SkillService):
    data = await state.get_data()
    description = None if msg.text.strip() == "-" else msg.text.strip()
   
    skill = await skill_service.create_skill(
        name=data["skill_name"],
        description=description
    )
   
    await msg.answer(
        f"✅ Навык '{skill.name}' добавлен!",
        reply_markup=admin_main_kb()
    )
    await state.clear()
@router.callback_query(F.data == "list_masters")
async def list_masters(callback: CallbackQuery, master_service: MasterService):
    """Список всех мастеров"""
    masters = await master_service.get_all_with_skills()
   
    if not masters:
        text = "👥 Мастеров пока нет. Добавьте первого!"
    else:
        text = "👥 Список мастеров:\n\n"
        for master in masters:
            skills_text = ", ".join([s.name for s in master.skills]) if master.skills else "Нет навыков"
            status = "🟢 Онлайн" if master.is_online else "⚪ Оффлайн"
            text += (
                f"• {master.name} {status}\n"
                f" ID: {master.telegram_id}\n"
                f" Навыки: {skills_text}\n\n"
            )
   
    await callback.message.edit_text(text, reply_markup=masters_menu_kb())
    await callback.answer()
@router.callback_query(F.data == "add_master")
async def add_master_start(callback: CallbackQuery, state: FSMContext):
    await state.clear() # Clear previous states
    await state.set_state(AdminStates.adding_master_name)
    await callback.message.edit_text("👤 Введите имя мастера:")
    await callback.answer()
@router.message(AdminStates.adding_master_name)
async def process_master_name(msg: Message, state: FSMContext):
    await state.update_data(master_name=msg.text.strip())
    await state.set_state(AdminStates.adding_master_phone)
    await msg.answer("📞 Введите телефон мастера (или '-' чтобы пропустить):")
@router.message(AdminStates.adding_master_phone)
async def process_master_phone(msg: Message, state: FSMContext):
    phone = None if msg.text.strip() == "-" else msg.text.strip()
    await state.update_data(master_phone=phone)
    await state.set_state(AdminStates.adding_master_telegram)
    await msg.answer("📱 Введите Telegram ID мастера (число):")
@router.message(AdminStates.adding_master_telegram)
async def process_master_telegram(msg: Message, state: FSMContext):
    try:
        telegram_id = int(msg.text.strip())
        await state.update_data(master_telegram_id=telegram_id)
        await state.set_state(AdminStates.adding_master_skills)
       
        kb = await skills_checkbox_kb()
        await msg.answer(
            "🔧 Выберите навыки мастера:",
            reply_markup=kb
        )
    except ValueError:
        await msg.answer("❌ Telegram ID должен быть числом. Попробуйте снова:")
@router.callback_query(F.data.startswith("skill_toggle_"), AdminStates.adding_master_skills)
async def toggle_master_skill(callback: CallbackQuery, state: FSMContext):
    """Переключение навыка при создании мастера"""
    skill_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    selected = data.get("selected_skills", [])
   
    if skill_id in selected:
        selected.remove(skill_id)
    else:
        selected.append(skill_id)
   
    await state.update_data(selected_skills=selected)
   
    kb = await skills_checkbox_kb(selected)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()
@router.callback_query(F.data == "skills_done", AdminStates.adding_master_skills)
async def save_master(callback: CallbackQuery, state: FSMContext, master_service: MasterService):
    """Сохранение мастера с навыками"""
    data = await state.get_data()
   
    master_data = await master_service.create_master(
        name=data["master_name"],
        telegram_id=data["master_telegram_id"],
        phone=data.get("master_phone"),
        skill_ids=data.get("selected_skills", [])
    )
   
    # Теперь работаем со словарём, а не ORM объектом
    skills_text = ", ".join([s["name"] for s in master_data["skills"]]) if master_data["skills"] else "без навыков"
   
    await callback.message.edit_text(
        f"✅ Мастер {master_data['name']} добавлен!\n"
        f"Навыки: {skills_text}"
    )
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=admin_main_kb()
    )
    await callback.answer()
    await state.clear()
# ==================== Обновление мастера ====================
@router.callback_query(F.data == "update_master")
async def update_master_start(callback: CallbackQuery, state: FSMContext):
    """Начало обновления мастера"""
    await state.clear()
    await state.set_state(AdminStates.selecting_master_to_update)
    kb = await master_update_selection_kb()
    await callback.message.edit_text(
        "👤 Выберите мастера для обновления:",
        reply_markup=kb
    )
    await callback.answer()
@router.callback_query(F.data.startswith("select_update_"), AdminStates.selecting_master_to_update)
async def select_master_to_update(callback: CallbackQuery, state: FSMContext, master_service: MasterService):
    """Выбор мастера для обновления"""
    master_id = int(callback.data.split("_")[2])
    master = await master_service.master_repo.get_with_skills(master_id)
    if not master:
        await callback.answer("❌ Мастер не найден!")
        return
   
    await state.update_data(master_id=master_id, current_name=master.name, current_phone=master.phone, current_telegram=master.telegram_id)
    selected_skills = [s.id for s in master.skills] if master.skills else []
    await state.update_data(selected_skills=selected_skills)
   
    text = (
        f"👤 Обновление мастера: {master.name}\n\n"
        f"Текущие данные:\n"
        f"📝 Имя: {master.name}\n"
        f"📞 Телефон: {master.phone or 'Не указан'}\n"
        f"📱 Telegram ID: {master.telegram_id}\n"
        f"🔧 Навыки: {', '.join([s.name for s in master.skills]) or 'Нет'}\n\n"
        f"Что обновить? (или /skip для пропуска)"
    )
   
    kb = master_update_menu_kb()
   
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()
@router.callback_query(F.data == "update_name", AdminStates.selecting_master_to_update)
async def update_master_name_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.updating_master_name)
    await callback.message.edit_text("📝 Введите новое имя мастера:")
    await callback.answer()
@router.message(AdminStates.updating_master_name)
async def process_update_master_name(msg: Message, state: FSMContext):
    await state.update_data(new_name=msg.text.strip())
    await state.set_state(AdminStates.selecting_master_to_update)
    await msg.answer("✅ Имя обновлено. Вернитесь к меню обновления.")
@router.callback_query(F.data == "update_phone", AdminStates.selecting_master_to_update)
async def update_master_phone_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.updating_master_phone)
    await callback.message.edit_text("📞 Введите новый телефон (или '-' чтобы пропустить):")
    await callback.answer()
@router.message(AdminStates.updating_master_phone)
async def process_update_master_phone(msg: Message, state: FSMContext):
    phone = None if msg.text.strip() == "-" else msg.text.strip()
    if phone and not validate_phone(phone):
        await msg.answer("❌ Неверный формат. Попробуйте снова:")
        return
    await state.update_data(new_phone=phone)
    await state.set_state(AdminStates.selecting_master_to_update)
    await msg.answer("✅ Телефон обновлен.")
@router.callback_query(F.data == "update_telegram", AdminStates.selecting_master_to_update)
async def update_master_telegram_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.updating_master_telegram)
    await callback.message.edit_text("📱 Введите новый Telegram ID (число):")
    await callback.answer()
@router.message(AdminStates.updating_master_telegram)
async def process_update_master_telegram(msg: Message, state: FSMContext):
    try:
        telegram_id = int(msg.text.strip())
        await state.update_data(new_telegram=telegram_id)
        await state.set_state(AdminStates.selecting_master_to_update)
        await msg.answer("✅ Telegram ID обновлен.")
    except ValueError:
        await msg.answer("❌ Должен быть числом. Попробуйте снова:")
@router.callback_query(F.data == "update_skills", AdminStates.selecting_master_to_update)
async def update_master_skills_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.updating_master_skills)
    data = await state.get_data()
    selected = data.get("selected_skills", [])
    kb = await skills_checkbox_kb(selected)
    await callback.message.edit_text("🔧 Выберите новые навыки мастера:", reply_markup=kb)
    await callback.answer()
@router.callback_query(F.data.startswith("skill_toggle_"), AdminStates.updating_master_skills)
async def toggle_update_master_skill(callback: CallbackQuery, state: FSMContext):
    skill_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    selected = data.get("selected_skills", [])
   
    if skill_id in selected:
        selected.remove(skill_id)
    else:
        selected.append(skill_id)
   
    await state.update_data(selected_skills=selected)
   
    kb = await skills_checkbox_kb(selected)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()
@router.callback_query(F.data == "skills_done", AdminStates.updating_master_skills)
async def finish_update_skills(callback: CallbackQuery, state: FSMContext, master_service: MasterService):
    data = await state.get_data()
    master_id = data.get("master_id")
    skill_ids = data.get("selected_skills", [])
   
    if master_id:
        await master_service.update_skills(master_id, skill_ids)
   
    await state.set_state(AdminStates.selecting_master_to_update)
    await callback.message.edit_text("✅ Навыки обновлены. Вернитесь к меню.")
    await callback.answer()
@router.callback_query(F.data == "save_update", AdminStates.selecting_master_to_update)
async def save_master_update(callback: CallbackQuery, state: FSMContext, master_service: MasterService):
    data = await state.get_data()
    master_id = data["master_id"]
   
    name = data.get("new_name", data.get("current_name"))
    phone = data.get("new_phone", data.get("current_phone"))
    telegram_id = data.get("new_telegram", data.get("current_telegram"))
    skill_ids = data.get("selected_skills", [])
   
    await master_service.update_master(
        master_id=master_id,
        name=name,
        phone=phone,
        telegram_id=telegram_id
    )
    await master_service.update_skills(master_id, skill_ids)
   
    await callback.message.edit_text(f"✅ Мастер {name} обновлен!")
    await callback.message.answer("Выберите действие:", reply_markup=admin_main_kb())
    await state.clear()
    await callback.answer()
# ==================== Удаление мастера ====================
@router.callback_query(F.data == "delete_master")
async def delete_master_start(callback: CallbackQuery, state: FSMContext):
    """Начало удаления мастера"""
    await state.clear()
    await state.set_state(AdminStates.selecting_master_to_delete)
    kb = await master_delete_selection_kb()
    await callback.message.edit_text(
        "🗑️ Выберите мастера для удаления:",
        reply_markup=kb
    )
    await callback.answer()
@router.callback_query(F.data.startswith("select_delete_"), AdminStates.selecting_master_to_delete)
async def select_master_to_delete(callback: CallbackQuery, state: FSMContext, master_service: MasterService):
    """Выбор мастера для удаления"""
    master_id = int(callback.data.split("_")[2])
    master = await master_service.master_repo.get(master_id)
    if not master:
        await callback.answer("❌ Мастер не найден!")
        return
   
    await state.update_data(master_id=master_id, master_name=master.name)
   
    kb = master_delete_confirm_kb(master_id)
   
    await callback.message.edit_text(
        f"🗑️ Вы уверены, что хотите удалить мастера '{master.name}'?\n"
        f"Это действие необратимо!",
        reply_markup=kb
    )
    await state.set_state(AdminStates.confirming_delete)
    await callback.answer()
@router.callback_query(F.data.startswith("confirm_delete_"), AdminStates.confirming_delete)
async def confirm_delete_master(callback: CallbackQuery, state: FSMContext, master_service: MasterService):
    """Подтверждение удаления"""
    master_id = int(callback.data.split("_")[2])
    success = await master_service.delete_master(master_id)
   
    data = await state.get_data()
    if success:
        await callback.message.edit_text(f"✅ Мастер '{data['master_name']}' удален!")
    else:
        await callback.message.edit_text(f"❌ Не удалось удалить мастера '{data['master_name']}'!")
   
    await callback.message.answer("Выберите действие:", reply_markup=admin_main_kb())
    await state.clear()
    await callback.answer()
@router.callback_query(F.data == "masters_cancel")
async def cancel_master_action(callback: CallbackQuery, state: FSMContext):
    """Отмена действий с мастерами"""
    await state.clear()
    await callback.message.edit_text("Действие отменено.", reply_markup=masters_menu_kb())
    await callback.answer()
# ==================== Отчеты ====================
@router.message(F.text == "📊 Отчеты")
async def reports_menu(msg: Message, state: FSMContext):
    """Главное меню отчетов"""
    await state.clear()
    kb = reports_menu_kb()
    await msg.answer("📊 Выберите тип отчета:", reply_markup=kb)
@router.callback_query(F.data == "report_financial")
async def start_financial_report(callback: CallbackQuery, state: FSMContext):
    """Начало финансового отчета"""
    await state.update_data(report_type="financial")
    await state.set_state(AdminStates.selecting_period)
    kb = period_selection_kb()
    await callback.message.edit_text("💰 Финансовый отчет. Выберите период:", reply_markup=kb)
    await callback.answer()
@router.callback_query(F.data == "report_masters")
async def start_masters_report(callback: CallbackQuery, state: FSMContext):
    """Начало отчета по мастерам"""
    await state.update_data(report_type="masters")
    await state.set_state(AdminStates.selecting_period)
    kb = period_selection_kb()
    await callback.message.edit_text("👥 Отчет по мастерам. Выберите период:", reply_markup=kb)
    await callback.answer()
@router.callback_query(F.data == "report_orders")
async def start_orders_report(callback: CallbackQuery, state: FSMContext):
    """Начало отчета по заказам"""
    await state.update_data(report_type="orders")
    await state.set_state(AdminStates.selecting_period)
    kb = period_selection_kb()
    await callback.message.edit_text("📋 Отчет по заказам. Выберите период:", reply_markup=kb)
    await callback.answer()
@router.callback_query(F.data == "export_all")
async def export_all_data(callback: CallbackQuery, state: FSMContext, report_service: ReportService, bot: Bot):
    """Экспорт всех данных в Excel"""
    await state.clear()
   
    try:
        await callback.message.edit_text("⏳ Генерация отчета... Пожалуйста, подождите.")
       
        # Получаем все данные
        export_data = await report_service.get_all_export_data()
        # Генерация Excel с несколькими листами
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, df in export_data.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        output.seek(0)
        filename = f"all_data_export_{date.today().strftime('%Y%m%d')}.xlsx"
        document = BufferedInputFile(file=output.getvalue(), filename=filename)
       
        await bot.send_document(
            callback.from_user.id,
            document,
            caption=(
                "📤 Полный экспорт всех данных:\n\n"
                "📋 Заказы - все заказы со статусами, описанием работ и фото\n"
                "👥 Мастера - мастера с навыками и итоговыми расчетами"
            )
        )
        await callback.message.edit_text("✅ Все данные экспортированы в Excel!")
        await callback.answer("✅ Экспорт завершен!")
       
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка при экспорте: {str(e)}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
@router.callback_query(F.data.startswith("period_"), AdminStates.selecting_period)
async def select_period(callback: CallbackQuery, state: FSMContext, report_service: ReportService):
    """Выбор периода и генерация отчета"""
    period = callback.data.split("_")[1]
    data = await state.get_data()
    report_type = data.get("report_type")
    if period == "today":
        date_from = date.today()
        date_to = date_from
        period_text = "сегодня"
    elif period == "week":
        date_from = date.today() - timedelta(days=7)
        date_to = date.today()
        period_text = "неделю"
    elif period == "month":
        date_from = date.today().replace(day=1)
        date_to = date.today()
        period_text = "месяц"
    elif period == "all":
        date_from = None
        date_to = None
        period_text = "весь период"
    elif period == "custom":
        await state.set_state(AdminStates.waiting_date_from)
        await callback.message.edit_text("📅 Введите дату начала (YYYY-MM-DD):")
        await callback.answer()
        return
    else:
        await callback.answer("❌ Неверный период!")
        return
    await state.update_data(date_from=date_from, date_to=date_to, period=period_text)
    # Генерация отчета
    if report_type == "financial":
        report = await report_service.get_financial_report(date_from, date_to)
        text = (
            f"💰 Финансовый отчет ({period_text}):\n\n"
            f"📊 Заказов: {report['orders_count']}\n"
            f"💵 Выручка: {report['total_revenue']:.2f} ₽\n"
            f"💸 Расходы: {report['total_expenses']:.2f} ₽\n"
            f"📈 Прибыль: {report['total_profit']:.2f} ₽\n"
            f"📉 Средняя прибыль: {report['average_profit']:.2f} ₽\n"
        )
    elif report_type == "masters":
        report = await report_service.get_masters_report(date_from, date_to)
        text = f"👥 Отчет по мастерам ({period_text}):\n\n"
        for master_name, stats in report.items():
            text += f"{master_name}: {stats['orders_count']} заказов, прибыль {stats['total_profit']:.2f} ₽\n"
    elif report_type == "orders":
        report = await report_service.get_orders_report(date_from, date_to)
        text = f"📋 Отчет по заказам ({period_text}):\n\n"
        for order in report:
            text += f"#{order.number}: {order.profit:.2f} ₽\n"
    else:
        text = "❌ Неизвестный тип отчета!"
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📤 Экспорт Excel (полный)", callback_data=f"export_{report_type}_{period}"))
    kb.row(InlineKeyboardButton(text="🔙 К отчетам", callback_data="back_to_reports"))
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()
@router.message(AdminStates.waiting_date_from)
async def process_date_from(msg: Message, state: FSMContext):
    try:
        date_from = datetime.strptime(msg.text.strip(), "%Y-%m-%d").date()
        await state.update_data(date_from=date_from)
        await state.set_state(AdminStates.waiting_date_to)
        await msg.answer("📅 Введите дату окончания (YYYY-MM-DD):")
    except ValueError:
        await msg.answer("❌ Неверный формат. Пример: 2025-10-01")
@router.message(AdminStates.waiting_date_to)
async def process_date_to_and_generate(msg: Message, state: FSMContext, report_service: ReportService):
    try:
        date_to = datetime.strptime(msg.text.strip(), "%Y-%m-%d").date()
        data = await state.get_data()
        date_from = data["date_from"]
        report_type = data["report_type"]
        period_text = "период"
        # Генерация отчета (аналогично выше)
        if report_type == "financial":
            report = await report_service.get_financial_report(date_from, date_to)
            text = (
                f"💰 Финансовый отчет ({period_text}):\n\n"
                f"📊 Заказов: {report['orders_count']}\n"
                f"💵 Выручка: {report['total_revenue']:.2f} ₽\n"
                f"💸 Расходы: {report['total_expenses']:.2f} ₽\n"
                f"📈 Прибыль: {report['total_profit']:.2f} ₽\n"
                f"📉 Средняя прибыль: {report['average_profit']:.2f} ₽\n"
            )
        elif report_type == "masters":
            report = await report_service.get_masters_report(date_from, date_to)
            text = f"👥 Отчет по мастерам ({period_text}):\n\n"
            for master_name, stats in report.items():
                text += f"{master_name}: {stats['orders_count']} заказов, прибыль {stats['total_profit']:.2f} ₽\n"
        elif report_type == "orders":
            report = await report_service.get_orders_report(date_from, date_to)
            text = f"📋 Отчет по заказам ({period_text}):\n\n"
            for order in report:
                text += f"#{order.number}: {order.profit:.2f} ₽\n"
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="📤 Экспорт Excel (полный)", callback_data=f"export_{report_type}_custom"))
        kb.row(InlineKeyboardButton(text="🔙 К отчетам", callback_data="back_to_reports"))
        await msg.answer(text, reply_markup=kb.as_markup())
        await state.update_data(date_to=date_to, period=period_text)
    except ValueError:
        await msg.answer("❌ Неверный формат. Пример: 2025-10-15")
    await state.clear()
@router.callback_query(F.data.startswith("export_"))
async def export_report(callback: CallbackQuery, state: FSMContext, report_service: ReportService, bot: Bot):
    """Экспорт полного отчета в Excel"""
    data_parts = callback.data.split("_")
    report_type = data_parts[1]
    period = "_".join(data_parts[2:]) # today, week, month, all, custom
    state_data = await state.get_data()
    date_from = state_data.get("date_from")
    date_to = state_data.get("date_to")
    if report_type == "financial":
        df = await report_service.get_financial_export_data(date_from, date_to)
        sheet_name = "Финансовый отчет"
    elif report_type == "masters":
        df = await report_service.get_masters_export_data(date_from, date_to)
        sheet_name = "Отчет по мастерам"
    elif report_type == "orders":
        df = await report_service.get_orders_export_data(date_from, date_to)
        sheet_name = "Отчет по заказам"
    else:
        await callback.answer("❌ Неизвестный тип отчета!", show_alert=True)
        return
    # Генерация Excel с pandas
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        # Добавляем итоговые строки если нужно
        if report_type == "financial":
            summary_df = pd.DataFrame({
                "Итого": ["Выручка", "Расходы", "Прибыль"],
                "Сумма": [df["Выручка"].sum(), df["Расходы"].sum(), df["Прибыль"].sum()]
            })
            summary_df.to_excel(writer, sheet_name="Итоги", index=False)
    output.seek(0)
    filename = f"{report_type}_{period}_full.xlsx"
    document = BufferedInputFile(file=output.getvalue(), filename=filename)
    await bot.send_document(
        callback.from_user.id,
        document,
        caption=f"📤 Полный экспорт отчета: {report_type} ({period})"
    )
    await callback.answer("✅ Полный отчет экспортирован в Excel!")
@router.callback_query(F.data == "back_to_reports")
async def back_to_reports(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    kb = reports_menu_kb()
    await callback.message.edit_text("📊 Выберите тип отчета:", reply_markup=kb)
    await callback.answer()
@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "👋 Добро пожаловать, админ!\n"
        "Выберите действие:",
        reply_markup=admin_main_kb()
    )
    await callback.answer()
