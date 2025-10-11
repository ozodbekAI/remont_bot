from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

router = Router()


@router.message(Command("cancel"))
async def cancel_handler(msg: Message, state: FSMContext):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state is None:
        await msg.answer("Нечего отменять.")
        return
    
    await state.clear()
    await msg.answer("✅ Действие отменено.\nИспользуйте /start для возврата в меню.")


@router.message(Command("help"))
async def help_handler(msg: Message, role: str = None):
    """Помощь"""
    if role == "admin":
        text = (
            "📚 Справка для администратора:\n\n"
            "🆕 Новая заявка - создать новую заявку\n"
            "📋 Заявки - просмотр и фильтрация заявок\n"
            "👥 Мастера и навыки - управление персоналом\n"
            "📊 Отчеты - статистика и аналитика\n\n"
            "Команды:\n"
            "/cancel - отменить текущее действие\n"
            "/start - главное меню"
        )
    elif role == "master":
        text = (
            "📚 Справка для мастера:\n\n"
            "📋 Мои заявки - список ваших заявок\n"
            "📅 График - ваш рабочий график\n"
            "💬 Админу - написать администратору\n\n"
            "Команды:\n"
            "/cancel - отменить текущее действие\n"
            "/start - главное меню"
        )
    else:
        text = "Используйте /start для начала работы"
    
    await msg.answer(text)


@router.message(F.text == "⚙️ Настройки")
async def settings_handler(msg: Message, state: FSMContext):
    """Настройки (заглушка)"""
    await state.clear()  # Ensure state is cleared for menu actions
    await msg.answer(
        "⚙️ Настройки:\n\n"
        "Эта функция в разработке.\n"
        "Скоро здесь появятся дополнительные опции."
    )