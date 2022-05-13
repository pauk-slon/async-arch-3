import enum
import datetime
import random

from sqlmodel import Field, Column, SQLModel, Enum, UniqueConstraint


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


class BillingCycleStatus(enum.Enum):
    open = 'open'
    closed = 'closed'


class BillingCycle(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint('business_day', 'account_id', name='unique_business_day_account'),
    )
    __tablename__ = 'billing_cycle'
    id: int | None = Field(primary_key=True)
    status = Field(default=BillingCycleStatus.open, sa_column=Column('status', Enum(BillingCycleStatus)))
    business_day: datetime.date = Field(default_factory=datetime.date.today)
    account_id: int = Field(foreign_key='account.id')
    opened_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    closed_at: datetime.datetime | None


class Transaction(SQLModel, table=True):
    id: int | None = Field(primary_key=True)
    date: datetime.datetime = Field(default_factory=datetime.datetime.now)
    billing_cycle_id: int = Field(foreign_key='billing_cycle.id')
    debit: int
    credit: int


class TaskAssignment(SQLModel, table=True):
    __tablename__ = 'task_assignment'
    id: int | None = Field(primary_key=True)
    transaction_id: int = Field(foreign_key='transaction.id')
    task_id: int = Field(foreign_key='task.id')


class TaskClosing(SQLModel, table=True):
    __tablename__ = 'task_closing'
    id: int | None = Field(primary_key=True)
    transaction_id: int = Field(foreign_key='transaction.id')
    task_id: int = Field(foreign_key='task.id')


class PaymentStatus(enum.Enum):
    pending = 'pending'
    completed = 'completed'
    failed = 'failed'


class Payment(SQLModel, table=True):
    id: int | None = Field(primary_key=True)
    transaction_id: int = Field(foreign_key='transaction.id')
    status: PaymentStatus = Field(default=PaymentStatus.pending, sa_column=Column('status', Enum(PaymentStatus)))
