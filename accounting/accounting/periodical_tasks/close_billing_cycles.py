import asyncio
import logging

from sqlalchemy import select

import database
from accounting.models import Account
from accounting.transactions.billing import close_current_billing_cycle

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def main():
    await database.setup(database.Settings())
    async with database.create_session() as session:
        accounts = (await session.execute(select(Account))).scalars().all()
    for account in accounts:
        logger.info('Closing billing cycle for %s', account)
        await close_current_billing_cycle(account.public_id)


if __name__ == '__main__':
    asyncio.run(main(), debug=True)
