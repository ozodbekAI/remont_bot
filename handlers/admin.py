from datetime import datetime, date, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import pandas as pd
import io
from core.keyboards import (
    admin_main_kb, order_assignment_choice_kb, master_selection_kb,
    filters_kb, masters_menu_kb, skills_checkbox_kb, order_status_kb,
    reports_menu_kb, period_selection_kb
)
from core.utils import validate_phone
from services.order_service import OrderService
from services.master_service import MasterService
from services.skill_service import SkillService
from services.report_service import ReportService
from models import OrderStatus
from filters.role import RoleFilter
from config import ADMIN_IDS

router = Router()

# ==================== FSM States ====================
class AdminStates(StatesGroup):
    waiting_client_name = State()
    waiting_phone = State()
    waiting_address = State()
    waiting_datetime = State()
    waiting_skills = State()
    waiting_type = State()
    waiting_brand = State()
    waiting_model = State()
    waiting_comment = State()
    waiting_manual_master = State()

    adding_skill_name = State()
    adding_skill_description = State()

    adding_master_name = State()
    adding_master_phone = State()
    adding_master_telegram = State()
    adding_master_skills = State()

    selecting_master_to_update = State()
    updating_master_name = State()
    updating_master_phone = State()
    updating_master_telegram = State()
    updating_master_skills = State()

    selecting_master_to_delete = State()
    confirming_delete = State()

    selecting_order_to_assign = State()
    selecting_master_to_assign = State()

    selecting_report_type = State()
    selecting_period = State()
    waiting_date_from = State()
    waiting_date_to = State()

    selecting_filter = State()
    selecting_master_for_filter = State()
    viewing_order_details = State()
    confirming_order_delete = State()

