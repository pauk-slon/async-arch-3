from fastapi import Depends, FastAPI, Form, HTTPException
from fastapi.security.oauth2 import OAuth2AuthorizationCodeBearer

from task_tracker import auth
from task_tracker import database

auth_client = auth.Client()
app = FastAPI(
    title="Task Tracker",
    swagger_ui_init_oauth={
        'clientId': auth_client.settings.oauth_client_id,
        'clientSecret': auth_client.settings.oauth_client_secret,
        'scopeSeparator': " ",
        'scopes': "public_id",
    },
    swagger_ui_parameters={
        'persistAuthorization': True,
    }
)
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=auth_client.oauth_authorization_url,
    tokenUrl='/oauth/token',
    scopes={
        'public_id': "Get public ID of the current user.",
    },
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
):
    if client_id != auth_client.settings.oauth_client_id:
        raise HTTPException(status_code=400, detail="Invalid oauth_client_id")
    if client_secret != auth_client.settings.oauth_client_secret:
        raise HTTPException(status_code=400, detail="Invalid oauth_client_secret")
    try:
        return await auth_client.fetch_token_by_authorization_code(code, redirect_uri)
    except auth.OAuthError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get('/accounts/current')
async def get_current_account(token: str = Depends(oauth2_scheme)):
    try:
        return await auth_client.fetch_account(token)
    except auth.OAuthError as error:
        raise HTTPException(status_code=400, detail=str(error))
