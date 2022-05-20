import asyncio
import logging

from sqlalchemy import select

from accounting import database
from accounting import event_producing
from accounting.models import Account, Payment, PaymentStatus, BillingTransaction, BillingCycle
import event_streaming

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def main():
    await database.setup(database.Settings())
    event_streaming_settings = event_streaming.Settings()
    await event_producing.producer.start(event_streaming_settings)
    async with database.create_session() as session:
        pending_payment_ids = (await session.execute(
            select(Payment.id).where(Payment.status == PaymentStatus.pending)
        )).scalars().all()
    for payment_id in pending_payment_ids:
        async with database.create_session() as session:
            payment, transaction, billing_cycle, account = (await session.execute(
                select(
                    Payment,
                    BillingTransaction,
                    BillingCycle,
                    Account,
                ).join(
                    BillingTransaction, onclause=BillingTransaction.id == Payment.billing_transaction_id,
                ).join(
                    BillingCycle, onclause=BillingCycle.id == BillingTransaction.billing_cycle_id,
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
        await event_producing.emit_task_transaction_completed_v1(
            account,
            billing_cycle.business_day,
            transaction,
            {'type': 'payment'},
        )
    await event_producing.producer.stop()


if __name__ == '__main__':
    asyncio.run(main(), debug=True)
