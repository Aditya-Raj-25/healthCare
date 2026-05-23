import structlog
import time
from typing import Dict, Optional

logger = structlog.get_logger(__name__)

class LatencyTracker:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.start_time = time.time()
        self.metrics: Dict[str, float] = {}

    def mark(self, phase: str):
        """Marks the latency duration since the tracker started for a specific phase."""
        self.metrics[f"latency_{phase}_ms"] = round((time.time() - self.start_time) * 1000, 2)

    def log_metrics(self, active_workflow_stage: Optional[str] = None):
        """Emits structured log with collected metrics."""
        self.metrics["latency_total_ms"] = round((time.time() - self.start_time) * 1000, 2)
        logger.info(
            "Orchestration Cycle Metrics",
            session_id=self.session_id,
            active_workflow_stage=active_workflow_stage,
            **self.metrics
        )
