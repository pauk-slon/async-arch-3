import enum
import uuid

from sqlmodel import Field, Column, SQLModel, Enum, Relationship


class AccountRole(enum.Enum):
    admin = 'admin'
    worker = 'worker'
    manager = 'manager'


class Account(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(sa_column_kwargs={'unique': True})
    email: str = Field(sa_column_kwargs={'unique': True})
    full_name: str
    role: AccountRole | None = Field(sa_column=Column('role', Enum(AccountRole)))


class TaskStatus(enum.Enum):
    open = 'open'
    closed = 'closed'


class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(default_factory=lambda: str(uuid.uuid4()), sa_column_kwargs={'unique': True})
    status: TaskStatus = Field(default=TaskStatus.open, sa_column=Column('status', Enum(TaskStatus)))
    description: str
    reporter_id: int = Field(foreign_key='account.id')
    reporter: Account | None = Relationship(back_populates='reported_tasks')
    assignee_id: int = Field(foreign_key='account.id')
    assignee: Account | None = Relationship(back_populates='assigned_tasks')

    def close(self):
        self.status = TaskStatus.closed

    def reopen(self):
        self.status = TaskStatus.open

    def is_closed(self) -> bool:
        return self.status == TaskStatus.closed

    def assign(self, account: Account):
        assert not self.is_closed(), 'Closed task cannot be assigned.'
        assert account.role == AccountRole.worker, 'Task can be assigned to a worker only.'
        self.assignee_id = account.id
