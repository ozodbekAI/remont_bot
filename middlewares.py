from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, Update

from config import ADMIN_IDS
from database.engine import get_session
from repositories.repositories import MasterRepository


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
       
        if isinstance(event, Update):
            if event.message:
                actual_event = event.message
            elif event.callback_query:
                actual_event = event.callback_query
            else:
                return await handler(event, data)
        else:
            actual_event = event
        
        
        if not isinstance(actual_event, (Message, CallbackQuery)):
            return await handler(event, data)
        
        user_id = actual_event.from_user.id
        
        if user_id in ADMIN_IDS:
            data["role"] = "admin"
            return await handler(event, data)
        
        async with get_session() as session:
            master_repo = MasterRepository(session)
            master = await master_repo.get_by_telegram_id(user_id)
            
            if master:
                data["role"] = "master"
                data["master"] = master
                return await handler(event, data)

        if isinstance(actual_event, Message):
            await actual_event.answer(
                "❌ Доступ запрещен!\n\n"
                "Вы не зарегистрированы в системе.\n"
                "Обратитесь к администратору для получения доступа.\n"
                f"Ваш ID: {user_id}"
            )
        else:
            await actual_event.answer("❌ Доступ запрещен!", show_alert=True)
        
        return None