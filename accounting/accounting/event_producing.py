import datetime
from typing import Any, Mapping

from accounting.models import Account, BillingTransaction, Task
import event_streaming

billing_transactions_topic = 'billing-transactions'
task_price_streaming_topic = 'task-price-stream'

producer = event_streaming.Producer('accounting')


async def emit_task_transaction_completed_v1(
    account: Account,
    business_day: datetime.date,
    billing_transaction: BillingTransaction,
    details: Mapping[str, Any],
):
    await producer.send(
        billing_transactions_topic,
        'BillingTransactionCompleted', 1, {
            'public_id': billing_transaction.public_id,
            'date': billing_transaction.date.isoformat(),
            'business_day': business_day.isoformat(),
            'account': account.public_id,
            'debit': billing_transaction.debit,
            'credit': billing_transaction.credit,
            'details': details,
        },
    )


async def emit_task_price_created_v1(task: Task):
    await producer.send(
        task_price_streaming_topic,
        'TaskPriceCreated', 1, {
            'public_id': task.public_id,
            'task': task.public_id,
            'assignment_cost': task.assignment_cost,
            'closing_cost': task.closing_cost,
        },
    )
