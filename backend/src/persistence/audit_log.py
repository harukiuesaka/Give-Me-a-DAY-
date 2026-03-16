"""
Append-only JSONL audit event logging.

Storage layout follows api_data_flow.md §7.
Each event is one JSON line, never modified or deleted.
"""

import json
from pathlib import Path

from src.config import settings
from src.domain.models import AuditEvent


class AuditLogger:
    """Append-only JSONL audit event logger."""

    def __init__(self, data_dir: str | None = None):
        self.data_dir = Path(data_dir or settings.DATA_DIR) / "audit_log"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def append_event(self, event: AuditEvent) -> None:
        """Append an audit event to the appropriate JSONL file."""
        if event.paper_run_id:
            log_dir = self.data_dir / event.paper_run_id
        else:
            log_dir = self.data_dir / event.run_id

        log_dir.mkdir(parents=True, exist_ok=True)

        # Determine file based on event type
        if event.event_type.startswith("paper_run."):
            filename = "runtime_events.jsonl"
        elif event.event_type.startswith("re_evaluation."):
            filename = "re_evaluation_events.jsonl"
        elif event.event_type.startswith("approval.") or event.event_type.startswith(
            "re_approval."
        ):
            filename = "approval_events.jsonl"
        else:
            filename = "pipeline_events.jsonl"

        filepath = log_dir / filename
        line = event.model_dump_json() + "\n"
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(line)

    def read_events(self, entity_id: str, filename: str = "pipeline_events.jsonl") -> list[dict]:
        """Read all events from a specific log file."""
        filepath = self.data_dir / entity_id / filename
        if not filepath.exists():
            return []

        events = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events
