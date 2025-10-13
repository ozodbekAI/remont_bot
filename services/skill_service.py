from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from models import Skill
from repositories.skill import SkillRepository


class SkillService:
    """Сервис для работы с навыками"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.skill_repo = SkillRepository(session)
    
    async def create_skill(self, name: str, description: str = None) -> Skill:
        """Создать навык"""
        return await self.skill_repo.create(
            name=name,
            description=description
        )
    
    async def get_all_skills(self) -> List[Skill]:
        """Получить все навыки"""
        return await self.skill_repo.get_all()
    
    async def get_skill_by_name(self, name: str) -> Skill:
        """Получить навык по имени"""
        return await self.skill_repo.get_by_name(name)