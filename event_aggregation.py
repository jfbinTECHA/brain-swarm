"""
Event Aggregation Layer for Brain Swarm
Handles high-volume event processing from hundreds/thousands of swarm nodes.
Provides scalable event collection, processing, and distribution.
"""

import asyncio
import json
import time
import threading
import heapq
from typing import Dict, List, Any, Optional, Callable, Set
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import logging
import hashlib
import random

logger = logging.getLogger(__name__)

class EventPriority(Enum):
    """Event priority levels for processing"""
    CRITICAL = 0  # System failures, security breaches
    HIGH = 1      # Node failures, task failures
    MEDIUM = 2    # Status changes, performance alerts
    LOW = 3       # Routine updates, heartbeats
    DEBUG = 4     # Debug information

class EventType(Enum):
    """Supported event types"""
    NODE_STATUS = "node_status"
    TASK_UPDATE = "task_update"
    DISCOVERY_EVENT = "discovery_event"
    SECURITY_EVENT = "security_event"
    PERFORMANCE_METRIC = "performance_metric"
    HEARTBEAT = "heartbeat"
    SYSTEM_ALERT = "system_alert"

@dataclass
class AggregatedEvent:
    """Represents an aggregated event with metadata"""
    event_id: str
    event_type: EventType
    priority: EventPriority
    source_node: str
    swarm_id: str
    timestamp: float
    data: Dict[str, Any]
    batch_id: Optional[str] = None
    processing_attempts: int = 0
    created_at: float = field(default_factory=time.time)

@dataclass
class EventBatch:
    """Represents a batch of events for processing"""
    batch_id: str
    events: List[AggregatedEvent]
    priority: EventPriority
    created_at: float
    size_bytes: int
    source_count: int  # Number of different sources

class EventFilter:
    """Event filtering and routing rules"""

    def __init__(self, name: str, condition: Callable[[AggregatedEvent], bool],
                 action: str, priority_boost: int = 0):
        self.name = name
        self.condition = condition
        self.action = action  # 'drop', 'prioritize', 'route', 'batch'
        self.priority_boost = priority_boost

class AggregationMetrics:
    """Metrics for monitoring aggregation performance"""

    def __init__(self):
        self.events_received = 0
        self.events_processed = 0
        self.events_dropped = 0
        self.batches_created = 0
        self.batches_processed = 0
        self.avg_processing_time = 0.0
        self.peak_queue_size = 0
        self.current_queue_size = 0
        self.node_count = 0
        self.active_connections = 0
        self.error_count = 0
        self.last_health_check = time.time()

