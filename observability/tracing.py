"""
Distributed tracing system for Brain Swarm
Provides correlation IDs, request tracing, and performance monitoring
"""

import time
import uuid
import contextvars
from typing import Dict, Any, Optional, List, ContextManager
from contextlib import contextmanager
import json

from core.base import logger


# Context variables for distributed tracing
correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'correlation_id', default=None
)
trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'trace_id', default=None
)
span_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'span_id', default=None
)
parent_span_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'parent_span_id', default=None
)


class TraceSpan:
    """Represents a single span in a distributed trace"""

    def __init__(self, name: str, service_name: str = "brain-swarm",
                 span_kind: str = "internal", trace_id: Optional[str] = None,
                 parent_span_id: Optional[str] = None):
        self.span_id = str(uuid.uuid4())
        self.trace_id = trace_id or str(uuid.uuid4())
        self.parent_span_id = parent_span_id
        self.name = name
        self.service_name = service_name
        self.span_kind = span_kind
        self.start_time = time.time_ns()
        self.end_time: Optional[int] = None
        self.duration_ns: Optional[int] = None
        self.tags: Dict[str, Any] = {}
        self.logs: List[Dict[str, Any]] = []
        self.status_code = "OK"
        self.status_message = ""

    def set_tag(self, key: str, value: Any):
        """Set a tag on the span"""
        self.tags[key] = value

    def log(self, event: str, **kwargs):
        """Add a log event to the span"""
        log_entry = {
            "timestamp": time.time_ns(),
            "event": event,
            **kwargs
        }
        self.logs.append(log_entry)

    def set_status(self, code: str, message: str = ""):
        """Set the span status"""
        self.status_code = code
        self.status_message = message

    def finish(self):
        """Finish the span"""
        self.end_time = time.time_ns()
        self.duration_ns = self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary for serialization"""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "service_name": self.service_name,
            "span_kind": self.span_kind,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ns": self.duration_ns,
            "tags": self.tags,
            "logs": self.logs,
            "status_code": self.status_code,
            "status_message": self.status_message
        }


class TracingManager:
    """Manages distributed tracing across the Brain Swarm system"""

    def __init__(self):
        self.active_spans: Dict[str, TraceSpan] = {}
        self.completed_spans: List[TraceSpan] = []
        self.max_completed_spans = 10000  # Keep last 10k spans in memory
        self.exporters: List[callable] = []

    def register_exporter(self, exporter: callable):
        """Register a span exporter"""
        self.exporters.append(exporter)

    def unregister_exporter(self, exporter: callable):
        """Unregister a span exporter"""
        if exporter in self.exporters:
            self.exporters.remove(exporter)

    def start_span(self, name: str, service_name: str = "brain-swarm",
                  span_kind: str = "internal", tags: Dict[str, Any] = None) -> TraceSpan:
        """Start a new span"""
        # Get current context
        current_trace_id = trace_id_var.get()
        current_span_id = span_id_var.get()

        # Create new span
        span = TraceSpan(
            name=name,
            service_name=service_name,
            span_kind=span_kind,
            trace_id=current_trace_id,
            parent_span_id=current_span_id
        )

        # Set tags if provided
        if tags:
            for key, value in tags.items():
                span.set_tag(key, value)

        # Store active span
        self.active_spans[span.span_id] = span

        # Update context variables
        trace_id_var.set(span.trace_id)
        span_id_var.set(span.span_id)
        parent_span_id_var.set(span.parent_span_id)

        return span

    def finish_span(self, span: TraceSpan):
        """Finish a span and export it"""
        span.finish()

        # Remove from active spans
        if span.span_id in self.active_spans:
            del self.active_spans[span.span_id]

        # Add to completed spans
        self.completed_spans.append(span)

        # Maintain size limit
        if len(self.completed_spans) > self.max_completed_spans:
            self.completed_spans.pop(0)

        # Export span
        self._export_span(span)

        # Log span completion
        logger.log("DEBUG", "TracingManager", f"Span finished: {span.name}",
                  {"span_id": span.span_id, "duration_ns": span.duration_ns})

    def _export_span(self, span: TraceSpan):
        """Export span to all registered exporters"""
        for exporter in self.exporters:
            try:
                exporter(span)
            except Exception as e:
                logger.log("ERROR", "TracingManager", f"Failed to export span: {e}",
                          {"span_id": span.span_id, "exporter": str(exporter)})

    @contextmanager
    def trace_context(self, name: str, service_name: str = "brain-swarm",
                     span_kind: str = "internal", tags: Dict[str, Any] = None):
        """Context manager for tracing a block of code"""
        span = self.start_span(name, service_name, span_kind, tags)
        try:
            yield span
        except Exception as e:
            span.set_status("ERROR", str(e))
            span.log("exception", error=str(e), error_type=type(e).__name__)
            raise
        finally:
            self.finish_span(span)

    def get_current_trace_id(self) -> Optional[str]:
        """Get the current trace ID"""
        return trace_id_var.get()

    def get_current_span_id(self) -> Optional[str]:
        """Get the current span ID"""
        return span_id_var.get()

    def get_correlation_id(self) -> str:
        """Get or create a correlation ID for the current request"""
        correlation_id = correlation_id_var.get()
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            correlation_id_var.set(correlation_id)
        return correlation_id

    def set_correlation_id(self, correlation_id: str):
        """Set the correlation ID for the current request"""
        correlation_id_var.set(correlation_id)

    def get_trace_context(self) -> Dict[str, Optional[str]]:
        """Get the current trace context"""
        return {
            "correlation_id": correlation_id_var.get(),
            "trace_id": trace_id_var.get(),
            "span_id": span_id_var.get(),
            "parent_span_id": parent_span_id_var.get()
        }

    def set_trace_context(self, context: Dict[str, Optional[str]]):
        """Set the trace context from an external source"""
        if "correlation_id" in context:
            correlation_id_var.set(context["correlation_id"])
        if "trace_id" in context:
            trace_id_var.set(context["trace_id"])
        if "span_id" in context:
            span_id_var.set(context["span_id"])
        if "parent_span_id" in context:
            parent_span_id_var.set(context["parent_span_id"])

    def get_active_spans(self) -> List[TraceSpan]:
        """Get all currently active spans"""
        return list(self.active_spans.values())

    def get_completed_spans(self, trace_id: Optional[str] = None,
                           limit: int = 100) -> List[TraceSpan]:
        """Get completed spans, optionally filtered by trace ID"""
        spans = self.completed_spans

        if trace_id:
            spans = [span for span in spans if span.trace_id == trace_id]

        return spans[-limit:] if limit else spans

    def get_trace_tree(self, trace_id: str) -> Dict[str, Any]:
        """Build a trace tree for visualization"""
        spans = self.get_completed_spans(trace_id, limit=None)
        spans.extend([span for span in self.active_spans.values() if span.trace_id == trace_id])

        if not spans:
            return {"error": "Trace not found"}

        # Build span tree
        span_map = {span.span_id: span for span in spans}
        root_spans = []

        for span in spans:
            if span.parent_span_id is None or span.parent_span_id not in span_map:
                root_spans.append(span)

        def build_tree(span: TraceSpan) -> Dict[str, Any]:
            children = [build_tree(child) for child in spans
                       if child.parent_span_id == span.span_id]

            return {
                "span": span.to_dict(),
                "children": children
            }

        return {
            "trace_id": trace_id,
            "root_spans": [build_tree(root) for root in root_spans],
            "total_spans": len(spans),
            "duration_ns": max((span.end_time or time.time_ns()) - span.start_time
                             for span in spans) if spans else 0
        }


# Default console exporter for spans
def console_span_exporter(span: TraceSpan):
    """Export spans to console for debugging"""
    print(f"[TRACE] {span.service_name}:{span.name} - {span.duration_ns or 'active'}ns")


# JSON file exporter for spans
class JSONFileSpanExporter:
    """Export spans to a JSON file"""

    def __init__(self, filename: str):
        self.filename = filename

    def __call__(self, span: TraceSpan):
        """Export a span to the JSON file"""
        try:
            # Read existing spans
            try:
                with open(self.filename, 'r') as f:
                    spans = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                spans = []

            # Add new span
            spans.append(span.to_dict())

            # Keep only last 1000 spans
            if len(spans) > 1000:
                spans = spans[-1000:]

            # Write back
            with open(self.filename, 'w') as f:
                json.dump(spans, f, indent=2, default=str)

        except Exception as e:
            logger.log("ERROR", "JSONFileSpanExporter", f"Failed to export span: {e}")


# Global tracing manager instance
tracing_manager = TracingManager()

# Register default console exporter
tracing_manager.register_exporter(console_span_exporter)


# Convenience functions for easy tracing
def start_trace(name: str, **tags) -> ContextManager[TraceSpan]:
    """Start a trace context manager"""
    return tracing_manager.trace_context(name, tags=tags)


def get_correlation_id() -> str:
    """Get the current correlation ID"""
    return tracing_manager.get_correlation_id()


def set_correlation_id(correlation_id: str):
    """Set the correlation ID"""
    tracing_manager.set_correlation_id(correlation_id)


def get_trace_context() -> Dict[str, Optional[str]]:
    """Get the current trace context"""
    return tracing_manager.get_trace_context()


def set_trace_context(context: Dict[str, Optional[str]]):
    """Set the trace context"""
    tracing_manager.set_trace_context(context)