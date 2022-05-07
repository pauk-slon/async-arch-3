from pydantic import BaseSettings


class Settings(BaseSettings):
    bootstrap_servers: str

    class Config:
        env_prefix = 'event_streaming_'
