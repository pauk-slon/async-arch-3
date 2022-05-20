import enum

from sqlmodel import Field, Column, SQLModel, Enum


class AccountRole(enum.Enum):
    admin = 'admin'
    worker = 'worker'
    manager = 'manager'


class Account(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(sa_column_kwargs={'unique': True})
    email: str = Field(default='')
    full_name: str = Field(default='')
    role: AccountRole | None = Field(sa_column=Column('role', Enum(AccountRole)))
    balance: int = Field(default=0)
