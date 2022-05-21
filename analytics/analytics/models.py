import datetime
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


class BillingTransactionType(enum.Enum):
    task_assignment = 'task_assignment'
    task_closing = 'task_closing'
    payment = 'payment'


class BillingTransaction(SQLModel, table=True):
    __tablename__ = 'billing_transaction'
    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(sa_column_kwargs={'unique': True})
    date: datetime.datetime
    business_day: datetime.date = Field(index=True)
    account_id: int = Field(foreign_key='account.id')
    type: BillingTransactionType = Field(sa_column=Column('type', Enum(BillingTransactionType)))
    debit: int
    credit: int
    task_id: int | None = Field(foreign_key='task.id', nullable=True)
