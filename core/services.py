from datetime import datetime
from sqlalchemy import and_, func
from models.order import Order
from models.master import Master
from models.assignment import Assignment
from models.skill import Skill
from core.utils import generate_order_number

async def assign_order(order: Order) -> Master:
    """Автоматическое распределение: по навыку и свободному времени"""
    # Находим мастера по типу техники (навык)
    skill = await Skill.get_by_name(order.type)
    if not skill:
        return None  # Нет навыка – админ уведомлен
    
    masters = await Master.get_by_skill(skill.id)
    for master in masters:
        # Проверяем график (динамический: занят ли в это время?)
        if not await master.is_free(order.datetime):
            continue
        # Назначаем
        assignment = Assignment(order_id=order.id, master_id=master.id)
        await assignment.save()
        await master.update_schedule(order.datetime, "busy")  # Занимаем слот
        return master
    return None  # Никто не свободен

async def get_report(date_from: datetime, date_to: datetime) -> dict:
    """Отчет: прибыль, кол-во и т.д."""
    orders = await Order.filter(and_(Order.created_at >= date_from, Order.created_at <= date_to, Order.status == "completed"))
    total_profit = sum(o.profit for o in orders)
    return {"orders_count": len(orders), "total_profit": total_profit}

async def update_master_schedule(master_id: int, datetime_obj: datetime, status: str):
    """Обновление графика при статусе (busy/free)"""
    master = await Master.get(master_id)
    if not master.schedule:
        master.schedule = {}
    date_str = datetime_obj.strftime("%Y-%m-%d")
    if date_str not in master.schedule:
        master.schedule[date_str] = []
    if status == "busy" and str(datetime_obj.time()) not in master.schedule[date_str]:
        master.schedule[date_str].append(str(datetime_obj.time()))
    elif status == "free":
        if str(datetime_obj.time()) in master.schedule[date_str]:
            master.schedule[date_str].remove(str(datetime_obj.time()))
    await master.save()