import logging

from fastapi import FastAPI, Form, HTTPException, Depends

import auth
import event_streaming
from accounting import database
from accounting.web_server.dependences import get_auth_client, get_producer
from accounting.web_server.endpoints import accounts, transactions

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Accounting",
    swagger_ui_init_oauth={
        'clientId': get_auth_client().settings.oauth_client_id,
        'clientSecret': get_auth_client().settings.oauth_client_secret,
        'scopeSeparator': " ",
        'scopes': "public_id",
    },
    swagger_ui_parameters={
        'persistAuthorization': True,
    }
)

app.include_router(accounts.router)
app.include_router(transactions.router)


@app.on_event('startup')
async def on_startup():
    await database.setup(database.Settings())
    await get_producer().start(event_streaming.Settings())


@app.on_event('shutdown')
async def on_shutdown():
    await get_producer().stop()


@app.post('/oauth/token', include_in_schema=False)
async def proxy_token(
        grant_type: str = Form(None, regex='authorization_code'),  # noqa
        code: str = Form(...),
        client_id: str = Form(...),
        client_secret: str = Form(...),
        redirect_uri: str = Form(...),
        auth_client: auth.Client = Depends(get_auth_client),
):
    if client_id != auth_client.settings.oauth_client_id:
        raise HTTPException(status_code=400, detail="Invalid oauth_client_id")
    if client_secret != auth_client.settings.oauth_client_secret:
        raise HTTPException(status_code=400, detail="Invalid oauth_client_secret")
    try:
        return await auth_client.fetch_token_by_authorization_code(code, redirect_uri)
    except auth.OAuthError as error:
        raise HTTPException(status_code=400, detail=str(error))
