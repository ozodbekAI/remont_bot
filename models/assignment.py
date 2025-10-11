from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, select
from sqlalchemy.orm import relationship
from models.base import BaseModel

class Assignment(BaseModel):
    __tablename__ = "assignments"
    
    order_id = Column(Integer, ForeignKey("orders.id"))
    master_id = Column(Integer, ForeignKey("masters.id"))
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
    order = relationship("Order", back_populates="assignments")
    master = relationship("Master", back_populates="assignments")
    
    @classmethod
    async def get_by_master(cls, master_id, session):
        return await session.execute(select(cls).where(cls.master_id == master_id))