from typing import Optional, List, Dict
from datetime import datetime, date
from sqlalchemy import insert, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Master, OrderStatus, Skill, Order, master_skills
from repositories.master import MasterRepository
from repositories.assignment import AssignmentRepository
from repositories.order import OrderRepository
from repositories.skill import SkillRepository


class MasterService:
    """Сервис для работы с мастерами"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.master_repo = MasterRepository(session)
        self.assignment_repo = AssignmentRepository(session)
        self.skill_repo = SkillRepository(session)
        self.order_repo = OrderRepository(session)
    
    async def get_masters_for_assignment(
        self,
        order_datetime: datetime,
        skill_ids: List[int] = None,
        buffer_hours: int = 4
    ) -> List[Dict]:
        """
        Получить всех мастеров для назначения на заказ с информацией о навыках и доступности.
        - skill_ids: требуемые навыки (если есть, показываем совпадения).
        - order_datetime: время заказа для проверки доступности.
        - buffer_hours: буфер времени (по умолчанию 4 часа).
        Возвращает список словарей с данными мастеров.
        """
        # Получаем всех мастеров с навыками
        masters = await self.master_repo.get_all_with_skills()
        result = []

        for master in masters:
            # Проверяем доступность с буфером
            is_available = await self.master_repo.check_availability_with_buffer(
                master.id, order_datetime, buffer_hours
            )
            
            # Количество заказов на сегодня (исключая new и rejected)
            today_count = await self.assignment_repo.count_today_assignments(master.id)
            
            # Навыки мастера
            master_skill_ids = [s.id for s in master.skills] if master.skills else []
            skills_text = ", ".join([s.name for s in master.skills]) if master.skills else "Нет навыков"
            
            # Совпадение навыков (если skill_ids указаны)
            matching_skills = []
            missing_skills = []
            if skill_ids:
                matching_skills = [s for s in master.skills if s.id in skill_ids]
                missing_skills = [s for s in (await self.skill_repo.get_by_ids(skill_ids)) if s.id not in master_skill_ids]
            
            result.append({
                "master": master,
                "today_orders": today_count,
                "skills": skills_text,
                "is_available": is_available,
                "matching_skills": [s.name for s in matching_skills] if skill_ids else [],
                "missing_skills": [s.name for s in missing_skills] if skill_ids else [],
                "skills_match_percent": (
                    len(matching_skills) / len(skill_ids) * 100 if skill_ids else 100
                )
            })
        
        # Сортировка: сначала по совпадению навыков (если есть), затем по количеству заказов
        result.sort(
            key=lambda x: (
                -x["skills_match_percent"] if skill_ids else 0,  # Сначала по совпадению навыков (убывание)
                x["today_orders"]  # Затем по количеству заказов (возрастание)
            )
        )
        
        return result
    
    async def find_suitable_masters(
        self,
        order_datetime: datetime,
        skill_ids: List[int],
        buffer_hours: int = 4
    ) -> List[Dict]:
        """
        Мос мастерларни топиш (навиклари тўғри ва вақти бўш)
        4 соат оралиқ билан текшириш, включая заявки в статусе new
        """
        if not skill_ids:
            return []
        
        # Керакли навиклари бўлган мастерларни оламиз
        masters = await self.master_repo.get_by_skills(skill_ids)
        
        suitable = []
        
        for master in masters:
            # Получаем все активные и новые назначения мастера на день
            assignments = await self.assignment_repo.get_active_for_master(master.id)
            is_time_conflict = False
            
            # Проверяем конфликт по времени с учетом буфера
            for assignment in assignments:
                existing_time = assignment.order.datetime
                time_diff = abs((order_datetime - existing_time).total_seconds() / 3600)
                if time_diff < buffer_hours:
                    is_time_conflict = True
                    break
            
            if is_time_conflict:
                continue
            
            # Проверяем доступность с буфером (дополнительно для графика)
            is_available = await self.master_repo.check_availability_with_buffer(
                master.id, 
                order_datetime, 
                buffer_hours
            )
            
            if not is_available:
                continue
            
            # Бугунги заказлар сони
            today_count = await self.assignment_repo.count_today_assignments(master.id)
            
            # Навиклар рўйхати
            skills_text = ", ".join([s.name for s in master.skills]) if master.skills else "Нет навыков"
            
            suitable.append({
                "master": master,
                "today_orders": today_count,
                "skills": skills_text
            })
        
        # Сортировка: у кого меньше заказов сегодня
        suitable.sort(key=lambda x: x["today_orders"])
        
        return suitable
    
    async def auto_assign_best_master(
        self,
        order_datetime: datetime,
        skill_ids: List[int]
    ) -> Optional[Master]:
        """
        Автоматик энг яхши мастерни топиш
        (бугун энг кам заказ олган)
        """
        suitable = await self.find_suitable_masters(order_datetime, skill_ids)
        
        if not suitable:
            return None
        
        # Энг кам заказли мастерни қайтарамиз
        return suitable[0]["master"]
    
    async def get_all_masters_with_today_count(self) -> List[Dict]:
        """
        ЯНГИ: Барча мастерларни бугунги заказлар сони билан олиш
        (навиқ ва вақт текшириш йўқ - фақат кўрсатиш учун)
        """
        masters = await self.master_repo.get_all_with_skills()
        
        result = []
        
        for master in masters:
            # Бугунги заказлар сони
            today_count = await self.assignment_repo.count_today_assignments(master.id)
            
            # Навиқлар
            skills_text = ", ".join([s.name for s in master.skills]) if master.skills else "Нет навыков"
            
            result.append({
                "master": master,
                "today_orders": today_count,
                "skills": skills_text
            })
        
        # Сортировка
        result.sort(key=lambda x: x["today_orders"])
        
        return result
    
    async def find_available_master(
        self,
        datetime: datetime,
        skill_ids: List[int],
        exclude_master_id: int = None
    ) -> Optional[Master]:
        """
        ЯНГИ: Бошқа мастер топиш (мастер рад этганда)
        exclude_master_id - рад этган мастерни чиқариш учун
        """
        suitable = await self.find_suitable_masters(datetime, skill_ids)
        
        # Рад этган мастерни олиб ташлаймиз
        if exclude_master_id:
            suitable = [s for s in suitable if s["master"].id != exclude_master_id]
        
        if not suitable:
            return None
        
        return suitable[0]["master"]
    
    async def create_master(
        self,
        name: str,
        telegram_id: int,
        skill_ids: List[int] = None,
        phone: str = None
    ) -> dict:
        """Создать мастера"""
        master = await self.master_repo.create(
            name=name,
            telegram_id=telegram_id,
            phone=phone
        )
        await self.session.flush()
        
        if skill_ids:
            for skill_id in skill_ids:
                stmt = insert(master_skills).values(
                    master_id=master.id,
                    skill_id=skill_id
                )
                await self.session.execute(stmt)
        
        skills = []
        if skill_ids:
            stmt = select(Skill).where(Skill.id.in_(skill_ids))
            result = await self.session.execute(stmt)
            skills = result.scalars().all()
        
        await self.session.commit()
        
        return {
            "id": master.id,
            "name": master.name,
            "telegram_id": master.telegram_id,
            "phone": master.phone,
            "skills": [{"id": s.id, "name": s.name} for s in skills]
        }
    
    async def update_master(
        self,
        master_id: int,
        name: str = None,
        phone: str = None,
        telegram_id: int = None
    ) -> Master:
        """Обновить мастера"""
        master = await self.master_repo.get(master_id)
        if not master:
            raise ValueError("Мастер не найден")
        
        if name is not None:
            master.name = name
        if phone is not None:
            master.phone = phone
        if telegram_id is not None:
            master.telegram_id = telegram_id
        
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(master)
        return master
    
    async def delete_master(self, master_id: int) -> bool:
        """Удалить мастера"""
        master = await self.master_repo.get(master_id)
        if not master:
            return False
        
        assignments = await self.assignment_repo.get_by_master(master_id)
        for assignment in assignments:
            await self.session.delete(assignment)
        
        stmt_delete_skills = delete(master_skills).where(master_skills.c.master_id == master_id)
        await self.session.execute(stmt_delete_skills)
        
        await self.session.delete(master)
        await self.session.commit()
        return True
    
    async def update_skills(self, master_id: int, skill_ids: List[int]):
        """Обновить навыки мастера"""
        stmt_delete = delete(master_skills).where(master_skills.c.master_id == master_id)
        await self.session.execute(stmt_delete)
        
        for skill_id in skill_ids:
            stmt = insert(master_skills).values(master_id=master_id, skill_id=skill_id)
            await self.session.execute(stmt)
        
        await self.session.commit()
    
    async def get_master_orders(self, master_id: int) -> List[Order]:
        """Получить все заказы мастера"""
        assignments = await self.assignment_repo.get_by_master(master_id)
        order_ids = [a.order_id for a in assignments]
        if not order_ids:
            return []
        
        orders = await self.order_repo.get_by_ids(order_ids)
        return sorted(orders, key=lambda x: x.datetime, reverse=True)
    
    async def get_all_with_skills(self):
        """Получить всех мастеров с навыками"""
        return await self.master_repo.get_all_with_skills()
    
    async def update_schedule(self, master_id: int, dt: datetime, status: str):
        """Обновить график мастера"""
        master = await self.master_repo.get(master_id)
        if not master:
            raise ValueError("Мастер не найден")
        
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
        
        # Графикни yangilash
        schedule = master.schedule or {}
        
        # schedule ni lug'at ekanligini tekshirish
        if not isinstance(schedule, dict):
            schedule = {}
        
        # date_str uchun lug'atni tayyorlash
        if date_str not in schedule:
            schedule[date_str] = {}
        
        # time_str uchun statusni yangilash
        schedule[date_str][time_str] = status
        master.schedule = schedule
        
        await self.session.flush()
        await self.session.commit()

    async def get_current_orders(self, master_id: int) -> List[Order]:
        """Получить текущие активные заказы мастера (new, confirmed, in_progress, arrived)"""
        assignments = await self.assignment_repo.get_by_master(master_id)
        order_ids = [a.order_id for a in assignments]
        if not order_ids:
            return []
        
        orders = await self.order_repo.get_by_ids(order_ids)
        active_orders = [
            o for o in orders 
            if o.status in [OrderStatus.confirmed, OrderStatus.in_progress, OrderStatus.arrived]
        ]
        return sorted(active_orders, key=lambda x: x.datetime, reverse=True)
    

    async def get_today_orders(self, master_id: int) -> List[Order]:
        """Получить заказы мастера на сегодня"""
        today = date.today()
        assignments = await self.assignment_repo.get_by_master(master_id)
        order_ids = [a.order_id for a in assignments]
        if not order_ids:
            return []
        
        orders = await self.order_repo.get_by_date_range(
            date_from=today,
            date_to=today,
            status=None  # Все статусы, но мы отфильтруем ниже
        )
        active_orders = [
            o for o in orders 
            if o.id in order_ids and o.status in [
                OrderStatus.confirmed, OrderStatus.in_progress, OrderStatus.arrived
            ]
        ]
        return sorted(active_orders, key=lambda x: x.datetime)