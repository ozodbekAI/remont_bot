from sqlalchemy import Column, Integer, String, Boolean, JSON, BigInteger  # ← + BigInteger!
from sqlalchemy.orm import relationship
from sqlalchemy import select  # Для get_by_telegram_id
from models.base import BaseModel
from models.skill import master_skills
from sqlalchemy.dialects.postgresql import JSONB

class Master(BaseModel):
    __tablename__ = "masters"
    
    name = Column(String)
    telegram_id = Column(BigInteger, unique=True)  
    schedule = Column(JSONB, default=dict) 
    is_online = Column(Boolean, default=False)
    phone = Column(String)
    skills = relationship("Skill", secondary=master_skills, back_populates="masters", lazy="selectin")
    assignments = relationship("Assignment", back_populates="master")
    
    @classmethod
    async def get_by_telegram_id(cls, tg_id: int, session):
        result = await session.execute(select(cls).where(cls.telegram_id == tg_id))
        return result.scalar_one_or_none() 
    
    @classmethod
    async def get_by_skill(cls, skill_id: int, session):
        result = await session.execute(
            select(cls).join(master_skills).where(master_skills.c.skill_id == skill_id)
        )
        return result.scalars().all()
    
    async def is_free(self, dt, session):
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
        if date_str in self.schedule and time_str in self.schedule[date_str]:
            return False
        return True
    
    async def update_schedule(self, dt, status: str, session):
        if not self.schedule:
            self.schedule = {}
        date_str = dt.strftime("%Y-%m-%d")
        if date_str not in self.schedule:
            self.schedule[date_str] = []
        time_str = dt.strftime("%H:%M")
        if status == "busy" and time_str not in self.schedule[date_str]:
            self.schedule[date_str].append(time_str)
        elif status == "free" and time_str in self.schedule[date_str]:
            self.schedule[date_str].remove(time_str)
        await BaseModel.save(self, session) 