import json
import os
from dataclasses import dataclass

import boto3


@dataclass
class AppConfig:
    notion_grabaciones_ds_id: str
    notion_episodios_ds_id: str
    notion_projects_ds_id: str
    notion_area_una_estrella_id: str
    google_calendar_id: str
    secrets_manager_secret_name: str
    notion_token: str
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str
    webhook_shared_secret: str


def _get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _load_secret(secret_name: str) -> dict:
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    secret_string = response.get("SecretString")

    if not secret_string:
        raise ValueError(f"Secret {secret_name} does not contain SecretString")

    return json.loads(secret_string)


def load_config() -> AppConfig:
    secret_name = _get_env("SECRETS_MANAGER_SECRET_NAME")
    secret = _load_secret(secret_name)

    return AppConfig(
        notion_grabaciones_ds_id=_get_env("NOTION_GRABACIONES_DS_ID"),
        notion_episodios_ds_id=_get_env("NOTION_EPISODIOS_DS_ID"),
        notion_projects_ds_id=_get_env("NOTION_PROJECTS_DS_ID"),
        notion_area_una_estrella_id=_get_env("NOTION_AREA_UNA_ESTRELLA_ID"),
        google_calendar_id=_get_env("GOOGLE_CALENDAR_ID"),
        secrets_manager_secret_name=secret_name,
        notion_token=secret["NOTION_TOKEN"],
        google_client_id=secret["GOOGLE_CLIENT_ID"],
        google_client_secret=secret["GOOGLE_CLIENT_SECRET"],
        google_refresh_token=secret["GOOGLE_REFRESH_TOKEN"],
        webhook_shared_secret=secret["WEBHOOK_SHARED_SECRET"],
    )