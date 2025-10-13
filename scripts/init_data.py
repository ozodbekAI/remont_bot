"""
Скрипт для первоначального заполнения БД демо-данными.
Запуск: python scripts/init_data.py
"""
import asyncio
import sys
from pathlib import Path

from services import master_service

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.engine import DatabaseManager, get_session
from database.base import BaseModel
from models import *
from services.skill_service import SkillService
from services.master_service import MasterService
from sqlalchemy import insert

factory = DatabaseManager()

async def create_initial_skills(skill_service: SkillService):
    """Создать начальные навыки"""
    skills_data = [
        {
            "name": "Стиральные машины",
            "description": "Ремонт стиральных машин всех марок"
        },
        {
            "name": "Холодильники",
            "description": "Ремонт и обслуживание холодильников"
        },
        {
            "name": "Кондиционеры",
            "description": "Установка, ремонт и обслуживание кондиционеров"
        },
        {
            "name": "Посудомоечные машины",
            "description": "Ремонт посудомоечных машин"
        },
        {
            "name": "Микроволновки",
            "description": "Ремонт микроволновых печей"
        },
        {
            "name": "Универсал",
            "description": "Ремонт любой бытовой техники"
        },
        {
            "name": "Варочная панель",
            "description": "Ремонт варочных панелей"
        },
        {
            "name": "Духовой шкаф",
            "description": "Ремонт духовых шкафов"
        }
    ]
    
    created_skills = []
    for skill_data in skills_data:
        skill = await skill_service.create_skill(**skill_data)
        created_skills.append(skill)
        print(f"✅ Создан навык: {skill.name}")
    
    return created_skills


async def create_demo_masters(skills, session):
    """Создать демо-мастеров"""
    from models import Master
    
    # Создаем словарь для быстрого поиска навыков по имени
    skill_map = {skill.name: skill.id for skill in skills}
    
    masters_data = [
        {
            "name": "Рустам 50/50",
            "telegram_id": 7388574158,
            "phone": "+998901234567",
            "skill_names": ["Стиральные машины", "Посудомоечные машины", "Варочная панель"]
        },
        {
            "name": "Данила",
            "telegram_id": 1066527048,
            "phone": "+998901234568",
            "skill_names": ["Стиральные машины"]
        },
        {
            "name": "Эдуард",
            "telegram_id": 1727377979,
            "phone": "+998901234569",
            "skill_names": ["Стиральные машины"]
        },
        {
            "name": "Платонов Александр",
            "telegram_id": 5041337189,
            "phone": "+998901234570",
            "skill_names": ["Посудомоечные машины", "Стиральные машины"]
        },
        {
            "name": "Александр Парфенов",
            "telegram_id": 5361679073,
            "phone": "+998901234571",
            "skill_names": ["Стиральные машины", "Посудомоечные машины"]
        },
        {
            "name": "Александр (САНЧИЗ)",
            "telegram_id": 704381585,
            "phone": "+998901234572",
            "skill_names": ["Универсал", "Стиральные машины", "Холодильники", "Кондиционеры", 
                           "Посудомоечные машины", "Микроволновки", "Варочная панель", "Духовой шкаф"]
        },
        {
            "name": "Конухов Максим",
            "telegram_id": 777332150,
            "phone": "+998901234573",
            "skill_names": ["Стиральные машины", "Посудомоечные машины", "Варочная панель", 
                           "Духовой шкаф", "Микроволновки"]
        },
        {
            "name": "Лазарев Григорий Сергеевич",
            "telegram_id": 2143023737,
            "phone": "+998901234574",
            "skill_names": ["Стиральные машины", "Холодильники", "Кондиционеры", "Посудомоечные машины", 
                           "Микроволновки", "Универсал", "Варочная панель", "Духовой шкаф"]
        },
        {
            "name": "Даниил Рыскаль",
            "telegram_id": 1846886236,
            "phone": "+998901234575",
            "skill_names": ["Стиральные машины", "Холодильники", "Кондиционеры", "Посудомоечные машины", 
                           "Универсал", "Варочная панель", "Микроволновки", "Духовой шкаф"]
        },
        {
            "name": "Поздняков Павел",
            "telegram_id": 5180625824,
            "phone": "+998901234576",
            "skill_names": ["Духовой шкаф", "Варочная панель", "Стиральные машины", 
                           "Посудомоечные машины", "Микроволновки"]
        },
        {
            "name": "Деянышев Максим",
            "telegram_id": 580804505,
            "phone": "+998901234577",
            "skill_names": ["Стиральные машины", "Посудомоечные машины"]
        },
        {
            "name": "Алексеев Сергей",
            "telegram_id": 5428559076,
            "phone": "+998901234578",
            "skill_names": ["Стиральные машины"]
        }
    ]
    
    created_masters = []
    for master_data in masters_data:
        # Создаем мастера без навыков
        basic_data = {
            "name": master_data["name"],
            "telegram_id": master_data["telegram_id"],
            "phone": master_data["phone"]
        }
        master = await master_service.create_master(**basic_data)
        created_masters.append(master)
        
        # Добавляем связи с навыками
        skill_ids = [skill_map[name] for name in master_data["skill_names"] if name in skill_map]
        for sid in skill_ids:
            stmt = insert(master_skills).values(master_id=master.id, skill_id=sid)
            await session.execute(stmt)
        
        # Формируем имена навыков для вывода
        skill_names_str = ", ".join(master_data["skill_names"])
        print(f"✅ Создан мастер: {master.name} (навыки: {skill_names_str})")
    
    return created_masters


async def main():
    print("🚀 Инициализация базы данных...\n")
    
    # Получаем engine
    engine = await factory.get_engine()
    
    # Пересоздаем схему БД
    metadata = BaseModel.metadata
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)
    print("✅ Схема БД пересоздана.\n")
    
    # Заполняем данными
    async with get_session() as session:
        skill_service = SkillService(session)
        master_service = MasterService(session)
        
        print("📚 Создание навыков...")
        skills = await create_initial_skills(skill_service)
        
        print("\n👥 Создание мастеров...")
        masters = await create_demo_masters(master_service, skills, session)
        
        await session.commit()
        
        print(f"\n✅ Готово!")
        print(f"   Создано навыков: {len(skills)}")
        print(f"   Создано мастеров: {len(masters)}")


if __name__ == "__main__":
    asyncio.run(main())