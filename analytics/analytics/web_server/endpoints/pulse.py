import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette import status as statuses
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.models import Account, BillingTransaction, BillingTransactionType
from analytics.web_server.dependences import get_session, get_current_account

router = APIRouter(
    prefix='/pulse',
    tags=['pulse'],
    responses={statuses.HTTP_404_NOT_FOUND: {'description': "Not Found"}},
)


class Pulse(BaseModel):
    profit_today: int
    negative_balance_worker_count: int
    most_expensive_task_today: int | None
    most_expensive_task_this_week: int | None
    most_expensive_task_this_month: int | None


async def get_most_expensive_task(
        session: AsyncSession,
        date_from: datetime.date,
        date_till: datetime.date,
) -> int | None:
    return (await session.execute(
        select(
            func.max(BillingTransaction.debit),
        ).where(
            BillingTransaction.business_day >= date_from,
            BillingTransaction.business_day <= date_till,
            BillingTransaction.type == BillingTransactionType.task_closing,
        )
    )).scalar_one_or_none()


@router.get('/', response_model=Pulse)
async def get_stats(
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(get_current_account),
):
    business_day = datetime.date.today()
    profit_today = (await session.execute(
        select(
            func.sum(BillingTransaction.credit - BillingTransaction.debit),
        ).where(
            BillingTransaction.business_day == business_day,
            BillingTransaction.type.in_((
                BillingTransactionType.task_assignment,
                BillingTransactionType.task_closing,
            )),
        )
    )).scalar_one_or_none() or 0

    negative_balance_worker_count = (await session.execute(select(
        func.count(distinct(BillingTransaction.account_id)),
    ).group_by(
        BillingTransaction.account_id,
    ).having(
        func.sum(BillingTransaction.debit - BillingTransaction.credit) < 0,
    ))).scalar_one_or_none() or 0
    return Pulse(
        profit_today=profit_today,
        negative_balance_worker_count=negative_balance_worker_count,
        most_expensive_task_today=await get_most_expensive_task(session, business_day, business_day),
        most_expensive_task_this_week=await get_most_expensive_task(
            session,
            business_day - datetime.timedelta(days=business_day.weekday()),
            business_day,
        ),
        most_expensive_task_this_month=await get_most_expensive_task(
            session,
            datetime.date(business_day.year, business_day.month, 1),
            business_day,
        ),
    )
