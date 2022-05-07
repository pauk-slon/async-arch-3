from pydantic import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

engine: AsyncEngine | None = None


class Settings(BaseSettings):
    url: str

    class Config:
        env_prefix = 'database_'


def create_session() -> AsyncSession:
    return sessionmaker(engine, AsyncSession, expire_on_commit=False)()


async def setup(settings: Settings):
    global engine
    engine = create_async_engine(settings.url, echo=True)
    from task_tracker import models  # noqa
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
