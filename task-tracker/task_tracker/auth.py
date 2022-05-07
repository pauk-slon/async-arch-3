from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseSettings


class Settings(BaseSettings):
    oauth_client_id: str
    oauth_client_secret: str
    internal_url: str
    url: str

    class Config:
        env_prefix = 'auth_'


class OAuthError(Exception):
    pass


class Client:
    def __init__(self):
        self.settings = Settings()

    @property
    def oauth_authorization_url(self):
        return self._compose_url('oauth/authorize')

    def _compose_internal_url(self, endpoint_path: str) -> str:
        return urljoin(self.settings.internal_url, endpoint_path)

    def _compose_url(self, endpoint_path: str) -> str:
        return urljoin(self.settings.url, endpoint_path)

    @property
    def introspection_internal_url(self):
        return urljoin(self.settings.internal_url, 'introspect')

    @property
    def root_netloc(self):
        return urlparse(self.settings.url).netloc

    async def fetch_token_by_authorization_code(self, code: str, redirect_uri: str) -> dict:
        headers = {
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'host': self.root_netloc,
        }
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'oauth_client_id': self.settings.oauth_client_id,
            'oauth_client_secret': self.settings.oauth_client_secret,
            'redirect_uri': redirect_uri,
        }
        token_url = self._compose_internal_url('oauth/token')
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, headers=headers, data=payload)
        if response.status_code == httpx.codes.OK:
            return response.json()
        else:
            raise OAuthError(response.text)

    async def fetch_account(self, token: str) -> dict:
        headers = {
            'accept': 'application/json',
            'host': self.root_netloc,
            'authorization': f'Bearer {token}',
        }
        current_account_url = self._compose_internal_url('accounts/current')
        async with httpx.AsyncClient() as client:
            response = await client.get(current_account_url, headers=headers)
        if response.status_code == httpx.codes.OK:
            return response.json()
        else:
            raise OAuthError(response.text)
