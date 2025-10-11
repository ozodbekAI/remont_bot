from sqlalchemy import Column, String, DateTime, Float, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from models.base import BaseModel

class OrderStatus(PyEnum):
    new = "new"
    confirmed = "confirmed"
    in_progress = "in_progress"
    arrived = "arrived"
    completed = "completed"
    rejected = "rejected"

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
    
    # Финансы
    work_amount = Column(Float, default=0.0)
    expenses = Column(Float, default=0.0)
    profit = Column(Float, default=0.0)
    
    # Описание работ и фото
    work_description = Column(Text, nullable=True)
    work_photos = Column(JSON, nullable=True)  # List[str] - file_ids
    
    assignments = relationship("Assignment", back_populates="order")
    required_skills = relationship("Skill", secondary="order_skills", back_populates="orders")
    
    def calculate_profit(self):
        """Рассчитать прибыль"""
        self.profit = (self.work_amount or 0) - (self.expenses or 0)