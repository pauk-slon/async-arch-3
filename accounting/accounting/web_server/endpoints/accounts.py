from typing import List

from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accounting.models import Account, AccountRole
from accounting.web_server.dependences import get_session, get_current_account

router = APIRouter(
    prefix='/accounts',
    tags=['accounts'],
    responses={status.HTTP_404_NOT_FOUND: {'description': "Not Found"}},
)


@router.get('/', response_model=List[Account])
async def list_accounts(
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(get_current_account),
):
    if account.role not in {AccountRole.manager, AccountRole.admin}:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    result = await session.execute(select(Account))
    return result.scalars().all()


@router.get('/current', response_model=Account)
async def get_current_account(account: Account = Depends(get_current_account)):
    return account
