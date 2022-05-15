import asyncio
import logging

from sqlalchemy import select

from accounting import database
from accounting.models import Account, Payment, PaymentStatus, Transaction, BillingCycle

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def main():
    await database.setup(database.Settings())
    async with database.create_session() as session:
        pending_payment_ids = (await session.execute(
            select(Payment.id).where(Payment.status == PaymentStatus.pending)
        )).scalars().all()
    for payment_id in pending_payment_ids:
        async with database.create_session() as session:
            payment, transaction, billing_cycle, account = (await session.execute(
                select(
                    Payment,
                    Transaction,
                    BillingCycle,
                    Account,
                ).join(
                    Transaction, onclause=Transaction.id == Payment.transaction_id,
                ).join(
                    BillingCycle, onclause=BillingCycle.id == Transaction.billing_cycle_id,
                ).join(
                    Account, onclause=Account.id == BillingCycle.account_id,
                ).where(
                    Payment.id == payment_id,
                    Payment.status == PaymentStatus.pending,
                ).with_for_update(
                    of=Payment,
                )
            )).one()
        logger.info(
            'Pay %s$ to %s for %s - %s',
            (transaction.credit - transaction.debit) / 100,
            account.full_name,
            billing_cycle.opened_at,
            billing_cycle.closed_at,
        )
        payment.status = PaymentStatus.completed
        session.add(payment)
        await session.commit()


if __name__ == '__main__':
    asyncio.run(main(), debug=True)
