from typing import Optional, List
from datetime import datetime, date
from sqlalchemy import select, and_, or_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from database.base import BaseRepository
from models import Skill, Master, Order, Assignment, OrderStatus, master_skills
class SkillRepository(BaseRepository[Skill]):
    def __init__(self, session: AsyncSession):
        super().__init__(Skill, session)
   
    async def get_by_name(self, name: str) -> Optional[Skill]:
        result = await self.session.execute(
            select(Skill).where(Skill.name == name)
        )
        return result.scalar_one_or_none()
   
    async def get_multiple_by_ids(self, ids: List[int]) -> List[Skill]:
        result = await self.session.execute(
            select(Skill).where(Skill.id.in_(ids))
        )
        return list(result.scalars().all())
class MasterRepository(BaseRepository[Master]):
    def __init__(self, session: AsyncSession):
        super().__init__(Master, session)
   
    async def get_by_telegram_id(self, telegram_id: int):
        stmt = select(Master).where(Master.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
   
    async def get_with_skills(self, master_id: int) -> Optional[Master]:
        result = await self.session.execute(
            select(Master)
            .options(selectinload(Master.skills))
            .where(Master.id == master_id)
        )
        return result.scalar_one_or_none()
   
    async def get_by_skills(self, skill_ids: list[int]) -> list[Master]:
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
        return result.scalars().all()
   
    async def get_by_skills_or_universal(self, skill_ids: list[int]) -> list[Master]:
        """Kerakli naviklar + Универсал navikli masterlarni topadi"""
        # Avval "Универсал" navikni topamiz
        universal_skill_stmt = select(Skill.id).where(Skill.name == "Универсал")
        universal_skill_result = await self.session.execute(universal_skill_stmt)
        universal_skill_id = universal_skill_result.scalar_one_or_none()
        
        # Agar "Универсал" yo'q bo'lsa, oddiy usulda ishlaydi
        if not universal_skill_id:
            return await self.get_by_skills(skill_ids)
        
        # Kerakli naviklar + "Универсал" ni birlashtirish
        all_skill_ids = skill_ids + [universal_skill_id]
        
        subquery = (
            select(Master.id)
            .join(master_skills)
            .where(master_skills.c.skill_id.in_(all_skill_ids))
            .distinct()
        )
    
        stmt = (
            select(Master)
            .options(selectinload(Master.skills))
            .where(Master.id.in_(subquery))
        )
    
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_all_with_skills(self) -> List[Master]:
        result = await self.session.execute(
            select(Master).options(selectinload(Master.skills))
        )
        return list(result.scalars().all())
   
    async def is_free_at(self, master_id: int, dt: datetime) -> bool:
        master = await self.get(master_id)
        if not master or not master.schedule:
            return True
       
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
       
        if date_str in master.schedule:
            return time_str not in master.schedule[date_str]
        return True
   
    async def update_schedule(self, master_id: int, dt: datetime, status: str):
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
class OrderRepository(BaseRepository[Order]):
   
    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)
   
    async def get_by_number(self, number: str) -> Optional[Order]:
        result = await self.session.execute(
            select(Order).where(Order.number == number)
        )
        return result.scalar_one_or_none()
   
    async def get_by_status(self, status: OrderStatus) -> List[Order]:
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.required_skills))
            .where(Order.status == status)
            .order_by(Order.datetime.desc())
        )
        return list(result.scalars().all())
   
    async def get_all(self, limit: int = None) -> List[Order]:
        query = select(Order).order_by(Order.datetime.desc())
        if limit:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
   
    async def get_with_skills(self, order_id: int) -> Optional[Order]:
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
   
    async def count_for_date(self, order_date: date) -> int:
        result = await self.session.execute(
            select(func.count(Order.id)).where(
                and_(
                    Order.datetime >= datetime.combine(order_date, datetime.min.time()),
                    Order.datetime <= datetime.combine(order_date, datetime.max.time())
                )
            )
        )
        return result.scalar() or 0
class AssignmentRepository(BaseRepository[Assignment]):
   
    def __init__(self, session: AsyncSession):
        super().__init__(Assignment, session)
   
    
    async def get_by_master(self, master_id: int) -> List[Assignment]:
        """Barcha assignments ni order bilan birga olish"""
        result = await self.session.execute(
            select(Assignment)
            .where(Assignment.master_id == master_id)
            .options(selectinload(Assignment.order))  # MUHIM: order ni ham yuklaymiz
            .order_by(Assignment.id.desc())  # Eng yangilari birinchi
        )
        return list(result.scalars().all())
   
    async def get_by_order(self, order_id: int) -> Optional[Assignment]:
        """Получить назначение по заказу"""
        result = await self.session.execute(
            select(Assignment)
            .options(selectinload(Assignment.master))
            .where(Assignment.order_id == order_id)
        )
        return result.scalar_one_or_none()
   
    async def get_active_for_master(self, master_id: int) -> List[Assignment]:
        """Активные назначения мастера"""
        result = await self.session.execute(
            select(Assignment)
            .join(Assignment.order)
            .options(selectinload(Assignment.order))
            .where(
                and_(
                    Assignment.master_id == master_id,
                    Order.status.in_([
                        OrderStatus.confirmed,
                        OrderStatus.in_progress,
                        OrderStatus.arrived
                    ])
                )
            )
            .order_by(Order.datetime)
        )
        return list(result.scalars().all())
    async def get_assignments_by_date_range(self, date_from: date, date_to: date) -> List[Assignment]:
        """Назначения по периоду"""
        query = select(Assignment).join(Assignment.order).where(
            and_(
                Order.datetime >= datetime.combine(date_from, datetime.min.time()),
                Order.datetime <= datetime.combine(date_to, datetime.max.time())
            )
        ).options(selectinload(Assignment.order), selectinload(Assignment.master))
        result = await self.session.execute(query)
        return result.scalars().all()
    async def get_all_assignments(self) -> List[Assignment]:
        """Все назначения"""
        result = await self.session.execute(
            select(Assignment).options(selectinload(Assignment.order), selectinload(Assignment.master))
        )
        return result.scalars().all()