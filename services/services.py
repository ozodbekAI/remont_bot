from typing import Optional, List, Dict
from datetime import datetime, date, timedelta
from sqlalchemy import insert, delete, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
import random
from models import Order, Master, Skill, Assignment, OrderStatus, order_skills, master_skills
from repositories.repositories import (
    OrderRepository, MasterRepository,
    SkillRepository, AssignmentRepository
)
class OrderService:
   
    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.assignment_repo = AssignmentRepository(session)
        self.master_repo = MasterRepository(session)
   
    async def create_order(
        self,
        client_name: str,
        phone: str,
        address: str,
        datetime: datetime,
        type: str,
        brand: str,
        model: str,
        comment: str,
        skill_ids: List[int] = None
    ) -> tuple[Order, bool]:
        count = await self.order_repo.count_for_date(datetime.date())
        date_str = datetime.strftime('%Y-%m-%d')
        number = f"{date_str}-{count + 1:03d}"
       
        order = await self.order_repo.create(
            number=number,
            client_name=client_name,
            phone=phone,
            address=address,
            datetime=datetime,
            type=type,
            brand=brand,
            model=model,
            comment=comment,
            status=OrderStatus.new
        )
        await self.session.flush()
       
        if skill_ids:
            for skill_id in skill_ids:
                stmt = insert(order_skills).values(order_id=order.id, skill_id=skill_id)
                await self.session.execute(stmt)
       
        await self.session.commit()
        await self.session.refresh(order)
       
        assigned_master = await self.assign_to_master(order.id)
        assigned = assigned_master is not None
       
        return order, assigned
   
    async def assign_to_master(self, order_id: int) -> Optional[Master]:
        order = await self.order_repo.get_with_skills(order_id)
        if not order or not order.required_skills:
            return None
       
        skill_ids = [s.id for s in order.required_skills]
        masters = await self.master_repo.get_by_skills(skill_ids)
       
        for master in masters:
            if await self.master_repo.is_free_at(master.id, order.datetime):
                await self.assignment_repo.create(
                    order_id=order.id,
                    master_id=master.id
                )
                order.status = OrderStatus.confirmed
                await self.master_repo.update_schedule(
                    master.id,
                    order.datetime,
                    "busy"
                )
                await self.session.flush()
                await self.session.commit()
                return master
       
        return None
   
    async def update_status(
        self,
        order_id: int,
        status: OrderStatus,
        work_amount: float = None,
        expenses: float = None,
        work_description: str = None,
        work_photos: List[str] = None
    ) -> Order:
        """Обновить статус заказа с дополнительными данными"""
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
           
            assignment = await self.assignment_repo.get_by_order(order_id)
            if assignment:
                await self.master_repo.update_schedule(
                    assignment.master_id,
                    order.datetime,
                    "free"
                )
       
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
        if date_from and date_to:
            return await self.order_repo.get_by_date_range(
                date_from, date_to, status
            )
        elif status:
            return await self.order_repo.get_by_status(status)
        else:
            return await self.order_repo.get_all(limit=100)
class MasterService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.master_repo = MasterRepository(session)
        self.skill_repo = SkillRepository(self.session)
        self.assignment_repo = AssignmentRepository(session)
   
    async def create_master(
        self,
        name: str,
        telegram_id: int,
        skill_ids: List[int] = None,
        phone: str = None
    ) -> dict:
        from sqlalchemy import select, insert
        from models import Master, Skill, master_skills
       
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
        """Удалить мастера (и его назначения/навыки)"""
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
        stmt_delete = delete(master_skills).where(master_skills.c.master_id == master_id)
        await self.session.execute(stmt_delete)
        for skill_id in skill_ids:
            stmt = insert(master_skills).values(master_id=master_id, skill_id=skill_id)
            await self.session.execute(stmt)
       
        await self.session.commit()
   
    async def get_master_orders(self, master_id: int) -> List[Order]:
        assignments = await self.assignment_repo.get_by_master(master_id)
        return [a.order for a in assignments if a.order]
   
    async def get_all_with_skills(self):
        result = await self.session.execute(
            select(Master).options(selectinload(Master.skills))
        )
        return result.scalars().all()
    async def update_schedule(self, master_id: int, dt: datetime, status: str):
        """Update master's schedule"""
        await self.master_repo.update_schedule(master_id, dt, status)
   
    # НОВЫЙ МЕТОД: Поиск доступного мастера
    async def find_available_master(
        self,
        datetime: datetime,
        skill_ids: List[int],
        exclude_master_id: Optional[int] = None
    ) -> Optional[Master]:
        """
        Найти свободного мастера с нужными навыками на указанное время
        
        Args:
            datetime: Время заказа
            skill_ids: Список ID необходимых навыков
            exclude_master_id: ID мастера, которого нужно исключить (например, отказавшегося)
           
        Returns:
            Master объект или None если не найден
        """
        if not skill_ids:
            return None
       
        # Получаем всех мастеров с нужными навыками
        masters = await self.master_repo.get_by_skills(skill_ids)
       
        suitable = []
        for master in masters:
            # Пропускаем исключенного мастера (того кто отказался)
            if exclude_master_id and master.id == exclude_master_id:
                continue
            
            if await self.is_available_with_buffer(master.id, datetime):
                suitable.append(master)
       
        if suitable:
            return random.choice(suitable)
       
        return None
    
    async def is_available_with_buffer(self, master_id: int, dt: datetime) -> bool:
        """
        Проверяет доступность мастера с учетом буфера в 4 часа
        Мастер считается недоступным если у него есть заказ в пределах ±4 часа
        """
        # Получаем мастера
        master = await self.master_repo.get(master_id)
        if not master:
            return False
        
        # Проверяем базовую доступность (точное время)
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
        
        if master.schedule and date_str in master.schedule:
            if time_str in master.schedule[date_str]:
                return False  # Уже занят в это точное время
        
        # Если расписание пустое - мастер свободен
        if not master.schedule:
            return True
        
        # Собираем все занятые временные слоты мастера
        busy_datetimes = []
        for schedule_date_str, times in master.schedule.items():
            for schedule_time_str in times:
                busy_dt_str = f"{schedule_date_str} {schedule_time_str}"
                try:
                    busy_dt = datetime.strptime(busy_dt_str, "%Y-%m-%d %H:%M")
                    busy_datetimes.append(busy_dt)
                except ValueError:
                    # Игнорируем некорректные форматы
                    continue
        
        # Проверяем: есть ли занятые слоты в пределах ±4 часов от нового времени
        buffer = timedelta(hours=4)
        for busy_dt in busy_datetimes:
            time_difference = abs(dt - busy_dt)
            if time_difference < buffer:
                # Нашли конфликт - мастер занят в пределах 4 часов
                return False
        
        # Все проверки пройдены - мастер доступен
        return True

