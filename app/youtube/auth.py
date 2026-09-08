"""Installed-app OAuth with human-action reporting instead of silent failure."""
from __future__ import annotations

from pathlib import Path

from app.core.errors import HumanActionRequired


def get_credentials(client_secret_path: Path | str, token_path: Path | str, scopes: list[str]):
    secret, token = Path(client_secret_path), Path(token_path)
    if not secret.is_file():
        raise HumanActionRequired(
            problem="YouTube OAuth client secret is missing.",
            root_cause="YouTube uploads require an OAuth Desktop App client, not an API key.",
            automated="Checked configuration and preserved the production for resume.",
            remains="Create/download the OAuth client secret and authorize this local application once.",
            action=f"1) In Google Cloud enable YouTube Data API v3. 2) Create OAuth Client ID of type Desktop app. "
                   f"3) Download JSON to {secret}. 4) Run oms youtube auth and approve the browser prompt.",
            next_step="The pipeline will resume upload after the token is saved.",
        )
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = Credentials.from_authorized_user_file(str(token), scopes) if token.is_file() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(secret), scopes)
        creds = flow.run_local_server(port=0)
        token.parent.mkdir(parents=True, exist_ok=True)
        token.write_text(creds.to_json(), encoding="utf-8")
    return creds
