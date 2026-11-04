import base64
import json

import pytest

from duolingo_export.auth import user_id_from_jwt
from duolingo_export.exceptions import ExportError


def _jwt(payload: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{body}.sig"


def test_user_id_from_jwt():
    assert user_id_from_jwt(_jwt({"sub": 12345})) == 12345


def test_user_id_from_bad_jwt():
    with pytest.raises(ExportError):
        user_id_from_jwt("not-a-jwt")
