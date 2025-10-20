from typing import Optional, List
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.base import BaseRepository
from models import Order, OrderStatus


class OrderRepository(BaseRepository[Order]):
    """Repository для работы с заказами"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)
    
    async def get_by_number(self, number: str) -> Optional[Order]:
        """Получить заказ по номеру"""
        result = await self.session.execute(
            select(Order).where(Order.number == number)
        )
        return result.scalar_one_or_none()
    
    async def get_by_status(self, status: OrderStatus, limit: Optional[int] = None, offset: Optional[int] = 0) -> List[Order]:
        """Получить заказы по статусу с пагинацией"""
        query = select(Order).where(Order.status == status).order_by(Order.datetime.desc())
        if limit is not None:
            query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_count_by_status(self, status: OrderStatus) -> int:
        """Получить количество заказов по статусу"""
        query = select(func.count()).select_from(Order).where(Order.status == status)
        result = await self.session.execute(query)
        return result.scalar_one()
    
    async def get_all(self, limit: Optional[int] = None, offset: Optional[int] = 0) -> List[Order]:
        """Получить все заказы с пагинацией"""
        query = select(Order).order_by(Order.datetime.desc())
        if limit is not None:
            query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_with_skills(self, order_id: int) -> Optional[Order]:
        """Получить заказ с навыками"""
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.required_skills))
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_date_range(
        self,
        date_from: date,
        date_to: date,
        status: Optional[OrderStatus] = None
    ) -> List[Order]:
        """Получить заказы за период"""
        query = select(Order).where(
            and_(
                Order.datetime >= datetime.combine(date_from, datetime.min.time()),
                Order.datetime <= datetime.combine(date_to, datetime.max.time())
            )
        )
        if status:
            query = query.where(Order.status == status)
        
        result = await self.session.execute(query.order_by(Order.datetime))
        return list(result.scalars().all())
    
    async def get_max_number_for_date(self, order_date: date) -> int:
        """Получить максимальный sequential номер заказа за дату"""
        date_str = order_date.strftime('%Y-%m-%d')
        result = await self.session.execute(
            select(func.max(Order.number))
            .where(Order.number.like(f"{date_str}-%"))
        )
        max_number = result.scalar()
        if max_number:
            try:
                seq = int(max_number.split('-')[-1])
                return seq
            except ValueError:
                return 0
        return 0
    
    async def get_by_ids(self, order_ids: List[int]) -> List[Order]:
        """Получить заказы по списку ID"""
        if not order_ids:
            return []
        result = await self.session.execute(
            select(Order)
            .where(Order.id.in_(order_ids))
            .order_by(Order.datetime.desc())
        )
        return list(result.scalars().all())
    
    async def get_count(self) -> int:
        """Получить общее количество заказов"""
        query = select(func.count()).select_from(Order)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_by_date_range(self, start_date: date, end_date: date, limit: Optional[int] = None, offset: Optional[int] = 0) -> List[Order]:
        """Получить заказы по диапазону дат с пагинацией"""
        query = select(Order).where(
            Order.datetime >= start_date,
            Order.datetime <= end_date + timedelta(days=1)  # Assuming import from datetime
        ).order_by(Order.datetime.desc())
        if limit is not None:
            query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    

    async def get_count_by_date_range(self, start_date: date, end_date: date) -> int:
        """Получить количество заказов по диапазону дат"""
        query = select(func.count()).select_from(Order).where(
            Order.datetime >= start_date,
            Order.datetime <= end_date + timedelta(days=1)
        )
        result = await self.session.execute(query)
        return result.scalar_one()
    
