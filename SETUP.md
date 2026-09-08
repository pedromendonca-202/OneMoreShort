# Setup

Crie/ative .venv, instale as dependências já usadas pelo projeto e execute python -m app.cli init-db.

O modo padrão é manual; ele não chama Veo. Para upload real, crie um OAuth Desktop App no Google Cloud, habilite YouTube Data API v3 e salve o JSON em secrets/youtube_client_secret.json. Depois execute python -m app.cli youtube-auth.
