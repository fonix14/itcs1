from dataclasses import dataclass
from typing import List, Dict, Any
from io import BytesIO
import hashlib

import pandas as pd


@dataclass
class ParseResult:
    tasks: List[Dict[str, Any]]
    total: int
    invalid: int
    headers: List[str]


def normalize(name: str) -> str:
    s = str(name).strip().lower()
    s = s.replace("\n", " ")
    s = s.replace("\t", " ")
    s = " ".join(s.split())
    return s


def find_col(df, variants):
    norm_map = {normalize(c): c for c in df.columns}
    for variant in variants:
        v = normalize(variant)
        if v in norm_map:
            return norm_map[v]

    for c in df.columns:
        nc = normalize(c)
        for variant in variants:
            vv = normalize(variant)
            if vv in nc or nc in vv:
                return c
    return None


def make_portal_task_id(row: dict) -> str:
    base = " | ".join(
        [
            str(row.get("store_no") or "").strip(),
            str(row.get("incident_type") or "").strip(),
            str(row.get("text") or "").strip(),
            str(row.get("status") or "").strip(),
            str(row.get("created_at") or "").strip(),
        ]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]


def parse_portal_l4_xlsx(content: bytes) -> ParseResult:
    df = pd.read_excel(BytesIO(content), dtype=object)

    headers = [str(x) for x in df.columns]

    col_portal_id = find_col(df, [
        "portal_task_id",
        "portal id",
        "task id",
        "id",
        "номер заявки",
        "№ заявки",
        "номер обращения",
        "обращение id",
        "заявка id",
    ])

    col_store_no = find_col(df, [
        "store_no",
        "store no",
        "store",
        "номер магазина",
        "№ магазина",
        "магазин",
        "код магазина",
        "тт",
        "торговая точка",
        "уровень 4",
    ])

    col_sla = find_col(df, [
        "sla",
        "sla_date",
        "дата sla",
        "срок sla",
        "дедлайн",
        "deadline",
        "срок",
    ])

    col_created = find_col(df, [
        "created_at",
        "created",
        "дата создания",
        "создано",
        "дата",
        "created date",
    ])

    col_status = find_col(df, [
        "status",
        "статус",
    ])

    col_type = find_col(df, [
        "тип инцидента",
        "incident type",
        "type",
        "категория",
        "тип",
    ])

    col_text = find_col(df, [
        "текст обращения",
        "description",
        "описание",
        "комментарий",
        "comment",
        "text",
    ])

    col_location = find_col(df, [
        "местонахождение",
        "location",
        "адрес",
    ])

    tasks: List[Dict[str, Any]] = []
    invalid = 0

    for _, row in df.iterrows():
        raw_store = row.get(col_store_no) if col_store_no else None
        raw_portal = row.get(col_portal_id) if col_portal_id else None

        store_no = None if pd.isna(raw_store) else str(raw_store).strip()
        portal_task_id = None if pd.isna(raw_portal) else str(raw_portal).strip()

        incident_type = None if not col_type or pd.isna(row.get(col_type)) else str(row.get(col_type)).strip()
        text = None if not col_text or pd.isna(row.get(col_text)) else str(row.get(col_text)).strip()
        status = None if not col_status or pd.isna(row.get(col_status)) else str(row.get(col_status)).strip()
        sla_date = None if not col_sla or pd.isna(row.get(col_sla)) else str(row.get(col_sla)).strip()
        created_at = None if not col_created or pd.isna(row.get(col_created)) else str(row.get(col_created)).strip()
        location = None if not col_location or pd.isna(row.get(col_location)) else str(row.get(col_location)).strip()

        if store_no:
            digits = "".join(ch for ch in store_no if ch.isdigit())
            store_no = digits if digits else store_no

        if not store_no:
            invalid += 1
            continue

        task = {
            "portal_task_id": portal_task_id or "",
            "store_no": store_no,
            "sla_date": sla_date,
            "created_at": created_at,
            "incident_type": incident_type,
            "text": text,
            "status": status,
            "location": location,
        }

        if not task["portal_task_id"]:
            task["portal_task_id"] = make_portal_task_id(task)

        tasks.append(task)

    return ParseResult(
        tasks=tasks,
        total=len(df),
        invalid=invalid,
        headers=headers,
    )
