"""Simple API key auth — maps static keys to user IDs."""
import yaml
from pathlib import Path
from fastapi import Header, HTTPException

_config_path = Path(__file__).parent.parent / "config.yaml"
with open(_config_path) as f:
    _config = yaml.safe_load(f)

_api_keys: dict[str, str] = _config["auth"]["api_keys"]


def get_current_user(x_api_key: str = Header(...)) -> str:
    user_id = _api_keys.get(x_api_key)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user_id
