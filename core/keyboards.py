from typing import List
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, timedelta

from database.engine import get_session
from services.services import SkillService, MasterService


# ==================== ADMIN KEYBOARDS ====================
def admin_main_kb() -> ReplyKeyboardMarkup:
    """Главное меню админа"""
    kb = [
        [KeyboardButton(text="🆕 Новая заявка")],
        [KeyboardButton(text="📋 Заявки"), KeyboardButton(text="👥 Мастера и навыки")],
        [KeyboardButton(text="📊 Отчеты"), KeyboardButton(text="⚙️ Настройки")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def filters_kb() -> InlineKeyboardMarkup:
    """Фильтры для списка заявок"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Все", callback_data="filter_all"),
        InlineKeyboardButton(text="🆕 Новые", callback_data="filter_new")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ В работе", callback_data="filter_work"),
        InlineKeyboardButton(text="✅ Готовые", callback_data="filter_done")
    )
    return builder.as_markup()


def masters_menu_kb() -> InlineKeyboardMarkup:
    """Меню управления мастерами"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📚 Навыки", callback_data="list_skills"),
        InlineKeyboardButton(text="👥 Мастера", callback_data="list_masters")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить навык", callback_data="add_skill"),
        InlineKeyboardButton(text="➕ Добавить мастера", callback_data="add_master")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить мастера", callback_data="update_master"),
        InlineKeyboardButton(text="🗑️ Удалить мастера", callback_data="delete_master")
    )
    return builder.as_markup()


async def skills_checkbox_kb(selected_ids: List[int] = None) -> InlineKeyboardMarkup:
    """
    Чекбоксы навыков (универсальная).
    Используется и при создании заявки, и при добавлении мастера.
    """
    if selected_ids is None:
        selected_ids = []
    
    builder = InlineKeyboardBuilder()
    
    # Получаем все навыки
    async with get_session() as session:
        skill_service = SkillService(session)
        skills = await skill_service.get_all_skills()
    
    for skill in skills:
        checkbox = "✅" if skill.id in selected_ids else "⬜"
        builder.row(
            InlineKeyboardButton(
                text=f"{checkbox} {skill.name}",
                callback_data=f"skill_toggle_{skill.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="💾 Готово", callback_data="skills_done")
    )
    
    return builder.as_markup()


async def master_update_selection_kb() -> InlineKeyboardMarkup:
    """Выбор мастера для обновления"""
    builder = InlineKeyboardBuilder()
    
    async with get_session() as session:
        from services.services import MasterService
        master_service = MasterService(session)
        masters = await master_service.get_all_with_skills()
    
    if not masters:
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    for master in masters:
        builder.row(
            InlineKeyboardButton(
                text=f"{master.name} (ID: {master.telegram_id})",
                callback_data=f"select_update_{master.id}"
            )
        )
    
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="masters_cancel"))
    return builder.as_markup()


async def master_delete_selection_kb() -> InlineKeyboardMarkup:
    """Выбор мастера для удаления"""
    builder = InlineKeyboardBuilder()
    
    async with get_session() as session:
        from services.services import MasterService
        master_service = MasterService(session)
        masters = await master_service.get_all_with_skills()
    
    if not masters:
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    for master in masters:
        builder.row(
            InlineKeyboardButton(
                text=f"{master.name} (ID: {master.telegram_id})",
                callback_data=f"select_delete_{master.id}"
            )
        )
    
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="masters_cancel"))
    return builder.as_markup()


def master_update_menu_kb() -> InlineKeyboardMarkup:
    """Меню выбора, что обновить у мастера"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📝 Имя", callback_data="update_name"))
    builder.row(InlineKeyboardButton(text="📞 Телефон", callback_data="update_phone"))
    builder.row(InlineKeyboardButton(text="📱 Telegram ID", callback_data="update_telegram"))
    builder.row(InlineKeyboardButton(text="🔧 Навыки", callback_data="update_skills"))
    builder.row(InlineKeyboardButton(text="✅ Сохранить", callback_data="save_update"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="masters_cancel"))
    return builder.as_markup()


def master_delete_confirm_kb(master_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления мастера"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"confirm_delete_{master_id}"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="masters_cancel"))
    return builder.as_markup()


async def manual_master_selection_kb(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для ручного выбора мастера (НОВОЕ)"""
    builder = InlineKeyboardBuilder()
    
    async with get_session() as session:
        from services.services import MasterService
        master_service = MasterService(session)
        masters = await master_service.get_all_with_skills()
    
    if not masters:
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    for master in masters:
        builder.row(
            InlineKeyboardButton(
                text=f"{master.name} (ID: {master.telegram_id})",
                callback_data=f"assign_manual_{master.id}_{order_id}"
            )
        )
    
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_manual_{order_id}"))
    return builder.as_markup()


# ==================== REPORTS KEYBOARDS ====================
def reports_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню отчетов"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💰 Финансовый", callback_data="report_financial"))
    builder.row(InlineKeyboardButton(text="👥 Мастера", callback_data="report_masters"))
    builder.row(InlineKeyboardButton(text="📋 Заказы", callback_data="report_orders"))
    builder.row(InlineKeyboardButton(text="📤 Экспорт всех данных", callback_data="export_all"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main"))
    return builder.as_markup()


def period_selection_kb() -> InlineKeyboardMarkup:
    """Выбор периода"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Сегодня", callback_data="period_today"),
        InlineKeyboardButton(text="📆 Неделя", callback_data="period_week")
    )
    builder.row(
        InlineKeyboardButton(text="📅 Месяц", callback_data="period_month"),
        InlineKeyboardButton(text="📊 Весь период", callback_data="period_all")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Пользовательский период", callback_data="period_custom")
    )
    builder.row(InlineKeyboardButton(text="🔙 К отчетам", callback_data="back_to_reports"))
    return builder.as_markup()


# ==================== MASTER KEYBOARDS ====================
def master_main_kb() -> ReplyKeyboardMarkup:
    """Главное меню мастера"""
    kb = [
        [KeyboardButton(text="📋 Мои заявки")],
        [KeyboardButton(text="📅 График"), KeyboardButton(text="💬 Админу")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def order_status_kb(order_id: int) -> InlineKeyboardMarkup:
    """Кнопки управления статусом заявки для мастера"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Беру!", callback_data=f"confirm_{order_id}"),
        InlineKeyboardButton(text="🚗 Выехал", callback_data=f"depart_{order_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Прибыл", callback_data=f"arrive_{order_id}"),
        InlineKeyboardButton(text="🛠️ Завершить", callback_data=f"complete_{order_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отказ", callback_data=f"reject_{order_id}")
    )
    return builder.as_markup()


def master_orders_kb(has_active: bool = False) -> InlineKeyboardMarkup:
    """Фильтры для списка заявок мастера"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Активные", callback_data="master_orders_active"),
        InlineKeyboardButton(text="✅ Архив", callback_data="master_orders_archive")
    )
    return builder.as_markup()