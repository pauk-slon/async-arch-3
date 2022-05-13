import enum
import random

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


class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(sa_column_kwargs={'unique': True})
    description: str = Field(default='')
    assignment_cost: int | None = Field(
        default=None,
        description="Amount of money that will be deducted from the account in cents.",
    )
    closing_cost: int | None = Field(
        default=None,
        description="Amount of money that will be assessed to the account in cents.",
    )

    def price(self):
        if self.assignment_cost is None:
            self.assignment_cost = random.randint(1000, 2000)
        if self.closing_cost is None:
            self.closing_cost = random.randint(2000, 4000)

    @property
    def is_not_priced(self) -> bool:
        return self.assignment_cost is None or self.closing_cost is None
