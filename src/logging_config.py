"""
Logging configuration for the Stock Market AI Agent.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: bool = False,
    log_dir: str = "logs"
) -> logging.Logger:
    """
    Configure application logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Whether to also log to file
        log_dir: Directory for log files

    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger("stock_agent")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    logger.handlers.clear()

    # Format
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        file_handler = logging.FileHandler(
            log_path / f"agent_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "stock_agent") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


# Metrics tracking
class MetricsCollector:
    """Simple metrics collector for tracking agent performance."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all metrics."""
        self._metrics = {
            "tool_calls": {},
            "errors": [],
            "response_times": [],
            "cache_hits": 0,
            "cache_misses": 0,
        }

    def record_tool_call(self, tool_name: str, success: bool, duration_ms: float):
        """Record a tool execution."""
        if tool_name not in self._metrics["tool_calls"]:
            self._metrics["tool_calls"][tool_name] = {
                "count": 0,
                "success": 0,
                "failed": 0,
                "total_time_ms": 0,
            }

        self._metrics["tool_calls"][tool_name]["count"] += 1
        self._metrics["tool_calls"][tool_name]["total_time_ms"] += duration_ms

        if success:
            self._metrics["tool_calls"][tool_name]["success"] += 1
        else:
            self._metrics["tool_calls"][tool_name]["failed"] += 1

    def record_error(self, error_type: str, message: str):
        """Record an error."""
        self._metrics["errors"].append({
            "type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        })

    def record_response_time(self, time_ms: float):
        """Record agent response time."""
        self._metrics["response_times"].append(time_ms)

    def record_cache_hit(self):
        """Record a cache hit."""
        self._metrics["cache_hits"] += 1

    def record_cache_miss(self):
        """Record a cache miss."""
        self._metrics["cache_misses"] += 1

    def get_summary(self) -> dict:
        """Get metrics summary."""
        response_times = self._metrics["response_times"]
        avg_response = sum(response_times) / len(response_times) if response_times else 0

        return {
            "total_tool_calls": sum(
                t["count"] for t in self._metrics["tool_calls"].values()
            ),
            "tool_breakdown": self._metrics["tool_calls"],
            "total_errors": len(self._metrics["errors"]),
            "recent_errors": self._metrics["errors"][-5:],
            "avg_response_time_ms": round(avg_response, 2),
            "cache_hit_rate": self._calculate_cache_hit_rate(),
        }

    def _calculate_cache_hit_rate(self) -> float:
        total = self._metrics["cache_hits"] + self._metrics["cache_misses"]
        if total == 0:
            return 0.0
        return round(self._metrics["cache_hits"] / total * 100, 2)


# Global metrics instance
metrics = MetricsCollector()
