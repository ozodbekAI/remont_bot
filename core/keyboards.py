from typing import List, Dict
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from models import OrderStatus


# ==================== ADMIN KEYBOARDS ====================
def admin_main_kb() -> ReplyKeyboardMarkup:
    """Главное меню админа"""
    kb = [
        [KeyboardButton(text="🆕 Новая заявка")],
        [KeyboardButton(text="📋 Заявки"), KeyboardButton(text="👥 Мастера и навыки")],
        [KeyboardButton(text="📊 Отчеты"), KeyboardButton(text="⚙️ Настройки")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def order_assignment_choice_kb(order_id: int) -> InlineKeyboardMarkup:
    """
    Заявка яратилганда тайинлаш усулини танлаш
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🤖 Автоматически назначить",
            callback_data=f"auto_assign_{order_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="👤 Выбрать мастера вручную",
            callback_data=f"manual_assign_choice_{order_id}"
        )
    )
    
    return builder.as_markup()


def master_selection_kb(
    masters_info: List[Dict], 
    order_id: int,
    show_all: bool = False
) -> InlineKeyboardMarkup:
    """
    Мастер танлаш клавиатураси
    
    masters_info: List[{"master": Master, "today_orders": int, "skills": str}]
    order_id: Заявка ID
    show_all: Агар True бўлса, барча мастерлар кўрсатилади (мос бўлмаса ҳам)
    """
    builder = InlineKeyboardBuilder()
    
    for info in masters_info:
        print( info )  # Лог для текшириш
        master = info["master"]
        today_orders = info["today_orders"]
        skills = info["skills"]
        
        # Тугма матни
        if show_all:
            # Барча мастерлар кўрсатилаётган бўлса
            button_text = (
                f"👤 {master.name}\n"
                f"📦: {today_orders} | 🔧 {skills}"
            )
        else:
            # Фақат мос мастерлар
            button_text = (
                f"👤 {master.name}\n"
                f"📦: {today_orders} | 🔧 {skills}"
            )
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"select_master_{master.id}_{order_id}"
            )
        )
    
    # Бекор қилиш тугмаси
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"cancel_assignment_{order_id}"
        )
    )
    
    return builder.as_markup()

def master_selection_kbb(masters: List[Dict], order_id: int):
    """
    Создать клавиатуру для выбора мастера.
    masters: список словарей с данными мастеров (из get_masters_for_assignment).
    order_id: ID заказа для callback_data.
    """
    kb = InlineKeyboardBuilder()
    
    for m in masters:
        master = m["master"]
        availability = "🟢 Свободен" if m["is_available"] else "🔴 Занят"
        orders = f"📋 Заказов сегодня: {m['today_orders']}"
        skills_match = (
            f"✅ Навыки: {m['skills']}\n"
            f"Совпадение: {m['skills_match_percent']:.0f}% ({len(m['matching_skills'])}/{len(m['matching_skills']) + len(m['missing_skills'])})"
            if m['matching_skills'] or m['missing_skills']
            else f"✅ Навыки: {m['skills']}"
        )
        
        button_text = f"{master.name}\n{availability}\n{orders}\n{skills_match}"
        kb.button(
            text=button_text,
            callback_data=f"select_master_{order_id}_{master.id}"
        )
    
    kb.button(text="🔙 Назад", callback_data="back_to_orders")
    kb.adjust(1)  # Один мастер на строку
    return kb.as_markup()

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
    """Чекбоксы навыков"""
    if selected_ids is None:
        selected_ids = []
    
    builder = InlineKeyboardBuilder()
    
    from database.engine import get_session
    from services.skill_service import SkillService
    
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


def order_status_kb(order_id: int, status: OrderStatus) -> InlineKeyboardMarkup:
    """Кнопки управления статусом заявки для мастера"""
    builder = InlineKeyboardBuilder()
    
    if status == OrderStatus.new:
        builder.row(
            InlineKeyboardButton(text="✅ Беру!", callback_data=f"confirm_{order_id}"),
            InlineKeyboardButton(text="❌ Отказ", callback_data=f"reject_{order_id}")
        )
    elif status == OrderStatus.confirmed:
        builder.row(
            InlineKeyboardButton(text="🚗 Выехал", callback_data=f"depart_{order_id}"),
            InlineKeyboardButton(text="❌ Отказ", callback_data=f"reject_{order_id}")
        )
    elif status == OrderStatus.in_progress:
        builder.row(
            InlineKeyboardButton(text="🏠 Прибыл", callback_data=f"arrive_{order_id}"),
            InlineKeyboardButton(text="❌ Отказ", callback_data=f"reject_{order_id}")
        )
    elif status == OrderStatus.arrived:
        builder.row(
            InlineKeyboardButton(text="🛠️ Завершить", callback_data=f"complete_{order_id}"),
            InlineKeyboardButton(text="❌ Отказ", callback_data=f"reject_{order_id}")
        )
    
    return builder.as_markup()



def filters_kb() -> InlineKeyboardMarkup:
    """Фильтры для списка заявок"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🆕 Новые", callback_data="filter_new"),
        InlineKeyboardButton(text="✅ Подтвержденные", callback_data="filter_confirmed")
    )
    builder.row(
        InlineKeyboardButton(text="🚗 В пути", callback_data="filter_work"),
        InlineKeyboardButton(text="🏠 На месте", callback_data="filter_arrived")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Завершенные", callback_data="filter_done"),
        InlineKeyboardButton(text="❌ Отклоненные", callback_data="filter_rejected")
    )
    builder.row(
        InlineKeyboardButton(text="📅 Сегодня", callback_data="filter_today"),
        InlineKeyboardButton(text="👤 По мастеру", callback_data="filter_bymaster")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Все", callback_data="filter_all")
    )
    return builder.as_markup()

def master_orders_kb(has_active: bool = False) -> InlineKeyboardMarkup:
    """Фильтры для списка заявок мастера"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛠 Текущие работы", callback_data="master_current_orders"),
        InlineKeyboardButton(text="📅 Работы на сегодня", callback_data="master_today_orders")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Все работы", callback_data="master_all_orders"),
        InlineKeyboardButton(text="✅ Архив", callback_data="master_orders_archive")
    )
    return builder.as_markup()