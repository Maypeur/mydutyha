"""MYDUTY app API client.

Uses the same private endpoints as the MYDUTY mobile app ("vayne"):

    GET  /v1/start                                          -> api.latestURI
    POST /v1/users/login                                    -> user, groupList
    GET  /v1/schedules/{userId}/duty-units                  -> shift definitions
    GET  /v1/schedules/{userId}/duty-schedules/{y}/{m}/{y}/{m}

Every request is signed with the app's embedded key (HMAC-SHA1, hex), and the
numeric MYDUTY user id is sent in the ``userId`` header. No share link is
involved, so nothing expires.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from datetime import date

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Constants from the shipped Android app (kr.fourwheels.api.a + R.string)
API_KEY = "e12b7e3d24b74749847c445012562828"
API_SECRET = "efc6f702d3d943619656f117a3c38afe4fc11cff31b6471d99246603f9817dcd"
BOOTSTRAP_URL = "https://vayne.myduty.kr/v1/start"
DEFAULT_API_BASE = "https://vayne-api.myduty.kr/v1/"

DEVICE_ID = "mydutyha-homeassistant"
VERSION_CODE = "2177"
VERSION_NAME = "2.34.3"
DEVICE_OS = "34"
DEVICE_MODEL = "HOME ASSISTANT"
TIMEOUT = aiohttp.ClientTimeout(total=20)


class MyDutyError(Exception):
    """API returned a business error."""


class MyDutyAuthError(MyDutyError):
    """E-mail/password was rejected."""


def _signed_params() -> dict[str, str]:
    ts = str(int(time.time()))
    nonce = str(uuid.uuid4())
    signature = hmac.new(
        API_SECRET.encode(), f"{nonce}&{ts}".encode(), hashlib.sha1
    ).hexdigest()
    return {
        "apiKey": API_KEY,
        "nonce": nonce,
        "timestamp": ts,
        "signature": signature,
    }


class MyDutyApi:
    """Minimal async client for the MYDUTY app API."""

    def __init__(self, user_id: str | None = None) -> None:
        self.user_id = str(user_id) if user_id else "0"
        self.base = DEFAULT_API_BASE

    # -- transport ---------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        return {
            "userId": self.user_id,
            "platform": "ANDROID",
            "versionCode": VERSION_CODE,
            "versionName": VERSION_NAME,
            "deviceID": DEVICE_ID,
            "deviceModel": DEVICE_MODEL,
            "deviceOSVersion": DEVICE_OS,
            "timezone": "Europe/Berlin",
            "language": "en",
            "Accept": "application/json",
        }

    async def _request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        path: str,
        data: dict | None = None,
        *,
        base: str | None = None,
    ) -> dict:
        url = (base or self.base) + path
        params = _signed_params()
        headers = self._headers()

        if method in ("POST", "PUT"):
            form = dict(data or {})
            form.update(params)  # signed params travel inside the form body
            request = session.request(method, url, data=form, headers=headers)
        else:
            request = session.request(method, url, params=params, headers=headers)

        async with request as response:
            try:
                payload = await response.json(content_type=None)
            except Exception as err:  # noqa: BLE001 - surface anything odd
                raise MyDutyError(f"invalid response ({response.status})") from err

        header = payload.get("header") or {}
        if header.get("status") != "success":
            message = header.get("message") or f"HTTP {response.status}"
            raise MyDutyError(message)
        return payload.get("body") or {}

    # -- endpoints ---------------------------------------------------------
    async def async_bootstrap(self) -> None:
        """Ask /v1/start for the current API base (best effort)."""
        try:
            async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
                body = await self._request(
                    session, "GET", "v1/start", base="https://vayne.myduty.kr/"
                )
        except (aiohttp.ClientError, MyDutyError) as err:
            _LOGGER.debug("MYDUTY bootstrap failed, using default base: %s", err)
            return
        latest = (body.get("api") or {}).get("latestURI")
        if latest:
            self.base = latest

    async def async_login(self, email: str, password: str) -> dict:
        try:
            async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
                body = await self._request(
                    session,
                    "POST",
                    "users/login",
                    {
                        "email": email,
                        "password": password,
                        "deviceID": DEVICE_ID,
                        "deviceOSName": "android",
                        "deviceOSVersion": DEVICE_OS,
                    },
                )
        except MyDutyError as err:
            raise MyDutyAuthError(str(err)) from err
        user = body.get("user") or {}
        if not user.get("userId"):
            raise MyDutyAuthError("login did not return a user id")
        self.user_id = str(user["userId"])
        return user

    async def async_user(self, session: aiohttp.ClientSession | None = None) -> dict:
        own = session is None
        session = session or aiohttp.ClientSession(timeout=TIMEOUT)
        try:
            body = await self._request(session, "GET", f"users/{self.user_id}")
        finally:
            if own:
                await session.close()
        return body.get("user") or {}

    async def async_duty_units(self, session: aiohttp.ClientSession) -> list[dict]:
        body = await self._request(
            session, "GET", f"schedules/{self.user_id}/duty-units"
        )
        return body.get("dutyUnits") or []

    async def async_schedules(
        self, session: aiohttp.ClientSession, start: date, end: date
    ) -> list[dict]:
        """Month blocks between start and end month (inclusive)."""
        body = await self._request(
            session,
            "GET",
            (
                f"schedules/{self.user_id}/duty-schedules/"
                f"{start.year}/{start.month:02d}/{end.year}/{end.month:02d}"
            ),
        )
        return body.get("schedulesForMonths") or []

    async def async_fetch_data(self) -> dict:
        """Return {"duty_units": [...], "month_blocks": [...]}."""
        await self.async_bootstrap()
        today = date.today()
        if today.month == 1:
            start = date(today.year - 1, 12, 1)
        else:
            start = date(today.year, today.month - 1, 1)
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            duty_units = await self.async_duty_units(session)
            month_blocks = await self.async_schedules(session, start, today)
        return {"duty_units": duty_units, "month_blocks": month_blocks}
