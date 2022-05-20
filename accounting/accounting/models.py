import enum
import datetime
import random
import uuid

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


class BillingCycleStatus(enum.Enum):
    open = 'open'
    closed = 'closed'


class BillingCycle(SQLModel, table=True):
    __tablename__ = 'billing_cycle'
    id: int | None = Field(primary_key=True)
    status = Field(default=BillingCycleStatus.open, sa_column=Column('status', Enum(BillingCycleStatus)))
    account_id: int = Field(foreign_key='account.id')
    opened_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    closed_at: datetime.datetime | None

    def close(self):
        self.status = BillingCycleStatus.closed
        self.closed_at = datetime.datetime.now()


class BillingTransaction(SQLModel, table=True):
    __tablename__ = 'billing_transaction'
    id: int | None = Field(primary_key=True)
    public_id: str = Field(default_factory=lambda: str(uuid.uuid4()), sa_column_kwargs={'unique': True})
    date: datetime.datetime = Field(default_factory=datetime.datetime.now)
    billing_cycle_id: int = Field(foreign_key='billing_cycle.id')
    debit: int
    credit: int


class TaskAssignment(SQLModel, table=True):
    __tablename__ = 'task_assignment'
    id: int | None = Field(primary_key=True)
    billing_transaction_id: int = Field(foreign_key='billing_transaction.id')
    task_id: int = Field(foreign_key='task.id')


class TaskClosing(SQLModel, table=True):
    __tablename__ = 'task_closing'
    id: int | None = Field(primary_key=True)
    billing_transaction_id: int = Field(foreign_key='billing_transaction.id')
    task_id: int = Field(foreign_key='task.id')


class PaymentStatus(enum.Enum):
    pending = 'pending'
    completed = 'completed'
    failed = 'failed'


class Payment(SQLModel, table=True):
    id: int | None = Field(primary_key=True)
    billing_transaction_id: int = Field(foreign_key='billing_transaction.id')
    status: PaymentStatus = Field(default=PaymentStatus.pending, sa_column=Column('status', Enum(PaymentStatus)))
