import datetime
from typing import Any, Mapping

import event_streaming

billing_transactions_topic = 'billing-transactions'

producer = event_streaming.Producer('accounting')


async def emit_event_task_transaction_completed_v1(
    account,
    business_day: datetime.date,
    transaction,
    details: Mapping[str, Any],
):
    await producer.send(
        billing_transactions_topic,
        'BillingTransactionCompleted', 1, {
            'public_id': transaction.public_id,
            'date': transaction.date.isoformat(),
            'business_day': business_day.isoformat(),
            'account': account.public_id,
            'debit': transaction.debit,
            'credit': transaction.credit,
            'details': details,
        },
    )
