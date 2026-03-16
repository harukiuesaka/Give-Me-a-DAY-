"""Shared dependencies for API endpoints."""

from src.persistence.store import PersistenceStore
from src.persistence.audit_log import AuditLogger

# Singleton instances used across the application
_store: PersistenceStore | None = None
_audit_logger: AuditLogger | None = None


def get_store() -> PersistenceStore:
    global _store
    if _store is None:
        _store = PersistenceStore()
    return _store


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
