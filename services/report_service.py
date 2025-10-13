from typing import Optional, Dict, List
from datetime import date
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from models import Order, OrderStatus
from repositories.order import OrderRepository
from repositories.assignment import AssignmentRepository
from repositories.master import MasterRepository


class ReportService:
    """Сервис для генерации отчетов"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.assignment_repo = AssignmentRepository(session)
        self.master_repo = MasterRepository(session)
    
    async def get_financial_report(
        self, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None
    ) -> Dict:
        """Финансовый отчет"""
        if date_from is None and date_to is None:
            orders = await self.order_repo.get_by_status(OrderStatus.completed)
        else:
            orders = await self.order_repo.get_by_date_range(
                date_from, date_to, OrderStatus.completed
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
    
    async def get_masters_report(
        self, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None
    ) -> Dict[str, Dict]:
        """Отчет по мастерам"""
        if date_from is None and date_to is None:
            assignments = await self.assignment_repo.get_all_assignments()
        else:
            assignments = await self.assignment_repo.get_by_date_range(date_from, date_to)
        
        stats = {}
        for assignment in assignments:
            if assignment.order and assignment.order.status == OrderStatus.completed:
                master_name = assignment.master.name
                if master_name not in stats:
                    stats[master_name] = {"orders_count": 0, "total_profit": 0.0}
                stats[master_name]["orders_count"] += 1
                stats[master_name]["total_profit"] += getattr(assignment.order, 'profit', 0)
        
        return stats
    
    async def get_orders_report(
        self, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None
    ) -> List[Order]:
        """Список заказов"""
        if date_from is None and date_to is None:
            return await self.order_repo.get_by_status(OrderStatus.completed)
        else:
            return await self.order_repo.get_by_date_range(
                date_from, date_to, OrderStatus.completed
            )
    
    async def get_financial_export_data(
        self, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None
    ) -> pd.DataFrame:
        """Данные для экспорта финансового отчета"""
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
    
    async def get_masters_export_data(
        self, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None
    ) -> pd.DataFrame:
        """Данные для экспорта отчета по мастерам"""
        stats = await self.get_masters_report(date_from, date_to)
        data = [
            {
                "Мастер": master, 
                "Заказы": s["orders_count"], 
                "Прибыль": s["total_profit"]
            } 
            for master, s in stats.items()
        ]
        
        df = pd.DataFrame(data)
        if not df.empty:
            df.loc[len(df)] = ["Итого", df["Заказы"].sum(), df["Прибыль"].sum()]
        return df
    
    async def get_orders_export_data(
        self, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None
    ) -> pd.DataFrame:
        """Данные для экспорта списка заказов"""
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
        """Полный экспорт всех данных"""
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
        
        # Мастера с навыками
        masters = await self.master_repo.get_all_with_skills()
        master_stats = {}
        
        for master in masters:
            assignments = await self.assignment_repo.get_by_master(master.id)
            total_profit = sum(
                getattr(a.order, 'profit', 0) 
                for a in assignments 
                if a.order and a.order.status == OrderStatus.completed
            )
            total_expenses = sum(
                getattr(a.order, 'expenses', 0) 
                for a in assignments 
                if a.order and a.order.status == OrderStatus.completed
            )
            total_revenue = sum(
                getattr(a.order, 'work_amount', 0) 
                for a in assignments 
                if a.order and a.order.status == OrderStatus.completed
            )
            orders_count = len([
                a for a in assignments 
                if a.order and a.order.status == OrderStatus.completed
            ])
            
            master_stats[master.name] = {
                "orders_count": orders_count,
                "total_revenue": total_revenue,
                "total_expenses": total_expenses,
                "total_profit": total_profit
            }
        
        masters_data = []
        for master in masters:
            stats = master_stats.get(master.name, {
                "orders_count": 0, 
                "total_revenue": 0, 
                "total_expenses": 0, 
                "total_profit": 0
            })
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