from typing import List
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Text, select
from sqlalchemy.orm import relationship
from models.base import BaseModel

master_skills = Table(
    "master_skills",
    BaseModel.metadata,
    Column("master_id", Integer, ForeignKey("masters.id")),
    Column("skill_id", Integer, ForeignKey("skills.id"))
)

class Skill(BaseModel):
    __tablename__ = "skills"
    
    name = Column(String, unique=True)
    description = Column(Text, nullable=True)
    
    masters = relationship("Master", secondary=master_skills, back_populates="skills", lazy="selectin")
    
    @classmethod
    async def get_by_name(cls, name: str, session):
        result = await session.execute(select(cls).where(cls.name == name))
        return result.scalar_one_or_none()
    
    @classmethod
    async def all(cls, session):
        return await cls.all(session)
    
    @classmethod
    async def get_multiple(cls, ids: List[int], session):
        result = await session.execute(select(cls).where(cls.id.in_(ids)))
        return result.scalars().all()