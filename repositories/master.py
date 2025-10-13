from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.base import BaseRepository
from models import Assignment, Master, Order, OrderStatus, master_skills


class MasterRepository(BaseRepository[Master]):
    """Repository для работы с мастерами"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Master, session)
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Master]:
        """Получить мастера по Telegram ID"""
        stmt = select(Master).where(Master.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_with_skills(self, master_id: int) -> Optional[Master]:
        """Получить мастера с навыками"""
        result = await self.session.execute(
            select(Master)
            .options(selectinload(Master.skills))
            .where(Master.id == master_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_skills(self, skill_ids: List[int]) -> List[Master]:
        """Получить мастеров по навыкам"""
        subquery = (
            select(Master.id)
            .join(master_skills)
            .where(master_skills.c.skill_id.in_(skill_ids))
            .distinct()
        )
        
        stmt = (
            select(Master)
            .options(selectinload(Master.skills))
            .where(Master.id.in_(subquery))
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_all_with_skills(self) -> List[Master]:
        """Получить всех мастеров с навыками"""
        result = await self.session.execute(
            select(Master).options(selectinload(Master.skills))
        )
        return list(result.scalars().all())
    
    async def is_free_at(self, master_id: int, dt: datetime) -> bool:
        """Проверить свободен ли мастер в указанное время"""
        master = await self.get(master_id)
        if not master or not master.schedule:
            return True
        
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
        
        if date_str in master.schedule:
            return time_str not in master.schedule[date_str]
        return True
    
    async def update_schedule(self, master_id: int, dt: datetime, status: str):
        """Обновить график мастера"""
        master = await self.get(master_id)
        if not master:
            return
        
        if not master.schedule:
            master.schedule = {}
        
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
        
        if date_str not in master.schedule:
            master.schedule[date_str] = []
        
        if status == "busy" and time_str not in master.schedule[date_str]:
            master.schedule[date_str].append(time_str)
        elif status == "free" and time_str in master.schedule[date_str]:
            master.schedule[date_str].remove(time_str)
        
        await self.session.flush()
    
    async def check_availability_with_buffer(
        self, 
        master_id: int, 
        order_datetime: datetime, 
        buffer_hours: int = 4
    ) -> bool:
        """
        Проверка доступности мастера с учетом буфера времени
        (учитываем и new, и активные статусы)
        """
        assignments = await self.get_active_assignments(master_id)
        for assignment in assignments:
            existing_time = assignment.order.datetime
            time_diff = abs((order_datetime - existing_time).total_seconds() / 3600)
            if time_diff < buffer_hours:
                return False
        
        # Проверяем график мастера
        date_str = order_datetime.strftime("%Y-%m-%d")
        time_str = order_datetime.strftime("%H:%M")
        schedule = (await self.get(master_id)).schedule or {}
        
        if date_str in schedule and time_str in schedule[date_str]:
            return schedule[date_str][time_str] == "free"
        
        return True

    async def get_active_assignments(self, master_id: int) -> List[Assignment]:
        """
        Получить все назначения мастера, включая new
        """
        result = await self.session.execute(
            select(Assignment)
            .join(Assignment.order)
            .where(
                and_(
                    Assignment.master_id == master_id,
                    Order.status.in_([
                        OrderStatus.new,  # Добавляем new
                        OrderStatus.confirmed,
                        OrderStatus.in_progress,
                        OrderStatus.arrived
                    ])
                )
            )
            .options(selectinload(Assignment.order))
        )
        return list(result.scalars().all())