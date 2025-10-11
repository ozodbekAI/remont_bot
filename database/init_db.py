import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from database.engine import create_engine, get_session
from models.skill import Skill
from models.master import Master
from models.base import BaseModel  # Для save

async def init():
    """Инициализация БД с примерами данных"""
    engine = await create_engine()  # Создаст таблицы
    async for session in get_session(engine):
        # Добавляем навыки
        skill_stiral = Skill(name="Стиральные машины", description="Ремонт стиралок")
        skill_holod = Skill(name="Холодильники", description="Ремонт холодильников")
        skill_uni = Skill(name="Универсал", description="Всё умеет")
        
        await BaseModel.save(skill_stiral, session)
        await BaseModel.save(skill_holod, session)
        await BaseModel.save(skill_uni, session)
        
        # Добавляем мастера
        master1 = Master(name="Иванов Иван", telegram_id=123456789)
        master1.skills = [skill_stiral, skill_uni]  # Связь
        await BaseModel.save(master1, session)
        
        print("✅ БД готова! Навыки и мастер добавлены. Проверь в pgAdmin/psql.")

if __name__ == "__main__":
    asyncio.run(init())