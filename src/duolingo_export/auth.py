"""Authentication: build a requests session carrying the Duolingo JWT."""
from __future__ import annotations

import base64
import json
import logging

import requests

from .config import REQUEST_TIMEOUT, USER_AGENT
from .exceptions import ExportError

log = logging.getLogger(__name__)

LOGIN_URL = "https://www.duolingo.com/2017-06-30/login?fields="


def user_id_from_jwt(jwt: str) -> int:
    """Read the numeric user id (the "sub" claim) from a JWT."""
    try:
        payload = jwt.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return int(json.loads(base64.urlsafe_b64decode(payload))["sub"])
    except (IndexError, KeyError, ValueError) as exc:
        raise ExportError(f"Could not read a user id from the JWT ({exc}).") from exc


def login_with_password(session: requests.Session, username: str, password: str) -> str:
    """Fallback login. Often blocked by Duolingo's bot protection."""
    r = session.post(
        LOGIN_URL,
        json={"login": username, "password": password, "distinctId": "export-script"},
        timeout=REQUEST_TIMEOUT,
    )
    if r.status_code != 200:
        raise ExportError(
            f"Login failed (HTTP {r.status_code}): {r.text[:300]}\n"
            "Duolingo likely blocked scripted login. Use the jwt_token cookie instead."
        )
    jwt = r.headers.get("jwt") or session.cookies.get("jwt_token")
    if not jwt:
        raise ExportError("Login returned no JWT. Use the jwt_token cookie instead.")
    return jwt


def build_session(
    jwt: str = "", username: str = "", password: str = ""
) -> tuple[requests.Session, int]:
    """Return an authenticated session and the user id."""
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://www.duolingo.com",
            "Referer": "https://www.duolingo.com/practice-hub/words",
        }
    )

    if not jwt:
        if not (username and password):
            raise ExportError(
                "Provide DUOLINGO_JWT, or DUOLINGO_USER and DUOLINGO_PASS "
                "(see .env.example)."
            )
        jwt = login_with_password(s, username, password)

    s.cookies.set("jwt_token", jwt, domain="www.duolingo.com")
    s.headers["Authorization"] = f"Bearer {jwt}"
    return s, user_id_from_jwt(jwt)
