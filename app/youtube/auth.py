"""Installed-app OAuth with human-action reporting instead of silent failure."""
from __future__ import annotations

from pathlib import Path

from app.core.errors import HumanActionRequired

# One consent screen covers upload, read-only Data API calls (stats, channel) and Analytics API
# reports, so analytics collection never needs a second human authorization.
YOUTUBE_SCOPES: list[str] = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def get_credentials(client_secret_path: Path | str, token_path: Path | str, scopes: list[str] | None = None):
    scopes = list(scopes or YOUTUBE_SCOPES)
    secret, token = Path(client_secret_path), Path(token_path)
    if not secret.is_file():
        raise HumanActionRequired(
            problem="YouTube OAuth client secret is missing.",
            root_cause="YouTube uploads require an OAuth Desktop App client, not an API key.",
            automated="Checked configuration and preserved the production for resume.",
            remains="Create/download the OAuth client secret and authorize this local application once.",
            action=f"1) In Google Cloud enable YouTube Data API v3 and YouTube Analytics API. 2) Create OAuth Client ID "
                   f"of type Desktop app. 3) Download JSON to {secret}. 4) Run `python -m app.cli youtube-auth` and "
                   f"approve the browser prompt once (upload + analytics scopes).",
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
