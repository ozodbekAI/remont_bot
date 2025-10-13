from typing import Optional, List, Tuple
from datetime import datetime, date
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import Order, OrderStatus, order_skills
from repositories.order import OrderRepository
from repositories.assignment import AssignmentRepository


class OrderService:
    """Сервис для работы с заказами"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.assignment_repo = AssignmentRepository(session)
    
    async def create_order(
        self,
        client_name: str,
        phone: str,
        address: str,
        datetime_obj: datetime,
        type: str,
        brand: str,
        model: str,
        comment: str,
        skill_ids: List[int] = None
    ) -> Order:
        """Создать новый заказ"""
        # Генерируем номер заказа на основе максимального существующего
        max_seq = await self.order_repo.get_max_number_for_date(datetime_obj.date())
        date_str = datetime_obj.strftime('%Y-%m-%d')
        number = f"{date_str}-{max_seq + 1:03d}"
        
        # Создаем заказ
        order = await self.order_repo.create(
            number=number,
            client_name=client_name,
            phone=phone,
            address=address,
            datetime=datetime_obj,
            type=type,
            brand=brand,
            model=model,
            comment=comment,
            status=OrderStatus.new
        )
        await self.session.flush()
        
        # Добавляем навыки
        if skill_ids:
            for skill_id in skill_ids:
                stmt = insert(order_skills).values(order_id=order.id, skill_id=skill_id)
                await self.session.execute(stmt)
        
        await self.session.commit()
        await self.session.refresh(order)
        
        return order
    
    async def assign_master_to_order(self, order_id: int, master_id: int):
        """Назначить мастера на заказ, поддерживая переназначение"""
        # Проверяем, существует ли мастер
        from repositories.master import MasterRepository
        master_repo = MasterRepository(self.session)
        master = await master_repo.get(master_id)
        if not master:
            raise ValueError(f"Мастер с ID {master_id} не найден")

        # Проверяем, есть ли уже назначение
        existing = await self.assignment_repo.get_by_order(order_id)
        if existing:
            if existing.master_id == master_id:
                # Если тот же мастер, ничего не делаем
                return await self.order_repo.get(order_id)
            else:
                # Удаляем старое назначение, если мастер другой
                await self.assignment_repo.delete(existing.id)
        
        # Создаем новое назначение
        await self.assignment_repo.create(
            order_id=order_id,
            master_id=master_id
        )
        
        # Коммитим изменения (статус остается OrderStatus.new)
        await self.session.commit()
        
        # Возвращаем заказ для уведомлений
        order = await self.order_repo.get(order_id)
        return order
    
    async def get_orders_by_master(self, master_id: int) -> List[Order]:
        """Получить все заказы мастера"""
        assignments = await self.assignment_repo.get_by_master(master_id)
        order_ids = [a.order_id for a in assignments]
        if not order_ids:
            return []
        
        orders = await self.order_repo.get_by_ids(order_ids)
        return sorted(orders, key=lambda x: x.datetime, reverse=True)
    
    async def update_status(
        self,
        order_id: int,
        status: OrderStatus,
        work_amount: float = None,
        expenses: float = None,
        work_description: str = None,
        work_photos: List[str] = None
    ) -> Order:
        """Обновить статус заказа"""
        order = await self.order_repo.get(order_id)
        order.status = status
        
        if status == OrderStatus.completed:
            if work_amount is not None:
                setattr(order, 'work_amount', work_amount)
            if expenses is not None:
                setattr(order, 'expenses', expenses)
            if work_description is not None:
                setattr(order, 'work_description', work_description)
            if work_photos is not None:
                setattr(order, 'work_photos', work_photos)
            
            order.calculate_profit()
        
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(order)
        return order
    
    async def get_orders_by_filter(
        self,
        status: Optional[OrderStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[Order]:
        """Получить заказы с фильтрами"""
        if date_from and date_to:
            return await self.order_repo.get_by_date_range(date_from, date_to, status)
        elif status:
            return await self.order_repo.get_by_status(status)
        else:
            return await self.order_repo.get_all(limit=100)