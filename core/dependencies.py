from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database.engine import get_session
from services.order_service import OrderService
from services.master_service import MasterService
from services.report_service import ReportService
from services.skill_service import SkillService


class ServiceMiddleware(BaseMiddleware):
    """
    Middleware для внедрения сервисов в handler data
    
    Usage в handler:
        async def handler(msg: Message, order_service: OrderService):
            order = await order_service.create_order(...)
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with get_session() as session:
            # Внедряем все сервисы
            data['session'] = session
            data['order_service'] = OrderService(session)
            data['report_service'] = ReportService(session)
            data['master_service'] = MasterService(session)
            data['skill_service'] = SkillService(session)
            
            return await handler(event, data)