# ==================== Helper Keyboard Functions ====================
async def master_update_selection_kb(master_service: MasterService) -> InlineKeyboardMarkup:
    """Клавиатура выбора мастера для обновления"""
    builder = InlineKeyboardBuilder()
    masters = await master_service.get_all_with_skills()
    for master in masters:
        builder.row(
            InlineKeyboardButton(
                text=f"{master.name} (ID: {master.telegram_id})",
                callback_data=f"select_update_{master.id}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="masters_cancel"))
    return builder.as_markup()

async def master_delete_selection_kb(master_service: MasterService) -> InlineKeyboardMarkup:
    """Клавиатура выбора мастера для удаления"""
    builder = InlineKeyboardBuilder()
    masters = await master_service.get_all_with_skills()
    for master in masters:
        builder.row(
            InlineKeyboardButton(
                text=f"{master.name} (ID: {master.telegram_id})",
                callback_data=f"select_delete_{master.id}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="masters_cancel"))
    return builder.as_markup()

def master_update_menu_kb() -> InlineKeyboardMarkup:
    """Меню выбора поля для обновления мастера"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Имя", callback_data="update_name"),
        InlineKeyboardButton(text="📞 Телефон", callback_data="update_phone")
    )
    builder.row(
        InlineKeyboardButton(text="📱 Telegram ID", callback_data="update_telegram"),
        InlineKeyboardButton(text="🔧 Навыки", callback_data="update_skills")
    )
    builder.row(
        InlineKeyboardButton(text="💾 Сохранить", callback_data="save_update"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_update")
    )
    return builder.as_markup()

def master_delete_confirm_kb(master_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления мастера"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_delete_{master_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="masters_cancel")
    )
    return builder.as_markup()

def order_delete_confirm_kb(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления заказа"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить удаление", callback_data=f"confirm_order_delete_{order_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order_delete")
    )
    return builder.as_markup()

async def masters_filter_kb(master_service: MasterService) -> InlineKeyboardMarkup:
    """Клавиатура выбора мастера для фильтра заказов"""
    builder = InlineKeyboardBuilder()
    masters = await master_service.get_all_with_skills()
    for master in masters:
        builder.row(
            InlineKeyboardButton(
                text=f"{master.name} (ID: {master.telegram_id})",
                callback_data=f"filter_master_{master.id}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад к фильтрам", callback_data="back_to_filters"))
    return builder.as_markup()

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
    await state.clear()
    await state.set_state(AdminStates.waiting_client_name)
    await msg.answer("📝 Введите имя клиента:")

@router.message(AdminStates.waiting_client_name)
async def process_client_name(msg: Message, state: FSMContext):
    await state.update_data(client_name=msg.text.strip())
    await state.set_state(AdminStates.waiting_phone)
    await msg.answer("📞 Введите телефон (например: +998901234567):")

@router.message(AdminStates.waiting_phone)
async def process_phone(msg: Message, state: FSMContext):
    phone = msg.text.strip()
    if not validate_phone(phone):
        await msg.answer(
            "❌ Неверный формат телефона.\n"
            "Пример: +998901234567\n"
            "Попробуйте снова:"
        )
        return
    await state.update_data(phone=phone)
    await state.set_state(AdminStates.waiting_address)
    await msg.answer("📍 Введите адрес:")

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

@router.callback_query(F.data == "skills_done", AdminStates.waiting_skills)
async def skills_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("selected_skills"):
        await callback.answer("❌ Выберите хотя бы один навык!", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_type)
    await callback.message.edit_text("🔧 Введите тип техники:")
    await callback.answer()

@router.message(AdminStates.waiting_type)
async def process_type(msg: Message, state: FSMContext):
    await state.update_data(type=msg.text.strip())
    await state.set_state(AdminStates.waiting_brand)
    await msg.answer("🏷️ Введите бренд:")

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

@router.message(AdminStates.waiting_comment)
async def create_order(msg: Message, state: FSMContext, order_service: OrderService):
    """Заявка яратиш ва тайинлаш усулини танлаш"""
    data = await state.get_data()
    comment = msg.text.strip()
    
    # Заявка яратамиз
    order = await order_service.create_order(
        client_name=data["client_name"],
        phone=data["phone"],
        address=data["address"],
        datetime_obj=data["datetime"],
        type=data["type"],
        brand=data["brand"],
        model=data["model"],
        comment=comment,
        skill_ids=data.get("selected_skills", [])
    )
    
    await state.update_data(order_id=order.id)
    
    # Икки вариантли клавиатура кўрсатамиз
    kb = order_assignment_choice_kb(order.id)
    
    await msg.answer(
        f"✅ Заявка #{order.number} создана!\n\n"
        f"👤 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔧 Техника: {order.type} {order.brand} {order.model}\n"
        f"💬 Проблема: {order.comment}\n\n"
        f"Выберите способ назначения мастера:",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("auto_assign_"))
async def auto_assign_master(
    callback: CallbackQuery, 
    state: FSMContext,
    order_service: OrderService,
    master_service: MasterService,
    bot: Bot
):
    """Автоматик мастер тайинлаш"""
    order_id = int(callback.data.split("_")[2])
    
    data = await state.get_data()
    skill_ids = data.get("selected_skills", [])
    
    order = await order_service.order_repo.get(order_id)
    if not order:
        await callback.answer("❌ Заявка не найдена!", show_alert=True)
        return
    
    # Энг яхши мастерни топамиз
    best_master = await master_service.auto_assign_best_master(order.datetime, skill_ids)
    
    if best_master:
        # Мастерни тайинлаймиз (статус new, график НЕ бронируем)
        await order_service.assign_master_to_order(order.id, best_master.id)
        # НЕ бронируем график здесь (только после confirm)
        
        await callback.message.edit_text(
            f"✅ Заявка #{order.number} автоматически назначена!\n\n"
            f"👤 Мастер: {best_master.name}\n"
            f"📋 Клиент: {order.client_name}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}"
        )
        
        # Мастерга хабар юборамиз (NEW статусида)
        await bot.send_message(
            best_master.telegram_id,
            f"🆕 Новая заявка #{order.number}!\n\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📞 Телефон: {order.phone}\n"
            f"📍 Адрес: {order.address}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
            f"🔧 Техника: {order.type} {order.brand} {order.model}\n"
            f"💬 Проблема: {order.comment}",
            reply_markup=order_status_kb(order.id, OrderStatus.new)
        )
        
        await callback.message.answer("Выберите действие:", reply_markup=admin_main_kb())
        await state.clear()
    else:
        await callback.answer(
            "⚠️ Нет свободных мастеров для автоматического назначения!",
            show_alert=True
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("manual_assign_choice_"))
async def manual_assign_choice(
    callback: CallbackQuery,
    state: FSMContext,
    order_service: OrderService,
    master_service: MasterService
):
    """Қўлда мастер танлаш бошлаш"""
    order_id = int(callback.data.split("_")[3])
    
    data = await state.get_data()
    skill_ids = data.get("selected_skills", [])
    
    order = await order_service.order_repo.get(order_id)
    if not order:
        await callback.answer("❌ Заявка не найдена!", show_alert=True)
        return
    
    # Мос мастерларни топамиз
    suitable_masters = await master_service.find_suitable_masters(order.datetime, skill_ids)
    
    if suitable_masters:
        # Мос мастерлар бор
        kb = master_selection_kb(suitable_masters, order_id)
        await callback.message.edit_text(
            f"📋 Выбор мастера для заявки #{order.number}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Найдено подходящих мастеров: {len(suitable_masters)}\n"
            f"Выберите мастера:",
            reply_markup=kb
        )
    else:
        # Мос мастер йўқ - барча мастерларни кўрсатамиз
        all_masters = await master_service.get_all_masters_with_today_count()
        
        kb = master_selection_kb(all_masters, order_id, show_all=True)
        await callback.message.edit_text(
            f"⚠️ Нет подходящих мастеров для времени {order.datetime.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"📋 Заявка #{order.number}\n"
            f"Показаны все мастера (могут быть заняты):",
            reply_markup=kb
        )
    
    await state.set_state(AdminStates.waiting_manual_master)
    await callback.answer()


@router.callback_query(F.data.startswith("select_master_"), AdminStates.waiting_manual_master)
async def manual_assign_master(
    callback: CallbackQuery,
    state: FSMContext,
    order_service: OrderService,
    master_service: MasterService,
    bot: Bot
):
    """Танланган мастерни тайинлаш"""
    parts = callback.data.split("_")
    master_id = int(parts[2])
    order_id = int(parts[3])
    
    master = await master_service.master_repo.get(master_id)
    order = await order_service.order_repo.get(order_id)
    
    if not master or not order:
        await callback.answer("❌ Ошибка: Мастер или заказ не найдены!", show_alert=True)
        return
    
    try:
        # Проверить текущее назначение
        existing_assignment = await order_service.assignment_repo.get_by_order(order_id)
        old_master_id = existing_assignment.master_id if existing_assignment else None
        
        # Тайинлаймиз
        await order_service.assign_master_to_order(order_id, master_id)
        # НЕ бронируем график здесь (только после confirm мастера)
        
        # Если был старый мастер, уведомляем его об отмене
        if old_master_id and old_master_id != master_id:
            old_master = await master_service.master_repo.get(old_master_id)
            if old_master:
                await bot.send_message(
                    old_master.telegram_id,
                    f"❌ Заявка #{order.number} была переназначена администратором другому мастеру."
                )
        
        await callback.message.edit_text(
            f"✅ Мастер назначен!\n\n"
            f"👤 Мастер: {master.name}\n"
            f"📋 Заявка: #{order.number}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}"
        )
        
        # Мастерга хабар
        await bot.send_message(
            master.telegram_id,
            f"🆕 Новая заявка #{order.number}!\n\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📞 Телефон: {order.phone}\n"
            f"📍 Адрес: {order.address}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
            f"🔧 Техника: {order.type} {order.brand} {order.model}\n"
            f"💬 Проблема: {order.comment}",
            reply_markup=order_status_kb(order.id, OrderStatus.new)
        )
        
        await callback.message.answer("Выберите действие:", reply_markup=admin_main_kb())
        await state.clear()
        
    except ValueError as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_assignment_"))
async def cancel_assignment(
    callback: CallbackQuery,
    state: FSMContext,
    order_service: OrderService
):
    """Тайинлашни бекор қилиш"""
    order_id = int(callback.data.split("_")[2])
    order = await order_service.order_repo.get(order_id)
    
    if not order:
        await callback.answer("❌ Заявка не найдена!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"❌ Назначение для заявки #{order.number} отменено."
    )
    
    await callback.message.answer("Выберите действие:", reply_markup=admin_main_kb())
    await state.clear()
    await callback.answer()

# ==================== Список заявок ====================
@router.message(F.text == "📋 Заявки")
async def list_orders(msg: Message, state: FSMContext):
    await state.clear()
    kb = filters_kb()
    await msg.answer("📋 Выберите фильтр:", reply_markup=kb)

@router.callback_query(F.data.startswith("filter_master_"), AdminStates.selecting_master_for_filter)
async def filter_orders_by_master(callback: CallbackQuery, order_service: OrderService, state: FSMContext):
    master_id = int(callback.data.split("_")[2])
    
    orders = await order_service.get_orders_by_master(master_id)
    
    if not orders:
        await callback.message.edit_text(
            "📋 Нет заявок у этого мастера",
            reply_markup=filters_kb()
        )
        await state.clear()
        await callback.answer()
        return
    
    text = "📋 Заявки мастера:\n\n"
    builder = InlineKeyboardBuilder()
    
    for order in orders:
        text += (
            f"#{order.number} - {order.client_name}\n"
            f"🔧 Тип: {order.type} {order.brand} {order.model}\n"
            f"Статус: {order.status.value}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
            f"📍 Адрес: {order.address}\n\n"
        )
        # Кнопки для каждой заявки
        row_buttons = []
        if order.status == OrderStatus.new or order.status == OrderStatus.rejected:
            row_buttons.append(InlineKeyboardButton(text="Переназначить", callback_data=f"assign_order_{order.id}"))
        row_buttons.append(InlineKeyboardButton(text="Подробности", callback_data=f"view_order_{order.id}"))
        row_buttons.append(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_order_{order.id}"))
        builder.row(*row_buttons)
    
    builder.row(InlineKeyboardButton(text="🔙 Назад к фильтрам", callback_data="back_to_filters"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("filter_"))
async def filter_orders(callback: CallbackQuery, order_service: OrderService, master_service: MasterService, state: FSMContext):
    filter_type = callback.data.split("_")[1]
    
    if filter_type == "all":
        orders = await order_service.order_repo.get_all(limit=50)
        title = "Все заявки"
    elif filter_type == "new":
        orders = await order_service.get_orders_by_filter(status=OrderStatus.new)
        title = "Новые заявки"
    elif filter_type == "confirmed":
        orders = await order_service.get_orders_by_filter(status=OrderStatus.confirmed)
        title = "Подтвержденные заявки"
    elif filter_type == "work":
        orders = await order_service.get_orders_by_filter(status=OrderStatus.in_progress)
        title = "В работе"
    elif filter_type == "arrived":
        orders = await order_service.get_orders_by_filter(status=OrderStatus.arrived)
        title = "Мастер на месте"
    elif filter_type == "done":
        orders = await order_service.get_orders_by_filter(status=OrderStatus.completed)
        title = "Завершенные"
    elif filter_type == "rejected":
        orders = await order_service.get_orders_by_filter(status=OrderStatus.rejected)
        title = "Отклоненные"
    elif filter_type == "today":
        from datetime import date
        orders = await order_service.order_repo.get_by_date_range(
            date.today(), 
            date.today()
        )
        title = "Заявки на сегодня"
    elif filter_type == "bymaster":
        print("Filter by master selected")
        # Переходим к выбору мастера для фильтра
        kb = await masters_filter_kb(master_service)
        await callback.message.edit_text("Выберите мастера для просмотра его заявок:", reply_markup=kb)
        await state.set_state(AdminStates.selecting_master_for_filter)
        await callback.answer()
        return
    else:
        orders = []
        title = "Неизвестный фильтр"
    
    if not orders:
        await callback.message.edit_text(
            f"📋 Нет заявок ({title.lower()})",
            reply_markup=filters_kb()
        )
        await callback.answer()
        return
    
    text = f"📋 {title}:\n\n"
    builder = InlineKeyboardBuilder()
    
    for order in orders:
        assignment = await order_service.assignment_repo.get_by_order(order.id)
        assigned_master = assignment.master.name if assignment and assignment.master else "Не назначен"
        text += (
            f"#{order.number} - {order.client_name}\n"
            f"🔧 Тип: {order.type} {order.brand} {order.model}\n"
            f"👤 Мастер: {assigned_master}\n"
            f"Статус: {order.status.value}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
            f"📍 Адрес: {order.address}\n\n"
        )
        # Кнопки для каждой заявки
        row_buttons = []
        if order.status == OrderStatus.new or order.status == OrderStatus.rejected:
            row_buttons.append(InlineKeyboardButton(text="Назначить/Переназначить", callback_data=f"assign_order_{order.id}"))
        row_buttons.append(InlineKeyboardButton(text="Подробности", callback_data=f"view_order_{order.id}"))
        row_buttons.append(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_order_{order.id}"))
        builder.row(*row_buttons)
    
    builder.row(InlineKeyboardButton(text="🔙 Назад к фильтрам", callback_data="back_to_filters"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()



@router.callback_query(F.data.startswith("view_order_"))
async def view_order_details(callback: CallbackQuery, order_service: OrderService, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    order = await order_service.order_repo.get_with_skills(order_id)
    if not order:
        await callback.answer("❌ Заявка не найдена!", show_alert=True)
        return
    
    assignment = await order_service.assignment_repo.get_by_order(order_id)
    master_name = assignment.master.name if assignment else "Не назначен"
    
    skills = ", ".join([s.name for s in order.required_skills]) if order.required_skills else "Нет"
    
    text = (
        f"📋 Подробности заявки #{order.number}\n\n"
        f"👤 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔧 Техника: {order.type} {order.brand} {order.model}\n"
        f"💬 Проблема: {order.comment}\n"
        f"👤 Мастер: {master_name}\n"
        f"📊 Статус: {order.status.value}\n"
        f"🛠 Навыки: {skills}\n"
    )
    
    if order.status == OrderStatus.completed:
        text += (
            f"\n📝 Работы: {order.work_description or 'Не указано'}\n"
            f"💰 Сумма: {order.work_amount:.2f} ₽\n"
            f"💵 Расходы: {order.expenses:.2f} ₽\n"
            f"💎 Прибыль: {order.profit:.2f} ₽\n"
            f"📸 Фото: {len(order.work_photos or [])}"
        )
    
    builder = InlineKeyboardBuilder()
    if order.status in [OrderStatus.new, OrderStatus.rejected]:
        builder.row(InlineKeyboardButton(text="Назначить/Переназначить", callback_data=f"assign_order_{order.id}"))
    builder.row(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_order_{order.id}"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_filters"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("delete_order_"))
async def confirm_order_delete(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    order_id = int(callback.data.split("_")[2])
    order = await order_service.order_repo.get(order_id)
    if not order:
        await callback.answer("❌ Заявка не найдена!", show_alert=True)
        return
    
    await state.update_data(delete_order_id=order_id)
    await state.set_state(AdminStates.confirming_order_delete)
    
    kb = order_delete_confirm_kb(order_id)
    await callback.message.edit_text(
        f"🗑 Вы уверены, что хотите удалить заявку #{order.number}?\n"
        f"Это действие необратимо!",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_order_delete_"), AdminStates.confirming_order_delete)
async def perform_order_delete(callback: CallbackQuery, state: FSMContext, order_service: OrderService, master_service: MasterService, bot: Bot):
    data = await state.get_data()
    order_id = data["delete_order_id"]
    
    order = await order_service.order_repo.get(order_id)
    if not order:
        await callback.answer("❌ Заявка не найдена!", show_alert=True)
        await state.clear()
        return
    
    # Получаем назначение
    assignment = await order_service.assignment_repo.get_by_order(order_id)
    master_id = assignment.master_id if assignment else None
    
    # Удаляем заказ (удаляет и назначение)
    success = await order_service.delete_order(order_id)
    
    if success:
        # Если был мастер и статус был confirmed или выше, освобождаем график
        if master_id and order.status in [OrderStatus.confirmed, OrderStatus.in_progress, OrderStatus.arrived]:
            await master_service.update_schedule(master_id, order.datetime, "отдан другому мвстеру")
        
        # Уведомляем мастера, если был назначен
        if master_id:
            master = await master_service.master_repo.get(master_id)
            if master:
                await bot.send_message(
                    master.telegram_id,
                    f"❌ Заявка #{order.number} была отменена администратором."
                )
        
        await callback.message.edit_text(f"✅ Заявка #{order.number} удалена!")
    else:
        await callback.message.edit_text(f"❌ Не удалось удалить заявку #{order.number}!")

    await callback.message.answer("Выберите действие:", reply_markup=admin_main_kb())
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_order_delete", AdminStates.confirming_order_delete)
async def cancel_order_delete(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Удаление отменено.", reply_markup=filters_kb())
    await callback.answer()

@router.callback_query(F.data.startswith("assign_order_"))
async def start_assign_existing_order(callback: CallbackQuery, state: FSMContext, order_service: OrderService, master_service: MasterService):
    order_id = int(callback.data.split("_")[2])
    order = await order_service.order_repo.get_with_skills(order_id)
    if not order:
        await callback.answer("❌ Заявка не найдена!", show_alert=True)
        return
    
    await state.update_data(order_id=order_id)
    await state.set_state(AdminStates.selecting_master_to_assign)
    
    # Используем новый метод вместо find_suitable_masters
    skill_ids = [s.id for s in order.required_skills] if order.required_skills else []
    masters = await master_service.get_masters_for_assignment(order.datetime, skill_ids)
    
    if not masters:
        await callback.message.edit_text(
            f"📋 Назначение мастера для заявки #{order.number}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"⚠️ Мастера не найдены. Создайте новых мастеров.",
            reply_markup=None
        )
        await callback.answer()
        return
    
    kb = master_selection_kb(masters, order_id)  # Убедитесь, что kb поддерживает новые данные
    await callback.message.edit_text(
        f"📋 Назначение/Переназначение мастера для заявки #{order.number}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"Выберите мастера:",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data.startswith("select_master_"))
async def assign_selected_master(callback: CallbackQuery, state: FSMContext, order_service: OrderService, master_service: MasterService, bot: Bot):
    _, _, order_id_str, master_id_str = callback.data.split("_")
    order_id = int(order_id_str)
    master_id = int(master_id_str)
    
    master = await master_service.master_repo.get(master_id)
    if not master:
        await callback.message.edit_text(
            f"❌ Мастер с ID {master_id} не найден. Возможно, он был удален.\n"
            f"Выберите другого мастера.",
            reply_markup=None
        )
        await callback.answer(show_alert=True)
        return
    
    # Назначаем мастера (без изменения статуса на confirmed!)
    order = await order_service.assign_master_to_order(order_id, master_id)
    
    # Уведомляем мастера с OrderStatus.new
    await bot.send_message(
        master.telegram_id,
        f"🆕 Новая заявка #{order.number} назначена вам!\n\n"
        f"👤 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔧 Техника: {order.type} {order.brand} {order.model}\n"
        f"💬 Проблема: {order.comment}\n\n"
        f"Принять или отказаться?",
        reply_markup=order_status_kb(order.id, OrderStatus.new)
    )
    
    await callback.message.edit_text(
        f"✅ Мастер {master.name} назначен на заявку #{order.number}. Ожидает принятия.",
        reply_markup=None
    )
    await state.clear()
    await callback.answer()

# ==================== Мастера и навыки ====================
@router.message(F.text == "👥 Мастера и навыки")
async def masters_menu(msg: Message, state: FSMContext):
    await state.clear()
    kb = masters_menu_kb()
    await msg.answer("👥 Управление мастерами и навыками:", reply_markup=kb)

@router.callback_query(F.data == "list_skills")
async def list_skills(callback: CallbackQuery, skill_service: SkillService):
    skills = await skill_service.get_all_skills()
    if not skills:
        text = "📚 Навыков пока нет. Добавьте первый!"
    else:
        text = "📚 Список навыков:\n\n"
        for skill in skills:
            text += f"• {skill.name}\n"
            if skill.description:
                text += f"  {skill.description}\n"
    await callback.message.edit_text(text, reply_markup=masters_menu_kb())
    await callback.answer()

@router.callback_query(F.data == "add_skill")
async def add_skill_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AdminStates.adding_skill_name)
    await callback.message.edit_text("📚 Введите название навыка:")
    await callback.answer()

@router.message(AdminStates.adding_skill_name)
async def process_skill_name(msg: Message, state: FSMContext, skill_service: SkillService):
    skill_name = msg.text.strip()
    existing_skill = await skill_service.get_skill_by_name(skill_name)
    if existing_skill:
        await msg.answer("❌ Навык с таким названием уже существует. Попробуйте другое название:")
        return
    await state.update_data(skill_name=skill_name)
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
    masters = await master_service.get_all_with_skills()
    if not masters:
        text = "👥 Мастеров пока нет. Добавьте первого!"
    else:
        text = "👥 Список мастеров:\n\n"
        for master in masters:
            skills_text = ", ".join([s.name for s in master.skills]) if master.skills else "Нет навыков"
            status = "🟢 Онлайн" if getattr(master, 'is_online', False) else "⚪ Оффлайн"
            text += (
                f"• {master.name} {status}\n"
                f"  ID: {master.telegram_id}\n"
                f"  Телефон: {master.phone or 'Не указан'}\n"
                f"  Навыки: {skills_text}\n\n"
            )
    await callback.message.edit_text(text, reply_markup=masters_menu_kb())
    await callback.answer()

@router.callback_query(F.data == "add_master")
async def add_master_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
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
    if phone and not validate_phone(phone):
        await msg.answer("❌ Неверный формат телефона. Попробуйте снова:")
        return
    await state.update_data(master_phone=phone)
    await state.set_state(AdminStates.adding_master_telegram)
    await msg.answer("📱 Введите Telegram ID мастера (число):")

@router.message(AdminStates.adding_master_telegram)
async def process_master_telegram(msg: Message, state: FSMContext, master_service: MasterService):
    try:
        telegram_id = int(msg.text.strip())
        existing_master = await master_service.master_repo.get_by_telegram_id(telegram_id)
        if existing_master:
            await msg.answer("❌ Этот Telegram ID уже используется другим мастером!")
            return
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
    data = await state.get_data()
    if not data.get("selected_skills"):
        await callback.answer("❌ Выберите хотя бы один навык!", show_alert=True)
        return
    master_data = await master_service.create_master(
        name=data["master_name"],
        telegram_id=data["master_telegram_id"],
        phone=data.get("master_phone"),
        skill_ids=data.get("selected_skills", [])
    )
    skills_text = ", ".join([s["name"] for s in master_data["skills"]]) if master_data["skills"] else "без навыков"
    await callback.message.edit_text(
        f"✅ Мастер {master_data['name']} добавлен!\n"
        f"Навыки: {skills_text}"
    )
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=admin_main_kb()
    )
    await state.clear()
    await callback.answer()

# ==================== Обновление мастера ====================
@router.callback_query(F.data == "update_master")
async def update_master_start(callback: CallbackQuery, state: FSMContext, master_service: MasterService):
    await state.clear()
    await state.set_state(AdminStates.selecting_master_to_update)
    kb = await master_update_selection_kb(master_service)
    await callback.message.edit_text(
        "👤 Выберите мастера для обновления:",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data.startswith("select_update_"), AdminStates.selecting_master_to_update)
async def select_master_to_update(callback: CallbackQuery, state: FSMContext, master_service: MasterService):
    master_id = int(callback.data.split("_")[2])
    master = await master_service.master_repo.get_with_skills(master_id)
    if not master:
        await callback.answer("❌ Мастер не найден!", show_alert=True)
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
        f"Что обновить?"
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
    await msg.answer("✅ Имя обновлено.", reply_markup=master_update_menu_kb())
    await msg.delete()

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
    await msg.answer("✅ Телефон обновлен.", reply_markup=master_update_menu_kb())
    await msg.delete()

@router.callback_query(F.data == "update_telegram", AdminStates.selecting_master_to_update)
async def update_master_telegram_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.updating_master_telegram)
    await callback.message.edit_text("📱 Введите новый Telegram ID (число):")
    await callback.answer()

@router.message(AdminStates.updating_master_telegram)
async def process_update_master_telegram(msg: Message, state: FSMContext, master_service: MasterService):
    try:
        telegram_id = int(msg.text.strip())
        existing_master = await master_service.master_repo.get_by_telegram_id(telegram_id)
        data = await state.get_data()
        if existing_master and existing_master.id != data["master_id"]:
            await msg.answer("❌ Этот Telegram ID уже используется другим мастером!")
            return
        await state.update_data(new_telegram=telegram_id)
        await state.set_state(AdminStates.selecting_master_to_update)
        await msg.answer("✅ Telegram ID обновлен.", reply_markup=master_update_menu_kb())
        await msg.delete()
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
    if not skill_ids:
        await callback.answer("❌ Выберите хотя бы один навык!", show_alert=True)
        return
    if master_id:
        await master_service.update_skills(master_id, skill_ids)
    await state.set_state(AdminStates.selecting_master_to_update)
    await callback.message.edit_text("✅ Навыки обновлены.", reply_markup=master_update_menu_kb())
    await callback.answer()

@router.callback_query(F.data == "save_update", AdminStates.selecting_master_to_update)
async def save_master_update(callback: CallbackQuery, state: FSMContext, master_service: MasterService):
    data = await state.get_data()
    master_id = data["master_id"]
    name = data.get("new_name", data.get("current_name"))
    phone = data.get("new_phone", data.get("current_phone"))
    telegram_id = data.get("new_telegram", data.get("current_telegram"))
    skill_ids = data.get("selected_skills", [])
    try:
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
    except ValueError as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
    await callback.answer()

@router.callback_query(F.data == "cancel_update", AdminStates.selecting_master_to_update)
async def cancel_master_update(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Обновление мастера отменено.")
    await callback.message.answer("Выберите действие:", reply_markup=admin_main_kb())
    await state.clear()
    await callback.answer()

# ==================== Удаление мастера ====================
@router.callback_query(F.data == "delete_master")
async def delete_master_start(callback: CallbackQuery, state: FSMContext, master_service: MasterService):
    await state.clear()
    await state.set_state(AdminStates.selecting_master_to_delete)
    kb = await master_delete_selection_kb(master_service)
    await callback.message.edit_text(
        "🗑️ Выберите мастера для удаления:",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data.startswith("select_delete_"), AdminStates.selecting_master_to_delete)
async def select_master_to_delete(callback: CallbackQuery, state: FSMContext, master_service: MasterService):
    master_id = int(callback.data.split("_")[2])
    master = await master_service.master_repo.get(master_id)
    if not master:
        await callback.answer("❌ Мастер не найден!", show_alert=True)
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
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.", reply_markup=masters_menu_kb())
    await callback.answer()

# ==================== Отчеты ====================
@router.message(F.text == "📊 Отчеты")
async def reports_menu(msg: Message, state: FSMContext):
    await state.clear()
    kb = reports_menu_kb()
    await msg.answer("📊 Выберите тип отчета:", reply_markup=kb)

@router.callback_query(F.data == "report_financial")
async def start_financial_report(callback: CallbackQuery, state: FSMContext):
    await state.update_data(report_type="financial")
    await state.set_state(AdminStates.selecting_period)
    kb = period_selection_kb()
    await callback.message.edit_text("💰 Финансовый отчет. Выберите период:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "report_masters")
async def start_masters_report(callback: CallbackQuery, state: FSMContext):
    await state.update_data(report_type="masters")
    await state.set_state(AdminStates.selecting_period)
    kb = period_selection_kb()
    await callback.message.edit_text("👥 Отчет по мастерам. Выберите период:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "report_orders")
async def start_orders_report(callback: CallbackQuery, state: FSMContext):
    await state.update_data(report_type="orders")
    await state.set_state(AdminStates.selecting_period)
    kb = period_selection_kb()
    await callback.message.edit_text("📋 Отчет по заказам. Выберите период:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "export_all")
async def export_all_data(callback: CallbackQuery, state: FSMContext, report_service: ReportService, bot: Bot):
    await state.clear()
    try:
        await callback.message.edit_text("⏳ Генерация отчета... Пожалуйста, подождите.")
        export_data = await report_service.get_all_export_data()
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
                "📋 Заказы - все заказы со статусами\n"
                "👥 Мастера - мастера с навыками и итогами"
            )
        )
        await callback.message.edit_text("✅ Все данные экспортированы в Excel!", reply_markup=admin_main_kb())
        await callback.answer()
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data.startswith("period_"), AdminStates.selecting_period)
async def select_period(callback: CallbackQuery, state: FSMContext, report_service: ReportService, bot: Bot):
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
        await callback.answer("❌ Неверный период!", show_alert=True)
        return
    
    await state.update_data(date_from=date_from, date_to=date_to, period_text=period_text)
    
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
        df = await report_service.get_financial_export_data(date_from, date_to)
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        filename = f"financial_report_{date.today().strftime('%Y%m%d')}.xlsx"
        document = BufferedInputFile(file=output.getvalue(), filename=filename)
        await bot.send_document(
            callback.from_user.id,
            document,
            caption=f"💰 Финансовый отчет ({period_text})"
        )
    elif report_type == "masters":
        report = await report_service.get_masters_report(date_from, date_to)
        text = f"👥 Отчет по мастерам ({period_text}):\n\n"
        for master_name, stats in report.items():
            text += f"{master_name}: {stats['orders_count']} заказов, прибыль {stats['total_profit']:.2f} ₽\n"
        df = await report_service.get_masters_export_data(date_from, date_to)
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        filename = f"masters_report_{date.today().strftime('%Y%m%d')}.xlsx"
        document = BufferedInputFile(file=output.getvalue(), filename=filename)
        await bot.send_document(
            callback.from_user.id,
            document,
            caption=f"👥 Отчет по мастерам ({period_text})"
        )
    elif report_type == "orders":
        report = await report_service.get_orders_report(date_from, date_to)
        text = f"📋 Отчет по заказам ({period_text}):\n\n"
        for order in report:
            text += f"#{order.number}: {getattr(order, 'profit', 0):.2f} ₽\n"
        df = await report_service.get_orders_export_data(date_from, date_to)
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        filename = f"orders_report_{date.today().strftime('%Y%m%d')}.xlsx"
        document = BufferedInputFile(file=output.getvalue(), filename=filename)
        await bot.send_document(
            callback.from_user.id,
            document,
            caption=f"📋 Отчет по заказам ({period_text})"
        )
    else:
        text = "❌ Неизвестный тип отчета!"
    
    await callback.message.edit_text(text, reply_markup=reports_menu_kb())
    await callback.message.answer("Выберите действие:", reply_markup=admin_main_kb())
    await state.clear()
    await callback.answer()

@router.message(AdminStates.waiting_date_from)
async def process_date_from(msg: Message, state: FSMContext):
    try:
        date_from = datetime.strptime(msg.text.strip(), "%Y-%m-%d").date()
        if date_from > date.today():
            await msg.answer("❌ Дата начала не может быть в будущем. Попробуйте снова:")
            return
        await state.update_data(date_from=date_from)
        await state.set_state(AdminStates.waiting_date_to)
        await msg.answer("📅 Введите дату окончания (YYYY-MM-DD):")
    except ValueError:
        await msg.answer("❌ Неверный формат. Пример: 2025-10-01")

@router.message(AdminStates.waiting_date_to)
async def process_date_to_and_generate(msg: Message, state: FSMContext, report_service: ReportService, bot: Bot):
    try:
        date_to = datetime.strptime(msg.text.strip(), "%Y-%m-%d").date()
        data = await state.get_data()
        date_from = data["date_from"]
        if date_to < date_from:
            await msg.answer("❌ Дата окончания не может быть раньше даты начала. Попробуйте снова:")
            return
        report_type = data["report_type"]
        period_text = f"{date_from.strftime('%Y-%m-%d')} - {date_to.strftime('%Y-%m-%d')}"
        
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
            df = await report_service.get_financial_export_data(date_from, date_to)
            output = io.BytesIO()
            df.to_excel(output, index=False, engine='openpyxl')
            output.seek(0)
            filename = f"financial_report_{date.today().strftime('%Y%m%d')}.xlsx"
            document = BufferedInputFile(file=output.getvalue(), filename=filename)
            await bot.send_document(
                msg.from_user.id,
                document,
                caption=f"💰 Финансовый отчет ({period_text})"
            )
        elif report_type == "masters":
            report = await report_service.get_masters_report(date_from, date_to)
            text = f"👥 Отчет по мастерам ({period_text}):\n\n"
            for master_name, stats in report.items():
                text += f"{master_name}: {stats['orders_count']} заказов, прибыль {stats['total_profit']:.2f} ₽\n"
            df = await report_service.get_masters_export_data(date_from, date_to)
            output = io.BytesIO()
            df.to_excel(output, index=False, engine='openpyxl')
            output.seek(0)
            filename = f"masters_report_{date.today().strftime('%Y%m%d')}.xlsx"
            document = BufferedInputFile(file=output.getvalue(), filename=filename)
            await bot.send_document(
                msg.from_user.id,
                document,
                caption=f"👥 Отчет по мастерам ({period_text})"
            )
        elif report_type == "orders":
            report = await report_service.get_orders_report(date_from, date_to)
            text = f"📋 Отчет по заказам ({period_text}):\n\n"
            for order in report:
                text += f"#{order.number}: {getattr(order, 'profit', 0):.2f} ₽\n"
            df = await report_service.get_orders_export_data(date_from, date_to)
            output = io.BytesIO()
            df.to_excel(output, index=False, engine='openpyxl')
            output.seek(0)
            filename = f"orders_report_{date.today().strftime('%Y%m%d')}.xlsx"
            document = BufferedInputFile(file=output.getvalue(), filename=filename)
            await bot.send_document(
                msg.from_user.id,
                document,
                caption=f"📋 Отчет по заказам ({period_text})"
            )
        else:
            text = "❌ Неизвестный тип отчета!"
        
        await msg.answer(text, reply_markup=admin_main_kb())
        await state.clear()
    except ValueError:
        await msg.answer("❌ Неверный формат. Пример: 2025-10-15")

# ==================== Общие обработчики ====================
@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "👋 Добро пожаловать, админ!\n"
        "Выберите действие:",
        reply_markup=admin_main_kb()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_reports")
async def back_to_reports(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "📊 Выберите тип отчета:",
        reply_markup=reports_menu_kb()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_filters")
async def back_to_filters(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "📋 Выберите фильтр:",
        reply_markup=filters_kb()
    )
    await callback.answer()