"""
File-based persistence store (JSON + Parquet).

Storage layout follows api_data_flow.md §6.
Every write validates against Pydantic model before saving.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Type, TypeVar

import pandas as pd
from pydantic import BaseModel

from src.config import settings

T = TypeVar("T", bound=BaseModel)


class PersistenceStore:
    """File-based persistence for Give Me a DAY v1."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir or settings.DATA_DIR)
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create base directory structure if it doesn't exist."""
        for subdir in ["runs", "paper_runs", "evidence/price", "evidence/macro",
                        "evidence/metadata", "audit_log", "runtime"]:
            (self.data_dir / subdir).mkdir(parents=True, exist_ok=True)

    def _run_dir(self, run_id: str) -> Path:
        d = self.data_dir / "runs" / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _pipeline_dir(self, run_id: str) -> Path:
        d = self._run_dir(run_id) / "pipeline"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _paper_run_dir(self, paper_run_id: str) -> Path:
        d = self.data_dir / "paper_runs" / paper_run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ---- Run metadata ----

    def save_run_meta(self, run_id: str, data: BaseModel) -> None:
        self._write_json(self._run_dir(run_id) / "meta.json", data)

    def load_run_meta(self, run_id: str) -> dict:
        return self._read_json(self._run_dir(run_id) / "meta.json")

    # ---- Pipeline objects (write-once) ----

    def save_run_object(self, run_id: str, object_type: str, data: BaseModel) -> None:
        """Save a pipeline object. object_type maps to filename."""
        path = self._pipeline_dir(run_id) / f"{object_type}.json"
        self._write_json(path, data)

    def load_run_object(self, run_id: str, object_type: str) -> dict:
        path = self._pipeline_dir(run_id) / f"{object_type}.json"
        return self._read_json(path)

    # ---- Candidate-scoped objects ----

    def save_candidate_object(
        self, run_id: str, collection: str, candidate_suffix: str, data: BaseModel
    ) -> None:
        """Save a per-candidate object (candidates/C01.json, audits/C01.json, etc.)."""
        d = self._pipeline_dir(run_id) / collection
        d.mkdir(parents=True, exist_ok=True)
        self._write_json(d / f"{candidate_suffix}.json", data)

    def load_candidate_object(
        self, run_id: str, collection: str, candidate_suffix: str
    ) -> dict:
        path = self._pipeline_dir(run_id) / collection / f"{candidate_suffix}.json"
        return self._read_json(path)

    def load_all_candidate_objects(self, run_id: str, collection: str) -> list[dict]:
        d = self._pipeline_dir(run_id) / collection
        if not d.exists():
            return []
        results = []
        for f in sorted(d.glob("*.json")):
            results.append(self._read_json(f))
        return results

    # ---- Presentation objects ----

    def save_presentation(self, run_id: str, filename: str, data: BaseModel) -> None:
        d = self._run_dir(run_id) / "presentation"
        d.mkdir(parents=True, exist_ok=True)
        self._write_json(d / filename, data)

    def save_presentation_list(
        self, run_id: str, filename: str, data_list: list[BaseModel]
    ) -> None:
        d = self._run_dir(run_id) / "presentation"
        d.mkdir(parents=True, exist_ok=True)
        path = d / filename
        json_data = [item.model_dump(mode="json") for item in data_list]
        path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_presentation(self, run_id: str, filename: str) -> dict | list:
        path = self._run_dir(run_id) / "presentation" / filename
        return self._read_json(path)

    # ---- Approval ----

    def save_approval(self, run_id: str, data: BaseModel) -> None:
        self._write_json(self._run_dir(run_id) / "approval.json", data)

    def load_approval(self, run_id: str) -> dict:
        return self._read_json(self._run_dir(run_id) / "approval.json")

    # ---- Runtime lifecycle ----

    def save_runtime_heartbeat(self, data: BaseModel) -> None:
        d = self.data_dir / "runtime"
        d.mkdir(parents=True, exist_ok=True)
        self._write_json(d / "runner_heartbeat.json", data)

    def load_runtime_heartbeat(self) -> dict | None:
        path = self.data_dir / "runtime" / "runner_heartbeat.json"
        if not path.exists():
            return None
        return self._read_json(path)

    # ---- Paper Run ----

    def save_paper_run_state(self, paper_run_id: str, data: BaseModel) -> None:
        d = self._paper_run_dir(paper_run_id)
        self._write_json(d / "state.json", data)

    def load_paper_run_state(self, paper_run_id: str) -> dict:
        return self._read_json(self._paper_run_dir(paper_run_id) / "state.json")

    def save_paper_run_snapshot(
        self, paper_run_id: str, date_str: str, data: BaseModel
    ) -> None:
        d = self._paper_run_dir(paper_run_id) / "snapshots"
        d.mkdir(parents=True, exist_ok=True)
        self._write_json(d / f"{date_str}.json", data)

    def save_paper_run_attention(self, paper_run_id: str, data: BaseModel) -> None:
        self._write_json(self._paper_run_dir(paper_run_id) / "attention.json", data)

    def load_paper_run_attention(self, paper_run_id: str) -> dict:
        return self._read_json(self._paper_run_dir(paper_run_id) / "attention.json")

    def load_paper_run_snapshots(self, paper_run_id: str) -> list[tuple[str, dict]]:
        d = self._paper_run_dir(paper_run_id) / "snapshots"
        if not d.exists():
            return []
        return [(f.stem, self._read_json(f)) for f in sorted(d.glob("*.json"))]

    def save_monthly_report(self, paper_run_id: str, report_id: str, data: BaseModel) -> None:
        d = self._paper_run_dir(paper_run_id) / "reports"
        d.mkdir(parents=True, exist_ok=True)
        self._write_json(d / f"{report_id}.json", data)

    def load_monthly_reports(self, paper_run_id: str) -> list[dict]:
        d = self._paper_run_dir(paper_run_id) / "reports"
        if not d.exists():
            return []
        return [self._read_json(f) for f in sorted(d.glob("*.json"))]

    def load_monthly_report(self, paper_run_id: str, report_id: str) -> dict:
        return self._read_json(
            self._paper_run_dir(paper_run_id) / "reports" / f"{report_id}.json"
        )

    def save_paper_run_lifecycle_event(
        self, paper_run_id: str, event_id: str, data: BaseModel
    ) -> None:
        d = self._paper_run_dir(paper_run_id) / "events"
        d.mkdir(parents=True, exist_ok=True)
        self._write_json(d / f"{event_id}.json", data)

    def load_paper_run_lifecycle_events(self, paper_run_id: str) -> list[dict]:
        d = self._paper_run_dir(paper_run_id) / "events"
        if not d.exists():
            return []
        events = [self._read_json(f) for f in sorted(d.glob("*.json"))]
        event_order = {
            "monthly_report_ready": 0,
            "quarterly_re_evaluation_outcome": 1,
            "reapproval_required": 2,
            "halted": 3,
        }
        events.sort(
            key=lambda item: (
                datetime.fromisoformat(item["timestamp"]),
                event_order.get(item.get("event_type", ""), 99),
                item.get("event_id", ""),
            )
        )
        return events

    def save_re_evaluation_result(
        self, paper_run_id: str, re_evaluation_id: str, data: BaseModel
    ) -> None:
        d = self._paper_run_dir(paper_run_id) / "re_evaluations"
        d.mkdir(parents=True, exist_ok=True)
        self._write_json(d / f"{re_evaluation_id}.json", data)

    def load_re_evaluation_results(self, paper_run_id: str) -> list[dict]:
        d = self._paper_run_dir(paper_run_id) / "re_evaluations"
        if not d.exists():
            return []
        return [self._read_json(f) for f in sorted(d.glob("*.json"))]

    def load_re_evaluation_result(self, paper_run_id: str, re_evaluation_id: str) -> dict:
        return self._read_json(
            self._paper_run_dir(paper_run_id) / "re_evaluations" / f"{re_evaluation_id}.json"
        )

    # ---- Evidence data (Parquet) ----

    def save_evidence_data(self, run_id: str, item_id: str, df: pd.DataFrame) -> None:
        d = self.data_dir / "evidence"
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{item_id}.parquet"
        df.to_parquet(path, engine="pyarrow")

    def load_evidence_data(self, run_id: str, item_id: str) -> pd.DataFrame:
        path = self.data_dir / "evidence" / f"{item_id}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Evidence data not found: {path}")
        return pd.read_parquet(path, engine="pyarrow")

    # ---- Markdown export ----

    def save_markdown_export(self, run_id: str, content: str) -> None:
        d = self._run_dir(run_id) / "presentation"
        d.mkdir(parents=True, exist_ok=True)
        (d / "markdown_export.md").write_text(content, encoding="utf-8")

    def load_markdown_export(self, run_id: str) -> str:
        path = self._run_dir(run_id) / "presentation" / "markdown_export.md"
        if not path.exists():
            raise FileNotFoundError(f"Markdown export not found: {path}")
        return path.read_text(encoding="utf-8")

    # ---- Internal helpers ----

    def _write_json(self, path: Path, data: BaseModel) -> None:
        """Validate via Pydantic and write JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        json_str = data.model_dump_json(indent=2)
        path.write_text(json_str, encoding="utf-8")

    def _read_json(self, path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def run_exists(self, run_id: str) -> bool:
        return (self.data_dir / "runs" / run_id / "meta.json").exists()

    def paper_run_exists(self, paper_run_id: str) -> bool:
        return (self.data_dir / "paper_runs" / paper_run_id / "state.json").exists()

    def list_paper_run_ids(self) -> list[str]:
        base = self.data_dir / "paper_runs"
        if not base.exists():
            return []
        return sorted(
            paper_run_dir.name
            for paper_run_dir in base.iterdir()
            if paper_run_dir.is_dir() and (paper_run_dir / "state.json").exists()
        )
