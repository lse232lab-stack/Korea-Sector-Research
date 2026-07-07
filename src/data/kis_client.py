"""Korea Investment & Securities Open API client."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class KISAPIError(RuntimeError):
    """Raised when KIS API returns an error response."""


@dataclass(frozen=True)
class KISConfig:
    app_key: str
    app_secret: str
    base_url: str
    is_paper: bool = False
    account_no: str = ""
    account_product_code: str = "01"

    @classmethod
    def from_env(cls, env_file: str | None = ".env") -> "KISConfig":
        if env_file:
            load_env_file(env_file)

        base_url = os.getenv("KIS_BASE_URL", "").strip()
        account_no_raw = os.getenv("KIS_ACCOUNT_NO", "").strip()
        account_product_code_raw = os.getenv("KIS_ACCOUNT_PRODUCT_CODE", "01").strip() or "01"
        is_paper = os.getenv("KIS_IS_PAPER", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
        }
        app_key = os.getenv("KIS_APP_KEY", "").strip()
        app_secret = os.getenv("KIS_APP_SECRET", "").strip()
        if is_paper:
            app_key = os.getenv("KIS_PAPER_APP_KEY", app_key).strip()
            app_secret = os.getenv("KIS_PAPER_APP_SECRET", app_secret).strip()
            account_no_raw = os.getenv("KIS_PAPER_ACCOUNT_NO", account_no_raw).strip()
            account_product_code_raw = (
                os.getenv("KIS_PAPER_ACCOUNT_PRODUCT_CODE", account_product_code_raw).strip()
                or account_product_code_raw
            )

        missing = [
            name
            for name, value in {
                "KIS_APP_KEY": app_key,
                "KIS_APP_SECRET": app_secret,
                "KIS_BASE_URL": base_url,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(
                "Missing required KIS environment variables: " + ", ".join(missing)
            )

        account_no, account_product_code = parse_account_no(
            account_no_raw,
            default_product_code=account_product_code_raw,
        )
        return cls(
            app_key=app_key,
            app_secret=app_secret,
            base_url=base_url.rstrip("/"),
            is_paper=is_paper,
            account_no=account_no,
            account_product_code=account_product_code,
        )


class KISClient:
    """Small KIS client focused on domestic daily chart price data."""

    def __init__(self, config: KISConfig, token_cache_path: str | Path | None = None):
        self.config = config
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self.token_cache_path = (
            Path(token_cache_path) if token_cache_path else Path(".cache/kis_token.json")
        )

    def get_access_token(self) -> str:
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at - timedelta(minutes=5):
                return self._access_token

        cached_token = self._load_cached_token()
        if cached_token:
            return cached_token

        url = f"{self.config.base_url}/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.config.app_key,
            "appsecret": self.config.app_secret,
        }
        data = self._request_json("POST", url, json_body=payload)

        access_token = data.get("access_token")
        if not access_token:
            raise KISAPIError("KIS token response did not include access_token.")

        expires_in = int(data.get("expires_in", 24 * 60 * 60))
        self._access_token = access_token
        self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        self._save_cached_token(access_token, self._token_expires_at)
        return access_token

    def get_daily_item_chart_price(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        *,
        adjusted_price: bool = True,
    ) -> list[dict[str, Any]]:
        """Fetch domestic daily stock chart rows from KIS.

        Dates must be `YYYYMMDD` strings. The returned list is the raw KIS
        `output2` payload so the loader can normalize it separately.
        """

        url = (
            f"{self.config.base_url}"
            "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        )
        headers = self._headers(transaction_id="FHKST03010100")
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": str(ticker).zfill(6),
            "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": end_date,
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0" if adjusted_price else "1",
        }
        data = self._request_json("GET", url, headers=headers, params=params)
        output = data.get("output2", [])
        if not isinstance(output, list):
            raise KISAPIError("KIS daily price response output2 is not a list.")
        return output

    def get_domestic_current_price(self, ticker: str) -> dict[str, Any]:
        """Fetch current domestic stock quote from KIS."""
        url = f"{self.config.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = self._headers(transaction_id="FHKST01010100")
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": str(ticker).zfill(6),
        }
        data = self._request_json("GET", url, headers=headers, params=params)
        output = data.get("output", {})
        if not isinstance(output, dict):
            raise KISAPIError("KIS current price response output is not a dict.")
        return output

    def get_domestic_balance(self) -> dict[str, Any]:
        """Fetch domestic stock balance for the configured account."""
        self._require_account()
        url = f"{self.config.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = self._headers(transaction_id="VTTC8434R" if self.config.is_paper else "TTTC8434R")
        params = {
            "CANO": self.config.account_no,
            "ACNT_PRDT_CD": self.config.account_product_code,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        return self._request_json("GET", url, headers=headers, params=params)

    def place_domestic_cash_order(
        self,
        *,
        ticker: str,
        side: str,
        quantity: int,
        price: int = 0,
        order_type: str = "01",
    ) -> dict[str, Any]:
        """Place a domestic cash order. Use only after a dry-run review."""
        self._require_account()
        side_normalized = side.lower().strip()
        if side_normalized not in {"buy", "sell"}:
            raise ValueError("side must be 'buy' or 'sell'.")
        if quantity <= 0:
            raise ValueError("quantity must be positive.")

        url = f"{self.config.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        tr_id = ("VTTC0802U" if side_normalized == "buy" else "VTTC0801U") if self.config.is_paper else (
            "TTTC0802U" if side_normalized == "buy" else "TTTC0801U"
        )
        body = {
            "CANO": self.config.account_no,
            "ACNT_PRDT_CD": self.config.account_product_code,
            "PDNO": str(ticker).zfill(6),
            "ORD_DVSN": order_type,
            "ORD_QTY": str(int(quantity)),
            "ORD_UNPR": str(int(price)),
        }
        headers = self._headers(transaction_id=tr_id)
        headers["hashkey"] = self.create_hashkey(body)
        return self._request_json("POST", url, headers=headers, json_body=body)

    def create_hashkey(self, payload: dict[str, Any]) -> str:
        """Create KIS hashkey for trading POST requests."""
        url = f"{self.config.base_url}/uapi/hashkey"
        headers = {
            "content-type": "application/json; charset=utf-8",
            "appkey": self.config.app_key,
            "appsecret": self.config.app_secret,
        }
        data = self._request_json("POST", url, headers=headers, json_body=payload)
        hashkey = data.get("HASH") or data.get("hash")
        if not hashkey:
            raise KISAPIError("KIS hashkey response did not include HASH.")
        return str(hashkey)

    def _require_account(self) -> None:
        if not self.config.account_no:
            raise ValueError("KIS_ACCOUNT_NO is required for account or order APIs.")

    def _headers(self, transaction_id: str) -> dict[str, str]:
        token = self.get_access_token()
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.config.app_key,
            "appsecret": self.config.app_secret,
            "tr_id": transaction_id,
            "custtype": "P",
        }

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        retry_on_token_expiry: bool = True,
    ) -> dict[str, Any]:
        headers = headers or {}
        original_headers = dict(headers)
        original_url = url
        body = None
        if params:
            url = f"{url}?{urlencode(params)}"
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            headers = {"content-type": "application/json; charset=utf-8", **headers}

        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=30) as response:
                response_body = response.read().decode("utf-8")
                status_code = response.status
        except HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            status_code = exc.code
        except URLError as exc:
            raise KISAPIError(f"KIS API request failed: {exc.reason}") from exc

        try:
            data = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise KISAPIError(
                f"KIS API returned non-JSON response: HTTP {status_code}"
            ) from exc

        if status_code >= 400:
            message = data.get("msg1") or data.get("error_description") or response_body
            if retry_on_token_expiry and _is_token_expiry_message(str(message)):
                self._invalidate_cached_token()
                if "authorization" in {key.lower(): value for key, value in original_headers.items()}:
                    refreshed_headers = dict(original_headers)
                    for key in list(refreshed_headers):
                        if key.lower() == "authorization":
                            refreshed_headers[key] = f"Bearer {self.get_access_token()}"
                    return self._request_json(
                        method,
                        original_url,
                        headers=refreshed_headers,
                        params=params,
                        json_body=json_body,
                        retry_on_token_expiry=False,
                    )
            raise KISAPIError(f"KIS API HTTP {status_code}: {message}")

        return_code = str(data.get("rt_cd", "0"))
        if return_code not in {"0", ""}:
            message = data.get("msg1") or data.get("msg_cd") or data
            if retry_on_token_expiry and _is_token_expiry_message(str(message)):
                self._invalidate_cached_token()
                if "authorization" in {key.lower(): value for key, value in original_headers.items()}:
                    refreshed_headers = dict(original_headers)
                    for key in list(refreshed_headers):
                        if key.lower() == "authorization":
                            refreshed_headers[key] = f"Bearer {self.get_access_token()}"
                    return self._request_json(
                        method,
                        original_url,
                        headers=refreshed_headers,
                        params=params,
                        json_body=json_body,
                        retry_on_token_expiry=False,
                    )
            raise KISAPIError(f"KIS API error: {message}")

        return data

    def _load_cached_token(self) -> str | None:
        if not self.token_cache_path.exists():
            return None

        try:
            data = json.loads(self.token_cache_path.read_text(encoding="utf-8"))
            token = data.get("access_token")
            expires_at_raw = data.get("expires_at")
            if not token or not expires_at_raw:
                return None
            expires_at = datetime.fromisoformat(expires_at_raw)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

        if datetime.now() >= expires_at - timedelta(minutes=5):
            return None

        self._access_token = token
        self._token_expires_at = expires_at
        return token

    def _save_cached_token(self, token: str, expires_at: datetime) -> None:
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "access_token": token,
            "expires_at": expires_at.isoformat(timespec="seconds"),
        }
        self.token_cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _invalidate_cached_token(self) -> None:
        self._access_token = None
        self._token_expires_at = None
        try:
            self.token_cache_path.unlink()
        except FileNotFoundError:
            pass


def polite_sleep(seconds: float) -> None:
    """Sleep between API calls to avoid rate-limit pressure."""
    if seconds > 0:
        time.sleep(seconds)


def load_env_file(path: str) -> None:
    """Load simple KEY=VALUE pairs without requiring python-dotenv."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def parse_account_no(
    raw_account_no: str,
    *,
    default_product_code: str = "01",
) -> tuple[str, str]:
    """Parse KIS account number from CANO-ACNT_PRDT_CD or compact format."""
    value = raw_account_no.strip()
    default_product_code = default_product_code.strip() or "01"
    if not value:
        return "", default_product_code
    if "-" in value:
        cano, product_code = value.split("-", 1)
        return cano.strip(), (product_code.strip() or default_product_code)
    if len(value) > 8:
        return value[:8], value[8:] or default_product_code
    return value, default_product_code


def _is_token_expiry_message(message: str) -> bool:
    lowered = message.lower()
    return "token" in lowered and ("만료" in message or "expired" in lowered)
