from typing import TypeVar, Generic, Type, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime
from datetime import datetime

Base = declarative_base()

T = TypeVar('T', bound='BaseModel')


class BaseModel(Base):
    """Базовая модель с общими полями"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # updated_at ni olib tashladik - eski jadvallar bilan muammo kelmasligi uchun


class BaseRepository(Generic[T]):
    """
    Generic Repository для CRUD операций.
    Принцип: Single Responsibility - только работа с БД.
    """
    
    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session
    
    async def create(self, **kwargs) -> T:
        """Создать запись"""
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
    
    async def get(self, id: int) -> Optional[T]:
        """Получить по ID"""
        return await self.session.get(self.model, id)
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Все записи с пагинацией"""
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
    
    async def filter_by(self, **filters) -> List[T]:
        """Фильтр по условиям"""
        query = select(self.model)
        conditions = [getattr(self.model, k) == v for k, v in filters.items()]
        if conditions:
            query = query.where(and_(*conditions))
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update(self, id: int, **kwargs) -> Optional[T]:
        """Обновить запись"""
        obj = await self.get(id)
        if not obj:
            return None
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
    
    async def delete(self, id: int) -> bool:
        """Удалить запись"""
        obj = await self.get(id)
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True
    
    async def exists(self, **filters) -> bool:
        """Проверка существования"""
        items = await self.filter_by(**filters)
        return len(items) > 0
    
    async def count(self, **filters) -> int:
        """Подсчет записей"""
        items = await self.filter_by(**filters)
        return len(items)