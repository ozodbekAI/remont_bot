from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Text, 
    Boolean, JSON, BigInteger, ForeignKey, Table, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from database.base import BaseModel


# ==================== ENUMS ====================
class OrderStatus(PyEnum):
    """Статусы заявки"""
    new = "new"
    confirmed = "confirmed"
    in_progress = "in_progress"
    arrived = "arrived"
    completed = "completed"
    rejected = "rejected"


# ==================== MANY-TO-MANY TABLES ====================
master_skills = Table(
    "master_skills",
    BaseModel.metadata,
    Column("master_id", Integer, ForeignKey("masters.id", ondelete="CASCADE")),
    Column("skill_id", Integer, ForeignKey("skills.id", ondelete="CASCADE"))
)

order_skills = Table(
    "order_skills",
    BaseModel.metadata,
    Column("order_id", Integer, ForeignKey("orders.id", ondelete="CASCADE")),
    Column("skill_id", Integer, ForeignKey("skills.id", ondelete="CASCADE"))
)


# ==================== MODELS ====================
class Skill(BaseModel):
    """Навык/компетенция мастера"""
    __tablename__ = "skills"
    
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text)
    
    # Relationships
    masters = relationship("Master", secondary=master_skills, back_populates="skills")
    orders = relationship("Order", secondary=order_skills, back_populates="required_skills")
    
    def __repr__(self):
        return f"<Skill(name={self.name})>"


class Master(BaseModel):
    """Мастер с навыками и графиком"""
    __tablename__ = "masters"
    
    name = Column(String, nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    phone = Column(String)
    is_online = Column(Boolean, default=False)
    schedule = Column(JSON, default=dict)  # {"2025-10-11": ["13:00", "15:00"]}
    
    # Relationships
    skills = relationship("Skill", secondary=master_skills, back_populates="masters")
    assignments = relationship("Assignment", back_populates="master", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Master(name={self.name}, telegram_id={self.telegram_id})>"


class Order(BaseModel):
    """Заявка/заказ"""
    __tablename__ = "orders"
    
    number = Column(String, unique=True, nullable=False, index=True)
    
    # Клиент
    client_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    address = Column(String, nullable=False)
    
    # Время и техника
    datetime = Column(DateTime, nullable=False, index=True)
    type = Column(String)  # Тип техники (стиралка, холодильник)
    brand = Column(String)
    model = Column(String)
    comment = Column(Text)
    
    # Статус и финансы
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.new, index=True)
    work_amount = Column(Float, default=0.0)
    expenses = Column(Float, default=0.0)
    profit = Column(Float, default=0.0)
    
    # Relationships
    required_skills = relationship("Skill", secondary=order_skills, back_populates="orders")
    assignments = relationship("Assignment", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order(number={self.number}, status={self.status.value})>"
    
    def calculate_profit(self):
        """Вычислить прибыль"""
        self.profit = self.work_amount - self.expenses


class Assignment(BaseModel):
    """Назначение заказа мастеру"""
    __tablename__ = "assignments"
    
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    master_id = Column(Integer, ForeignKey("masters.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    order = relationship("Order", back_populates="assignments")
    master = relationship("Master", back_populates="assignments")
    
    def __repr__(self):
        return f"<Assignment(order_id={self.order_id}, master_id={self.master_id})>"


# Экспорт всех моделей
__all__ = [
    'OrderStatus',
    'Skill',
    'Master',
    'Order',
    'Assignment',
    'master_skills',
    'order_skills'
]