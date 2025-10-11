from sqlalchemy import Column, String, DateTime, Float, Enum as SQLEnum, select
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from models.base import BaseModel

class OrderStatus(PyEnum):
    new = "new"
    confirmed = "confirmed"
    in_progress = "in_progress"
    arrived = "arrived"
    completed = "completed"

class Order(BaseModel):
    __tablename__ = "orders"
    
    number = Column(String, unique=True)
    client_name = Column(String)
    phone = Column(String)
    address = Column(String)
    datetime = Column(DateTime)
    type = Column(String)  # Тип техники
    brand = Column(String)
    model = Column(String)
    comment = Column(String)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.new)
    work_amount = Column(Float, default=0.0)
    expenses = Column(Float, default=0.0)
    profit = Column(Float, default=0.0)
    
    assignments = relationship("Assignment", back_populates="order")
    
    @classmethod
    async def filter_by_status(cls, status, session):
        return await session.execute(select(cls).where(cls.status == status))
    
    async def update_profit(self, session):
        self.profit = self.work_amount - self.expenses
        await self.save(session)