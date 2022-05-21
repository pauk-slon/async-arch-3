import datetime
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette import status as statuses
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from accounting.models import Account, AccountRole, BillingCycle, TaskAssignment, TaskClosing, BillingTransaction
from accounting.web_server.dependences import get_session, get_current_account

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix='/daily-profit',
    tags=['daily_profit'],
    responses={statuses.HTTP_404_NOT_FOUND: {'description': "Not Found"}},
)


class DailyProfit(BaseModel):
    business_day: datetime.date
    amount: int


@router.get('/', response_model=List[DailyProfit])
async def list_profit_by_business_day(
    business_day_from: datetime.date,
    business_day_till: datetime.date,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(get_current_account),
):
    if account.role not in {AccountRole.manager, AccountRole.admin}:
        raise HTTPException(statuses.HTTP_403_FORBIDDEN)
    profit_by_business_day_query = select(
        func.sum(BillingTransaction.debit),
        func.sum(BillingTransaction.credit),
        func.date(BillingCycle.opened_at),
    ).join(
        BillingCycle,
        BillingCycle.id == BillingTransaction.billing_cycle_id,
    ).outerjoin(
        TaskAssignment,
        TaskAssignment.billing_transaction_id == BillingTransaction.id,
    ).outerjoin(
        TaskClosing,
        TaskClosing.billing_transaction_id == BillingTransaction.id,
    ).where(
        func.date(BillingCycle.opened_at) >= business_day_from,
        func.date(BillingCycle.opened_at) <= business_day_till,
        TaskAssignment.id.isnot(None) | TaskAssignment.id.isnot(None),
    ).group_by(
        func.date(BillingCycle.opened_at),
    )
    profit_by_business_day = (
        await session.execute(profit_by_business_day_query)
    ).all()
    return [
        DailyProfit(business_day=business_day, amount=credit - debit)
        for debit, credit, business_day in profit_by_business_day
    ]
