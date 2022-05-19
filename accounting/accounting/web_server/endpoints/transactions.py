import datetime
import enum
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from starlette import status as statuses
from sqlalchemy import asc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from accounting import models
from accounting.web_server.dependences import get_session, get_current_account

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix='/transactions',
    tags=['transactions'],
    responses={statuses.HTTP_404_NOT_FOUND: {'description': "Not Found"}},
)


class TransactionType(enum.Enum):
    payment = 'payment'
    task_assignment = 'task_assignment'
    task_closing = 'task_closing'


class PaymentDetails(BaseModel):
    payment_status: models.PaymentStatus


class TaskAssignmentDetails(BaseModel):
    task: models.Task


class TaskClosingDetails(BaseModel):
    task: models.Task


class Transaction(BaseModel):
    id: int
    date: datetime.datetime
    account_id: int
    business_day: datetime.date
    type: TransactionType | None
    amount: int
    details: PaymentDetails | TaskAssignmentDetails | TaskClosingDetails | None


async def _fetch_transactions(
    session: AsyncSession,
    business_day_from: datetime.date,
    business_day_till: datetime.date,
    account_id: int | None = None,
) -> List[Transaction]:
    query = select(
        models.Transaction,
        models.BillingCycle,
        models.TaskAssignment,
        models.TaskClosing,
        models.Payment,
        models.Task,
    ).outerjoin(
        models.TaskAssignment,
        models.TaskAssignment.transaction_id == models.Transaction.id,
    ).outerjoin(
        models.TaskClosing,
        models.TaskClosing.transaction_id == models.Transaction.id,
    ).outerjoin(
        models.Payment,
        models.Payment.transaction_id == models.Transaction.id,
    ).join(
        models.BillingCycle,
        models.Transaction.billing_cycle_id == models.BillingCycle.id,
    ).outerjoin(
        models.Task,
        (models.Task.id == models.TaskAssignment.task_id)
        | (models.Task.id == models.TaskClosing.task_id),
    ).order_by(
        asc(models.Transaction.id),
    )
    if account_id:
        query = query.where(models.BillingCycle.account_id == account_id)
    if business_day_from:
        query = query.where(func.DATE(models.BillingCycle.opened_at) >= business_day_from)
    if business_day_till:
        query = query.where(func.DATE(models.BillingCycle.opened_at) >= business_day_till)
    result = await session.execute(query)
    transactions: List[Transaction] = []
    transaction: models.Transaction
    billing_cycle: models.BillingCycle
    task_assignment: models.TaskAssignment | None
    task_closing: models.TaskClosing | None
    payment: models.Payment | None
    task: models.Task | None
    for (
        transaction,
        billing_cycle,
        task_assignment,
        task_closing,
        payment,
        task,
    ) in result.all():
        if task_assignment:
            transaction_type = TransactionType.task_assignment
            transaction_details = TaskAssignmentDetails(task=task)
        elif task_closing:
            transaction_type = TransactionType.task_closing
            transaction_details = TaskClosingDetails(task=task)
        elif payment:
            transaction_type = TransactionType.payment
            transaction_details = PaymentDetails(payment_status=payment.status)
        else:
            transaction_type = None
            transaction_details = None
            logger.warning('%s: unknown transaction type', transaction)
        transactions.append(Transaction(
            id=transaction.id,
            date=transaction.date,
            account_id=billing_cycle.account_id,
            business_day=billing_cycle.opened_at.date(),
            type=transaction_type,
            details=transaction_details,
            amount=transaction.debit - transaction.credit,
        ))
    return transactions


@router.get('/', response_model=List[Transaction])
async def list_transactions(
    business_day_from: datetime.date | None = None,
    business_day_till: datetime.date | None = None,
    account_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    account: models.Account = Depends(get_current_account),
):
    if account.role not in {models.AccountRole.manager, models.AccountRole.admin}:
        raise HTTPException(statuses.HTTP_403_FORBIDDEN)
    return await _fetch_transactions(session, business_day_from, business_day_till, account_id)


@router.get('/my/', response_model=List[Transaction])
async def list_my_transactions(
    business_day_from: datetime.date | None = None,
    business_day_till: datetime.date | None = None,
    session: AsyncSession = Depends(get_session),
    account: models.Account = Depends(get_current_account),
):
    if account.role not in {models.AccountRole.manager, models.AccountRole.admin}:
        raise HTTPException(statuses.HTTP_403_FORBIDDEN)
    return await _fetch_transactions(session, business_day_from, business_day_till, account.id)
