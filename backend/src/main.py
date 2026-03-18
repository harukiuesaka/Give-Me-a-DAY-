"""FastAPI app entry point for Give Me a DAY v1."""

import logging
import uuid
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.dependencies import get_store
from src.config import settings
from src.api.routes import router
from src.pipeline.runtime_controller import (
    ensure_runtime_runner_lease,
    reconcile_active_paper_runs,
)

logger = logging.getLogger(__name__)


def _runtime_runner_loop(stop_event: threading.Event) -> None:
    store = get_store()
    runner_id = f"runner_{uuid.uuid4().hex[:8]}"
    while not stop_event.is_set():
        try:
            if ensure_runtime_runner_lease(store, runner_id):
                reconcile_active_paper_runs(store)
                ensure_runtime_runner_lease(store, runner_id)
            else:
                logger.warning("Runtime lifecycle runner lease is held by another instance; waiting for takeover.")
        except Exception:
            logger.exception("Runtime lifecycle runner failed during reconciliation cycle")
        stop_event.wait(settings.RUNTIME_RUNNER_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    stop_event = threading.Event()
    runner = threading.Thread(
        target=_runtime_runner_loop,
        args=(stop_event,),
        daemon=True,
        name="paper-run-lifecycle-runner",
    )
    runner.start()
    try:
        yield
    finally:
        stop_event.set()
        runner.join(timeout=1.0)

app = FastAPI(
    title="Give Me a DAY",
    version="1.0.0",
    description="Validation-first product for investment research and strategy validation",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
