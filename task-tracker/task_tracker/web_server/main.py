from fastapi import FastAPI, Form, HTTPException, Depends

from task_tracker import auth
from task_tracker import database
from task_tracker.web_server.dependences import get_auth_client
from task_tracker.web_server.endpoints import accounts

app = FastAPI(
    title="Task Tracker",
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
database_settings = database.Settings()


@app.on_event('startup')
async def on_startup():
    await database.setup(database_settings)


@app.post('/oauth/token', include_in_schema=False)
async def proxy_token(
    grant_type: str = Form(None, regex='authorization_code'),
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


app.include_router(accounts.router)
