import random
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette import status as statuses
from sqlalchemy import select, asc
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from task_tracker.models import Account, AccountRole, Task, TaskStatus
from task_tracker.web_server.dependences import get_session, get_current_account

router = APIRouter(
    prefix='/tasks',
    tags=['tasks'],
    responses={statuses.HTTP_404_NOT_FOUND: {'description': "Not Found"}},
)


class TaskWrite(BaseModel):
    description: str


@router.get('/', response_model=List[Task])
async def list_tasks(
    status: TaskStatus | None = None,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(get_current_account),
):
    if account.role not in {AccountRole.manager, AccountRole.admin}:
        raise HTTPException(statuses.HTTP_403_FORBIDDEN)
    query = select(Task)
    if status:
        query = query.where(Task.status == status)
    return (await session.execute(query.order_by(asc(Task.id)))).scalars().all()


@router.get('/{task_id}', response_model=Task)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(get_current_account),
):
    if account.role not in {AccountRole.manager, AccountRole.admin}:
        raise HTTPException(statuses.HTTP_403_FORBIDDEN)
    result = await session.execute(select(Task).where(Task.id == task_id))
    try:
        return result.one()
    except NoResultFound:
        raise HTTPException(statuses.HTTP_404_NOT_FOUND)


@router.patch('/{task_id}', response_model=Task)
async def update_task(
    task_id: int,
    task_write: TaskWrite,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(get_current_account),
):
    if account.role not in {AccountRole.manager, AccountRole.admin}:
        raise HTTPException(statuses.HTTP_403_FORBIDDEN)
    task_result = await session.execute(select(Task).where(Task.id == task_id))
    try:
        task = task_result.scalars().one()
    except NoResultFound:
        raise HTTPException(statuses.HTTP_404_NOT_FOUND)
    task_data = task_write.dict(exclude_unset=True)
    for key, value in task_data.items():
        setattr(task, key, value)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.get('/my/', response_model=List[Task])
async def list_my_tasks(
    status: TaskStatus | None = None,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(get_current_account),
):
    query = select(Task).where(Task.assignee_id == account.id)
    if status:
        query = query.where(Task.status == status)
    return (await session.execute(query)).scalars().all()


@router.get('/my/{task_id}', response_model=Task)
async def get_my_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(get_current_account),
):
    result = await session.execute(
        select(Task).where(
            Task.assignee_id == account.id,
            Task.id == task_id,
        )
    )
    try:
        return result.scalars().one()
    except NoResultFound:
        raise HTTPException(statuses.HTTP_404_NOT_FOUND)


@router.post('/my/{task_id}/close', response_model=Task)
async def close_my_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(get_current_account),
):
    task_result = await session.execute(
        select(Task).where(
            Task.assignee_id == account.id,
            Task.id == task_id,
        )
    )
    try:
        task: Task = task_result.scalars().one()
    except NoResultFound:
        raise HTTPException(statuses.HTTP_404_NOT_FOUND)
    if task.is_closed():
        raise HTTPException(statuses.HTTP_400_BAD_REQUEST, detail="Task already closed.")
    task.close()
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.post('/my/{task_id}/reopen', response_model=Task)
async def reopen_my_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(get_current_account),
):
    task_result = await session.execute(
        select(Task).where(
            Task.assignee_id == account.id,
            Task.id == task_id,
        )
    )
    try:
        task: Task = task_result.scalars().one()
    except NoResultFound:
        raise HTTPException(statuses.HTTP_404_NOT_FOUND)
    if not task.is_closed():
        raise HTTPException(statuses.HTTP_400_BAD_REQUEST, detail="Task should be closed.")
    task.reopen()
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.post('/', response_model=Task)
async def create_task(
    task_write: TaskWrite,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(get_current_account),
):
    workers: List[Account] = (await session.execute(
        select(Account).where(Account.role == AccountRole.worker)
    )).scalars().all()
    if not workers:
        raise HTTPException(
            statuses.HTTP_400_BAD_REQUEST,
            detail="There is no any worker assign the task to.",
        )
    assignee: Account = random.choice(workers)
    task = Task(
        description=task_write.description,
        reporter_id=account.id,
        assignee_id=assignee.id,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.post('/shuffle')
async def shuffle_tasks(
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(get_current_account),
):
    if account.role not in {AccountRole.manager, AccountRole.admin}:
        raise HTTPException(statuses.HTTP_403_FORBIDDEN)
    workers: List[Account] = (await session.execute(
        select(Account).where(Account.role == AccountRole.worker)
    )).scalars().all()
    if not workers:
        raise HTTPException(
            statuses.HTTP_400_BAD_REQUEST,
            detail="There is no any worker, the action cannot be performed.",
        )
    open_tasks: List[Task] = (await session.execute(
        select(Task).where(Task.status == TaskStatus.open).order_by(asc(Task.id))
    )).scalars().all()
    result = []
    for task in open_tasks:
        new_assignee = random.choice(workers)
        result.append((task.id, task.assignee_id, new_assignee.id))
        task.assign(new_assignee)
        session.add(task)
    await session.commit()
    return result
