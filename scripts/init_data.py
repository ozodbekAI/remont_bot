"""
Скрипт для первоначального заполнения БД демо-данными.
Запуск: python scripts/init_data.py
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.engine import DatabaseManager
from database.base import BaseModel
from models import *  # Импорт моделей для регистрации в metadata
from services.services import SkillService, MasterService
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
        }
    ]
    
    created_skills = []
    for skill_data in skills_data:
        skill = await skill_service.create_skill(**skill_data)
        created_skills.append(skill)
        print(f"✅ Создан навык: {skill.name}")
    
    return created_skills


async def create_demo_masters(master_service: MasterService, skills, session):
    """Создать демо-мастеров"""
    masters_data = [
        {
            "name": "Иванов Иван",
            "telegram_id": 111111111,  # Замените на реальный ID
            "phone": "+998901234567",
            "skill_ids": [skills[0].id, skills[5].id]  # Стиралки + Универсал
        },
        {
            "name": "Петров Петр",
            "telegram_id": 222222222,  # Замените на реальный ID
            "phone": "+998901234568",
            "skill_ids": [skills[1].id, skills[2].id]  # Холодильники + Кондиционеры
        },
        {
            "name": "Сидоров Сидор",
            "telegram_id": 333333333,  # Замените на реальный ID
            "phone": "+998901234569",
            "skill_ids": [skills[5].id]  # Универсал
        }
    ]
    
    created_masters = []
    for master_data in masters_data:
        # Создаем мастера без навыков
        basic_data = {k: v for k, v in master_data.items() if k != "skill_ids"}
        master = await master_service.create_master(**basic_data)
        created_masters.append(master)
        
        # Добавляем связи с навыками напрямую в таблицу many-to-many
        skill_ids = master_data["skill_ids"]
        for sid in skill_ids:
            stmt = insert(master_skills).values(master_id=master.id, skill_id=sid)
            await session.execute(stmt)
        
        # Формируем имена навыков для вывода
        skill_names = ", ".join(s.name for s in skills if s.id in skill_ids)
        print(f"✅ Создан мастер: {master.name} (навыки: {skill_names})")
    
    return created_masters


async def main():
    print("🚀 Инициализация базы данных...\n")
    
    # Получаем engine
    engine = await factory.get_engine()
    
    metadata = BaseModel.metadata
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)
    print("✅ Схема БД пересоздана.\n")
    
    # Заполняем данными
    from database.engine import get_session
    async with get_session() as session:
        skill_service = SkillService(session)
        master_service = MasterService(session)
        
        print("\n📚 Создание навыков...")
        skills = await create_initial_skills(skill_service)
        
        # print("\n👥 Создание мастеров...")
        # masters = await create_demo_masters(master_service, skills, session)
        
        
        await session.commit()
        
        print(f"\n✅ Готово!")
        print(f"   Создано навыков: {len(skills)}")
        # print(f"   Создано мастеров: {len(masters)}")
        print("\n⚠️  ВАЖНО: Обновите Telegram ID мастеров в коде на реальные!")


if __name__ == "__main__":
    asyncio.run(main())