class EventAggregationService:
    """
    High-performance event aggregation service for swarm monitoring.
    Handles event collection, batching, filtering, and distribution at scale.
    """

    def __init__(self,
                 max_queue_size: int = 100000,
                 batch_size: int = 100,
                 batch_timeout: float = 1.0,
                 max_workers: int = 4,
                 enable_buffering: bool = True,
                 buffer_size: int = 50000):
        """
        Initialize the event aggregation service.

        Args:
            max_queue_size: Maximum events in processing queue
            batch_size: Target batch size for processing
            batch_timeout: Maximum time to wait for batch completion
            max_workers: Number of worker threads for processing
            enable_buffering: Enable event buffering for high throughput
            buffer_size: Size of circular buffer for recent events
        """
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_workers = max_workers
        self.enable_buffering = enable_buffering
        self.buffer_size = buffer_size

        # Event processing queues
        self.event_queue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self.processing_queue = asyncio.Queue()
        self.batch_queue = asyncio.Queue()
        self._event_counter = 0  # For tie-breaking in priority queue

        # Event storage
        self.event_buffer = deque(maxlen=buffer_size) if enable_buffering else None
        self.event_store = {}  # event_id -> AggregatedEvent
        self.batch_store = {}  # batch_id -> EventBatch

        # Processing state
        self.running = False
        self.workers = []
        self.batch_tasks = []

        # Filters and routing
        self.filters: List[EventFilter] = []
        self.route_handlers: Dict[str, Callable] = {}

        # Metrics and monitoring
        self.metrics = AggregationMetrics()
        self.node_health = {}  # node_id -> last_heartbeat
        self.swarm_stats = defaultdict(lambda: {'node_count': 0, 'event_rate': 0})

        # Load balancing
        self.instance_id = f"aggregator_{random.randint(1000, 9999)}"
        self.load_balance_peers = set()
        self.load_balance_interval = 30  # seconds

        # Initialize default filters
        self._setup_default_filters()

        logger.info(f"EventAggregationService initialized: {self.instance_id}")

    def _setup_default_filters(self):
        """Set up default event filtering rules"""

        # High priority events
        self.add_filter(EventFilter(
            "critical_events",
            lambda e: e.priority == EventPriority.CRITICAL,
            "prioritize",
            priority_boost=2
        ))

        # Security events
        self.add_filter(EventFilter(
            "security_events",
            lambda e: e.event_type == EventType.SECURITY_EVENT,
            "prioritize",
            priority_boost=1
        ))

        # Drop debug events in production
        self.add_filter(EventFilter(
            "drop_debug",
            lambda e: e.priority == EventPriority.DEBUG and not self._is_debug_mode(),
            "drop"
        ))

        # Batch routine heartbeats
        self.add_filter(EventFilter(
            "batch_heartbeats",
            lambda e: e.event_type == EventType.HEARTBEAT,
            "batch"
        ))

    def _is_debug_mode(self) -> bool:
        """Check if debug mode is enabled"""
        return False  # Could be configurable

    async def start_service(self):
        """Start the event aggregation service"""
        self.running = True
        logger.info("Starting Event Aggregation Service...")

        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._event_processor(i))
            self.workers.append(worker)

        # Start batching task
        batcher = asyncio.create_task(self._batch_processor())
        self.batch_tasks.append(batcher)

        # Start health monitoring
        health_monitor = asyncio.create_task(self._health_monitor())
        self.batch_tasks.append(health_monitor)

        # Start load balancing
        load_balancer = asyncio.create_task(self._load_balancer())
        self.batch_tasks.append(load_balancer)

        logger.info(f"Event Aggregation Service started with {self.max_workers} workers")

    async def stop_service(self):
        """Stop the event aggregation service"""
        self.running = False
        logger.info("Stopping Event Aggregation Service...")

        # Cancel all tasks
        for worker in self.workers:
            worker.cancel()
        for task in self.batch_tasks:
            task.cancel()

        # Wait for completion
        await asyncio.gather(*self.workers, *self.batch_tasks, return_exceptions=True)
        logger.info("Event Aggregation Service stopped")

    async def submit_event(self, event_data: Dict[str, Any], source_ip: str = None) -> bool:
        """
        Submit an event for processing.

        Args:
            event_data: Event data dictionary
            source_ip: Source IP address for rate limiting

        Returns:
            True if event was accepted, False if rejected
        """
        try:
            # Create aggregated event
            event = AggregatedEvent(
                event_id=event_data.get('event_id', f"evt_{int(time.time() * 1000000)}"),
                event_type=EventType(event_data.get('event_type', 'node_status')),
                priority=EventPriority(event_data.get('priority', EventPriority.MEDIUM.value)),
                source_node=event_data.get('source_node', 'unknown'),
                swarm_id=event_data.get('swarm_id', 'default'),
                timestamp=event_data.get('timestamp', time.time()),
                data=event_data.get('data', {})
            )

            # Apply filters
            filtered_event = self._apply_filters(event)
            if filtered_event is None:
                self.metrics.events_dropped += 1
                return False

            # Update metrics
            self.metrics.events_received += 1
            self.metrics.current_queue_size = self.event_queue.qsize()

            # Add to buffer if enabled
            if self.event_buffer is not None:
                self.event_buffer.append(filtered_event)

            # Update node health
            if filtered_event.event_type == EventType.HEARTBEAT:
                self.node_health[filtered_event.source_node] = filtered_event.timestamp

            # Update swarm stats
            swarm_id = filtered_event.swarm_id
            self.swarm_stats[swarm_id]['event_rate'] += 1

            # Store event
            self.event_store[filtered_event.event_id] = filtered_event

            # Add to processing queue with priority (priority, counter, event)
            priority_value = filtered_event.priority.value
            self._event_counter += 1
            await self.event_queue.put((priority_value, self._event_counter, filtered_event))

            return True

        except Exception as e:
            logger.error(f"Error submitting event: {e}")
            self.metrics.error_count += 1
            return False

    def _apply_filters(self, event: AggregatedEvent) -> Optional[AggregatedEvent]:
        """Apply filtering rules to an event"""
        for filter_rule in self.filters:
            if filter_rule.condition(event):
                if filter_rule.action == 'drop':
                    return None
                elif filter_rule.action == 'prioritize':
                    # Boost priority
                    new_priority_value = max(0, event.priority.value - filter_rule.priority_boost)
                    event.priority = EventPriority(new_priority_value)
                elif filter_rule.action == 'route':
                    # Route to specific handler
                    handler = self.route_handlers.get(filter_rule.name)
                    if handler:
                        try:
                            handler(event)
                        except Exception as e:
                            logger.error(f"Error in route handler {filter_rule.name}: {e}")
                # 'batch' action is handled by batch processor

        return event

    async def _event_processor(self, worker_id: int):
        """Worker task for processing individual events"""
        logger.info(f"Event processor {worker_id} started")

        while self.running:
            try:
                # Get next event from priority queue
                priority, counter, event = await self.event_queue.get()

                start_time = time.time()

                # Process the event
                await self._process_single_event(event)

                # Update metrics
                processing_time = time.time() - start_time
                self.metrics.events_processed += 1
                self.metrics.avg_processing_time = (
                    (self.metrics.avg_processing_time * (self.metrics.events_processed - 1)) +
                    processing_time
                ) / self.metrics.events_processed

                self.event_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in event processor {worker_id}: {e}")
                self.metrics.error_count += 1

        logger.info(f"Event processor {worker_id} stopped")

    async def _process_single_event(self, event: AggregatedEvent):
        """Process a single event"""
        try:
            # Route to appropriate handlers
            route_key = f"{event.event_type.value}_{event.swarm_id}"
            handler = self.route_handlers.get(route_key)

            if handler:
                await handler(event)
            else:
                # Default processing - add to batch queue
                await self.processing_queue.put(event)

        except Exception as e:
            logger.error(f"Error processing event {event.event_id}: {e}")
            event.processing_attempts += 1

            # Retry logic
            if event.processing_attempts < 3:
                # Re-queue with lower priority
                retry_priority = min(4, event.priority.value + 1)
                await asyncio.sleep(0.1 * event.processing_attempts)  # Exponential backoff
                self._event_counter += 1
                await self.event_queue.put((retry_priority, self._event_counter, event))
            else:
                logger.error(f"Event {event.event_id} failed after {event.processing_attempts} attempts")

    async def _batch_processor(self):
        """Process events in batches for efficiency"""
        logger.info("Batch processor started")

        batch_buffer = defaultdict(list)
        batch_timers = {}

        while self.running:
            try:
                # Wait for events or timeout
                try:
                    event = await asyncio.wait_for(
                        self.processing_queue.get(),
                        timeout=self.batch_timeout
                    )
                except asyncio.TimeoutError:
                    # Process any pending batches
                    await self._flush_batches(batch_buffer)
                    continue

                # Add event to appropriate batch
                batch_key = f"{event.event_type.value}_{event.swarm_id}"
                batch_buffer[batch_key].append(event)

                # Check if batch is ready
                if len(batch_buffer[batch_key]) >= self.batch_size:
                    await self._create_and_queue_batch(batch_key, batch_buffer[batch_key])
                    batch_buffer[batch_key] = []

                # Update batch timer
                if batch_key not in batch_timers:
                    batch_timers[batch_key] = asyncio.create_task(
                        self._batch_timeout_handler(batch_key, batch_buffer, batch_timers)
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")

        # Flush remaining batches
        await self._flush_batches(batch_buffer)

        logger.info("Batch processor stopped")

    async def _batch_timeout_handler(self, batch_key: str, batch_buffer: Dict,
                                   batch_timers: Dict):
        """Handle batch timeout"""
        await asyncio.sleep(self.batch_timeout)

        if batch_key in batch_buffer and batch_buffer[batch_key]:
            await self._create_and_queue_batch(batch_key, batch_buffer[batch_key])
            batch_buffer[batch_key] = []

        if batch_key in batch_timers:
            del batch_timers[batch_key]

    async def _create_and_queue_batch(self, batch_key: str, events: List[AggregatedEvent]):
        """Create a batch from events and queue it"""
        if not events:
            return

        batch_id = f"batch_{batch_key}_{int(time.time() * 1000)}"

        # Calculate batch size
        size_bytes = sum(len(json.dumps(e.data).encode()) for e in events)
        source_count = len(set(e.source_node for e in events))

        # Determine batch priority (highest priority of events)
        batch_priority = min(events, key=lambda e: e.priority.value).priority

        batch = EventBatch(
            batch_id=batch_id,
            events=events,
            priority=batch_priority,
            created_at=time.time(),
            size_bytes=size_bytes,
            source_count=source_count
        )

        # Store batch
        self.batch_store[batch_id] = batch

        # Update metrics
        self.metrics.batches_created += 1

        # Queue for processing
        await self.batch_queue.put(batch)

    async def _flush_batches(self, batch_buffer: Dict):
        """Flush all pending batches"""
        for batch_key, events in batch_buffer.items():
            if events:
                await self._create_and_queue_batch(batch_key, events)

        batch_buffer.clear()

    async def _health_monitor(self):
        """Monitor system health and performance"""
        while self.running:
            try:
                await asyncio.sleep(10)  # Health check every 10 seconds

                # Update metrics
                self.metrics.last_health_check = time.time()
                self.metrics.node_count = len(self.node_health)
                self.metrics.active_connections = len([
                    node for node, last_heartbeat in self.node_health.items()
                    if time.time() - last_heartbeat < 60  # Active in last minute
                ])

                # Check for dead nodes
                dead_nodes = [
                    node for node, last_heartbeat in self.node_health.items()
                    if time.time() - last_heartbeat > 300  # No heartbeat for 5 minutes
                ]

                if dead_nodes:
                    logger.warning(f"Detected {len(dead_nodes)} dead nodes: {dead_nodes[:5]}...")

                # Log performance stats
                if self.metrics.events_processed > 0:
                    logger.info(
                        f"Aggregation stats: {self.metrics.events_processed} events processed, "
                        f"avg time: {self.metrics.avg_processing_time:.3f}s, "
                        f"queue size: {self.metrics.current_queue_size}, "
                        f"active nodes: {self.metrics.active_connections}"
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")

    async def _load_balancer(self):
        """Handle load balancing across multiple aggregation instances"""
        while self.running:
            try:
                await asyncio.sleep(self.load_balance_interval)

                # In a real distributed system, this would:
                # 1. Discover other aggregation instances
                # 2. Share load information
                # 3. Redistribute events if overloaded
                # 4. Handle failover scenarios

                # For now, just log load status
                load_factor = self.metrics.current_queue_size / self.max_queue_size
                if load_factor > 0.8:
                    logger.warning(f"High load detected: {load_factor:.1%} queue utilization")
                elif load_factor > 0.6:
                    logger.info(f"Moderate load: {load_factor:.1%} queue utilization")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in load balancer: {e}")

    def add_filter(self, filter_rule: EventFilter):
        """Add an event filtering rule"""
        self.filters.append(filter_rule)
        logger.info(f"Added filter: {filter_rule.name}")

    def add_route_handler(self, route_key: str, handler: Callable):
        """Add a route handler for specific event types"""
        self.route_handlers[route_key] = handler
        logger.info(f"Added route handler: {route_key}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get current aggregation metrics"""
        return {
            'events_received': self.metrics.events_received,
            'events_processed': self.metrics.events_processed,
            'events_dropped': self.metrics.events_dropped,
            'batches_created': self.metrics.batches_created,
            'batches_processed': self.metrics.batches_processed,
            'avg_processing_time': round(self.metrics.avg_processing_time, 3),
            'current_queue_size': self.metrics.current_queue_size,
            'max_queue_size': self.max_queue_size,
            'peak_queue_size': self.metrics.peak_queue_size,
            'node_count': self.metrics.node_count,
            'active_connections': self.metrics.active_connections,
            'error_count': self.metrics.error_count,
            'last_health_check': self.metrics.last_health_check,
            'instance_id': self.instance_id
        }

    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events from buffer"""
        if not self.event_buffer:
            return []

        events = list(self.event_buffer)[-limit:]
        return [{
            'event_id': e.event_id,
            'event_type': e.event_type.value,
            'priority': e.priority.value,
            'source_node': e.source_node,
            'swarm_id': e.swarm_id,
            'timestamp': e.timestamp,
            'data': e.data
        } for e in events]

    def get_swarm_stats(self) -> Dict[str, Any]:
        """Get statistics per swarm"""
        stats = {}
        current_time = time.time()

        for swarm_id, swarm_data in self.swarm_stats.items():
            # Calculate event rate per minute
            event_rate = swarm_data['event_rate'] / max(1, current_time - getattr(self, '_last_swarm_reset', current_time))
            stats[swarm_id] = {
                'node_count': swarm_data['node_count'],
                'event_rate_per_minute': round(event_rate * 60, 1)
            }

        # Reset counters periodically
        if not hasattr(self, '_last_swarm_reset'):
            self._last_swarm_reset = current_time
        elif current_time - self._last_swarm_reset > 60:  # Reset every minute
            for swarm_data in self.swarm_stats.values():
                swarm_data['event_rate'] = 0
            self._last_swarm_reset = current_time

        return stats

    async def query_events(self, filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Query events with filters"""
        matching_events = []

        # Search through stored events (in production, this would use a proper database)
        for event in self.event_store.values():
            if self._matches_filters(event, filters):
                matching_events.append({
                    'event_id': event.event_id,
                    'event_type': event.event_type.value,
                    'priority': event.priority.value,
                    'source_node': event.source_node,
                    'swarm_id': event.swarm_id,
                    'timestamp': event.timestamp,
                    'data': event.data
                })

                if len(matching_events) >= limit:
                    break

        return matching_events

    def _matches_filters(self, event: AggregatedEvent, filters: Dict[str, Any]) -> bool:
        """Check if event matches the given filters"""
        if 'event_type' in filters and event.event_type.value != filters['event_type']:
            return False
        if 'source_node' in filters and event.source_node != filters['source_node']:
            return False
        if 'swarm_id' in filters and event.swarm_id != filters['swarm_id']:
            return False
        if 'priority' in filters and event.priority.value != filters['priority']:
            return False
        if 'start_time' in filters and event.timestamp < filters['start_time']:
            return False
        if 'end_time' in filters and event.timestamp > filters['end_time']:
            return False

        return True