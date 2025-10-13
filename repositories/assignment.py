from typing import Optional, List
from datetime import date, datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.base import BaseRepository
from models import Assignment, Order, OrderStatus


class AssignmentRepository(BaseRepository[Assignment]):
    """Repository для работы с назначениями мастеров"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Assignment, session)
    
    async def get_by_order(self, order_id: int) -> Optional[Assignment]:
        """Получить назначение по заказу"""
        result = await self.session.execute(
            select(Assignment)
            .options(selectinload(Assignment.master))
            .where(Assignment.order_id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_order(self, order_id: int) -> Optional[Assignment]:
        """Получить назначение по заказу"""
        result = await self.session.execute(
            select(Assignment)
            .options(selectinload(Assignment.master))
            .where(Assignment.order_id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_active_for_master(self, master_id: int) -> List[Assignment]:
        """Получить активные назначения мастера"""
        result = await self.session.execute(
            select(Assignment)
            .join(Assignment.order)
            .options(selectinload(Assignment.order))
            .where(
                and_(
                    Assignment.master_id == master_id,
                    Order.status.in_([
                        OrderStatus.new,
                        OrderStatus.confirmed,
                        OrderStatus.in_progress,
                        OrderStatus.arrived
                    ])
                )
            )
            .order_by(Order.datetime)
        )
        return list(result.scalars().all())
    
    async def get_by_date_range(self, date_from: date, date_to: date) -> List[Assignment]:
        """Получить назначения за период"""
        query = select(Assignment).join(Assignment.order).where(
            and_(
                Order.datetime >= datetime.combine(date_from, datetime.min.time()),
                Order.datetime <= datetime.combine(date_to, datetime.max.time())
            )
        ).options(selectinload(Assignment.order), selectinload(Assignment.master))
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_all_assignments(self) -> List[Assignment]:
        """Получить все назначения"""
        result = await self.session.execute(
            select(Assignment).options(
                selectinload(Assignment.order),
                selectinload(Assignment.master)
            )
        )
        return list(result.scalars().all())
    
    async def count_today_assignments(self, master_id: int) -> int:
        """
        Подсчитать количество АКТИВНЫХ и НОВЫХ заказов мастера на сегодня
        (исключая rejected и completed)
        """
        today = date.today()
        result = await self.session.execute(
            select(Assignment)
            .join(Assignment.order)
            .where(
                and_(
                    Assignment.master_id == master_id,
                    Order.status.in_([
                        OrderStatus.new,  # Добавляем new статус
                        OrderStatus.confirmed,
                        OrderStatus.in_progress,
                        OrderStatus.arrived
                    ])
                )
            )
        )
        return len(list(result.scalars().all()))