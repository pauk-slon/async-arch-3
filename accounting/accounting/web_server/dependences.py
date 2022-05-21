from functools import cache

from fastapi import Depends, HTTPException
from fastapi.security.oauth2 import OAuth2AuthorizationCodeBearer
from starlette import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import auth
import database
from event_streaming import Producer
from accounting.event_producing import producer
from accounting.models import Account


async def get_session():
    async with database.create_session() as session:
        yield session


@cache
def get_auth_client():
    return auth.Client()


oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=get_auth_client().oauth_authorization_url,
    tokenUrl='/oauth/token',
    scopes={
        'public_id': "Get public ID of the current user.",
    },
)


async def get_current_account(
    token: str = Depends(oauth2_scheme),
    auth_client: auth.Client = Depends(get_auth_client),
    session: AsyncSession = Depends(get_session),
) -> Account:
    try:
        # TODO: cache a token->public_id map until the token is not expired
        account_data = await auth_client.fetch_account(token)
    except auth.OAuthError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error))
    public_id = account_data['public_id']
    result = await session.execute(
        select(Account).where(Account.public_id == public_id)
    )
    account: Account | None = result.scalars().first()
    if not account:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown account")
    return account


@cache
def get_producer() -> Producer:
    return producer
