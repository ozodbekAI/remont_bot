from typing import Callable
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import get_session
from services.services import (
    OrderService, MasterService, 
    SkillService, ReportService
)


class ServiceFactory:
    """
    Фабрика сервисов с Dependency Injection.
    Принцип: Dependency Inversion - зависимости через абстракции.
    """
    
    @staticmethod
    def get_order_service(session: AsyncSession) -> OrderService:
        return OrderService(session)
    
    @staticmethod
    def get_master_service(session: AsyncSession) -> MasterService:
        return MasterService(session)
    
    @staticmethod
    def get_skill_service(session: AsyncSession) -> SkillService:
        return SkillService(session)
    
    @staticmethod
    def get_report_service(session: AsyncSession) -> ReportService:
        return ReportService(session)


from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import get_session
from services.services import (
    OrderService, MasterService, 
    SkillService, ReportService
)


class ServiceMiddleware(BaseMiddleware):
    """
    Middleware для внедрения сервисов в handler data.
    
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
            data['master_service'] = MasterService(session)
            data['skill_service'] = SkillService(session)
            data['report_service'] = ReportService(session)
            
            return await handler(event, data)