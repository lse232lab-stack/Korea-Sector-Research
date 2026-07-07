"""OpenDART data helpers used by the LS ELECTRIC recruiting report."""

from __future__ import annotations

import io
import json
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen
from xml.etree import ElementTree


OPEN_DART_BASE = "https://opendart.fss.or.kr/api"


class DARTAPIError(RuntimeError):
    """Raised when OpenDART returns an unsuccessful response."""


@dataclass(frozen=True)
class DARTConfig:
    api_key: str

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "DARTConfig":
        api_key = os.getenv("DART_API_KEY")
        path = Path(env_path)
        if not api_key and path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("DART_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        if not api_key:
            raise DARTAPIError("DART_API_KEY is not configured.")
        return cls(api_key=api_key)


class DARTClient:
    """Small stdlib-only OpenDART client.

    The client intentionally avoids logging the API key. Callers should persist
    raw responses for auditability and use parsed summaries for reports.
    """

    def __init__(self, config: DARTConfig):
        self.config = config

    def get_json(self, endpoint: str, **params: Any) -> dict[str, Any]:
        payload = {"crtfc_key": self.config.api_key, **params}
        url = f"{OPEN_DART_BASE}/{endpoint}?{urlencode(payload)}"
        with urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        status = data.get("status")
        if status and status not in {"000", "013"}:
            message = data.get("message", "unknown OpenDART error")
            raise DARTAPIError(f"{endpoint} failed: {status} {message}")
        return data

    def download_zip(self, endpoint: str, **params: Any) -> zipfile.ZipFile:
        payload = {"crtfc_key": self.config.api_key, **params}
        url = f"{OPEN_DART_BASE}/{endpoint}?{urlencode(payload)}"
        with urlopen(url, timeout=60) as response:
            blob = response.read()
        if blob[:1] == b"{":
            data = json.loads(blob.decode("utf-8"))
            raise DARTAPIError(f"{endpoint} failed: {data.get('status')} {data.get('message')}")
        return zipfile.ZipFile(io.BytesIO(blob))

    def corp_codes(self) -> list[dict[str, str]]:
        archive = self.download_zip("corpCode.xml")
        xml_name = archive.namelist()[0]
        root = ElementTree.fromstring(archive.read(xml_name))
        rows: list[dict[str, str]] = []
        for item in root.findall("list"):
            rows.append(
                {
                    "corp_code": _text(item, "corp_code"),
                    "corp_name": _text(item, "corp_name"),
                    "stock_code": _text(item, "stock_code"),
                    "modify_date": _text(item, "modify_date"),
                }
            )
        return rows

    def company(self, corp_code: str) -> dict[str, Any]:
        return self.get_json("company.json", corp_code=corp_code)

    def filings(
        self,
        corp_code: str,
        bgn_de: str,
        end_de: str,
        pblntf_detail_ty: str | None = None,
        page_count: int = 100,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "page_count": page_count,
        }
        if pblntf_detail_ty:
            params["pblntf_detail_ty"] = pblntf_detail_ty
        data = self.get_json("list.json", **params)
        return data.get("list", [])

    def single_accounts(self, corp_code: str, bsns_year: str, reprt_code: str) -> list[dict[str, Any]]:
        data = self.get_json(
            "fnlttSinglAcnt.json",
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
        )
        return data.get("list", [])

    def report_document_text(self, rcept_no: str) -> str:
        archive = self.download_zip("document.xml", rcept_no=rcept_no)
        chunks: list[str] = []
        for name in archive.namelist():
            raw = archive.read(name)
            text = _decode_bytes(raw)
            chunks.append(_strip_xml_tags(text))
        return "\n".join(chunks)


def _text(node: ElementTree.Element, child: str) -> str:
    found = node.find(child)
    return (found.text or "").strip() if found is not None else ""


def _decode_bytes(raw: bytes) -> str:
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _strip_xml_tags(text: str) -> str:
    in_tag = False
    output: list[str] = []
    for char in text:
        if char == "<":
            in_tag = True
            output.append(" ")
        elif char == ">":
            in_tag = False
            output.append(" ")
        elif not in_tag:
            output.append(char)
    cleaned = "".join(output)
    return "\n".join(line.strip() for line in cleaned.splitlines() if line.strip())