class SkillService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.skill_repo = SkillRepository(session)
   
    async def create_skill(self, name: str, description: str = None) -> Skill:
        return await self.skill_repo.create(
            name=name,
            description=description
        )
   
    async def get_all_skills(self) -> List[Skill]:
        return await self.skill_repo.get_all()
class ReportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.assignment_repo = AssignmentRepository(session)
        self.master_repo = MasterRepository(session)
   
    async def get_report(
        self,
        date_from: date,
        date_to: date
    ) -> Dict:
        orders = await self.order_repo.get_by_date_range(
            date_from,
            date_to,
            OrderStatus.completed
        )
       
        total_profit = sum(getattr(o, 'profit', 0) for o in orders)
        total_revenue = sum(getattr(o, 'work_amount', 0) for o in orders)
        total_expenses = sum(getattr(o, 'expenses', 0) for o in orders)
       
        return {
            "orders_count": len(orders),
            "total_profit": total_profit,
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "average_profit": total_profit / len(orders) if orders else 0
        }
    async def get_financial_report(self, date_from: Optional[date] = None, date_to: Optional[date] = None) -> Dict:
        """Финансовый отчет (все данные если None)"""
        if date_from is None and date_to is None:
            orders = await self.order_repo.get_by_status(OrderStatus.completed)
        else:
            orders = await self.order_repo.get_by_date_range(date_from, date_to, OrderStatus.completed)
        total_profit = sum(getattr(o, 'profit', 0) for o in orders)
        total_revenue = sum(getattr(o, 'work_amount', 0) for o in orders)
        total_expenses = sum(getattr(o, 'expenses', 0) for o in orders)
        return {
            "orders_count": len(orders),
            "total_profit": total_profit,
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "average_profit": total_profit / len(orders) if orders else 0
        }
    async def get_masters_report(self, date_from: Optional[date] = None, date_to: Optional[date] = None) -> Dict[str, Dict]:
        """Полный отчет по всем мастерам"""
        if date_from is None and date_to is None:
            assignments = await self.assignment_repo.get_all_assignments()
        else:
            assignments = await self.assignment_repo.get_assignments_by_date_range(date_from, date_to)
        stats = {}
        for assignment in assignments:
            if assignment.order and assignment.order.status == OrderStatus.completed:
                master_name = assignment.master.name
                if master_name not in stats:
                    stats[master_name] = {"orders_count": 0, "total_profit": 0.0}
                stats[master_name]["orders_count"] += 1
                stats[master_name]["total_profit"] += getattr(assignment.order, 'profit', 0)
        return stats
    async def get_orders_report(self, date_from: Optional[date] = None, date_to: Optional[date] = None) -> List[Order]:
        """Полный список заказов"""
        if date_from is None and date_to is None:
            return await self.order_repo.get_by_status(OrderStatus.completed)
        else:
            return await self.order_repo.get_by_date_range(date_from, date_to, OrderStatus.completed)
    async def get_financial_export_data(self, date_from: Optional[date] = None, date_to: Optional[date] = None) -> pd.DataFrame:
        """Полные данные для экспорта финансового отчета"""
        orders = await self.get_orders_report(date_from, date_to)
        data = []
        for order in orders:
            data.append({
                "Номер": order.number,
                "Дата": order.datetime.strftime("%Y-%m-%d"),
                "Клиент": order.client_name,
                "Выручка": getattr(order, 'work_amount', 0),
                "Расходы": getattr(order, 'expenses', 0),
                "Прибыль": getattr(order, 'profit', 0),
                "Описание работ": getattr(order, 'work_description', None) or "Не указано",
                "Фото": len(getattr(order, 'work_photos', None) or [])
            })
        df = pd.DataFrame(data)
        if not df.empty:
            df.loc[len(df)] = [
                "Итого", "", "",
                df["Выручка"].sum(),
                df["Расходы"].sum(),
                df["Прибыль"].sum(),
                "", ""
            ]
        return df
    async def get_masters_export_data(self, date_from: Optional[date] = None, date_to: Optional[date] = None) -> pd.DataFrame:
        """Полные данные для экспорта по мастерам"""
        stats = await self.get_masters_report(date_from, date_to)
        data = [{"Мастер": master, "Заказы": s["orders_count"], "Прибыль": s["total_profit"]} for master, s in stats.items()]
        df = pd.DataFrame(data)
        if not df.empty:
            df.loc[len(df)] = ["Итого", df["Заказы"].sum(), df["Прибыль"].sum()]
        return df
    async def get_orders_export_data(self, date_from: Optional[date] = None, date_to: Optional[date] = None) -> pd.DataFrame:
        """Полные данные для экспорта по заказам"""
        orders = await self.get_orders_report(date_from, date_to)
        data = []
        for o in orders:
            data.append({
                "Номер": o.number,
                "Дата": o.datetime.strftime("%Y-%m-%d"),
                "Клиент": o.client_name,
                "Прибыль": getattr(o, 'profit', 0),
                "Описание": getattr(o, 'work_description', None) or "Не указано",
                "Фото": len(getattr(o, 'work_photos', None) or [])
            })
        df = pd.DataFrame(data)
        if not df.empty:
            df.loc[len(df)] = ["Итого", "", "", df["Прибыль"].sum(), "", ""]
        return df
    async def get_all_export_data(self) -> Dict[str, pd.DataFrame]:
        """Полные данные для экспорта всего: заказы со статусами, мастера с навыками и итоговыми расчетами"""
        # Заказы со статусами
        all_orders = await self.order_repo.get_all()
        orders_data = []
        for order in all_orders:
            orders_data.append({
                "Номер": order.number,
                "Дата": order.datetime.strftime("%Y-%m-%d %H:%M"),
                "Клиент": order.client_name,
                "Статус": order.status.value,
                "Тип": order.type,
                "Бренд": order.brand,
                "Модель": order.model,
                "Выручка": getattr(order, 'work_amount', 0),
                "Расходы": getattr(order, 'expenses', 0),
                "Прибыль": getattr(order, 'profit', 0),
                "Описание работ": getattr(order, 'work_description', None) or "Не указано",
                "Кол-во фото": len(getattr(order, 'work_photos', None) or [])
            })
        orders_df = pd.DataFrame(orders_data)
        if not orders_df.empty:
            orders_df.loc[len(orders_df)] = [
                "Итого", "", "", "", "", "", "",
                orders_df["Выручка"].sum(),
                orders_df["Расходы"].sum(),
                orders_df["Прибыль"].sum(),
                "", ""
            ]
        # Мастера с навыками и итоговыми расчетами (прибыль/расходы по всем заказам)
        masters = await self.master_repo.get_all_with_skills()
        master_stats = {}
        for master in masters:
            assignments = await self.assignment_repo.get_by_master(master.id)
            total_profit = sum(getattr(a.order, 'profit', 0) for a in assignments if a.order and a.order.status == OrderStatus.completed)
            total_expenses = sum(getattr(a.order, 'expenses', 0) for a in assignments if a.order and a.order.status == OrderStatus.completed)
            total_revenue = sum(getattr(a.order, 'work_amount', 0) for a in assignments if a.order and a.order.status == OrderStatus.completed)
            orders_count = len([a for a in assignments if a.order and a.order.status == OrderStatus.completed])
           
            master_stats[master.name] = {
                "orders_count": orders_count,
                "total_revenue": total_revenue,
                "total_expenses": total_expenses,
                "total_profit": total_profit
            }
        masters_data = []
        for master in masters:
            stats = master_stats.get(master.name, {"orders_count": 0, "total_revenue": 0, "total_expenses": 0, "total_profit": 0})
            skills_list = ", ".join([skill.name for skill in master.skills]) if master.skills else "Нет навыков"
            masters_data.append({
                "Имя": master.name,
                "Telegram ID": master.telegram_id,
                "Телефон": master.phone or "Не указан",
                "Навыки": skills_list,
                "Заказов": stats["orders_count"],
                "Выручка": stats["total_revenue"],
                "Расходы": stats["total_expenses"],
                "Прибыль": stats["total_profit"]
            })
        masters_df = pd.DataFrame(masters_data)
        if not masters_df.empty:
            masters_df.loc[len(masters_df)] = [
                "Итого", "", "", "",
                masters_df["Заказов"].sum(),
                masters_df["Выручка"].sum(),
                masters_df["Расходы"].sum(),
                masters_df["Прибыль"].sum()
            ]
        return {
            "Заказы": orders_df,
            "Мастера": masters_df
        }