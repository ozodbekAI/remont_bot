from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine,
    async_sessionmaker
)
from config import DB_URL
from database.base import Base


class DatabaseManager:
    """
    Менеджер БД (Singleton).
    Принцип: Single Responsibility - управление соединением.
    """
    _engine: AsyncEngine = None
    _session_factory: async_sessionmaker = None
    
    @classmethod
    async def get_engine(cls) -> AsyncEngine:
        """Получить engine (создается один раз)"""
        if cls._engine is None:
            cls._engine = create_async_engine(
                DB_URL,
                echo=False,  # True для debug
                pool_pre_ping=True,
                pool_size=20,
                max_overflow=10
            )
        return cls._engine
    
    @classmethod
    async def get_session_factory(cls) -> async_sessionmaker:
        """Получить фабрику сессий"""
        if cls._session_factory is None:
            engine = await cls.get_engine()
            cls._session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False
            )
        return cls._session_factory
    
    @classmethod
    async def create_tables(cls):
        """Создать все таблицы"""
        engine = await cls.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    @classmethod
    async def drop_tables(cls):
        """Удалить все таблицы (для тестов)"""
        engine = await cls.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    @classmethod
    async def close(cls):
        """Закрыть соединение"""
        if cls._engine:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Контекстный менеджер для сессии.
    Автоматический commit/rollback.
    
    Usage:
        async with get_session() as session:
            await service.do_something(session)
    """
    factory = await DatabaseManager.get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Инициализация БД (для startup)"""
    await DatabaseManager.create_tables()
    print("✅ База данных инициализирована")