from sqlalchemy import Column, Integer, String, DateTime, Float, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import select
from datetime import datetime
from typing import Optional, List

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    @classmethod
    async def save(cls, obj: 'BaseModel', session):
        """Сохранить объект"""
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    @classmethod
    async def get(cls, ident: int, session) -> Optional['BaseModel']:
        result = await session.get(cls, ident)
        return result

    @classmethod
    async def all(cls, session) -> List['BaseModel']:
        result = await session.execute(select(cls))
        return result.scalars().all()

    @classmethod
    async def filter(cls, *args, session) -> List['BaseModel']:
        stmt = select(cls)
        for arg in args:
            stmt = stmt.where(arg)
        result = await session.execute(stmt)
        return result.scalars().all()
