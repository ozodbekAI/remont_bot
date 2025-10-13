from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.base import BaseRepository
from models import Skill


class SkillRepository(BaseRepository[Skill]):
    """Repository для работы с навыками"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Skill, session)
    
    async def get_by_ids(self, skill_ids: List[int]) -> List[Skill]:
        """Получить навыки по списку ID"""
        result = await self.session.execute(
            select(Skill).where(Skill.id.in_(skill_ids))
        )
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Optional[Skill]:
        """Получить навык по названию"""
        result = await self.session.execute(
            select(Skill).where(Skill.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_multiple_by_ids(self, ids: List[int]) -> List[Skill]:
        """Получить несколько навыков по ID"""
        result = await self.session.execute(
            select(Skill).where(Skill.id.in_(ids))
        )
        return list(result.scalars().all())