from sqlalchemy import select

from accounting import database
from accounting.models import Account, BillingCycle, BillingCycleStatus
from accounting.transactions.utils import get_or_create


async def initialize_account(account_public_id: str):
    async with database.create_session() as init_session:
        account, account_created = await get_or_create(init_session, Account, public_id=account_public_id)
        if account_created:
            await init_session.commit()
            await init_session.refresh(account)
        billing_cycle, billing_cycle_created = (
            await get_or_create(init_session, BillingCycle, account_id=account.id, status=BillingCycleStatus.open)
        )
        if billing_cycle_created:
            await init_session.commit()
            await init_session.refresh(billing_cycle)


async def get_current_billing_cycle(session, account_public_id: str) -> BillingCycle:
    return (await session.execute(
        select(BillingCycle).join(Account).where(
            BillingCycle.status == BillingCycleStatus.open,
            Account.public_id == account_public_id,
        ).with_for_update()
    )).scalar_one()
