"""
Scheduled Summarizer Job for Knowledge Cortex
Handles event compaction and embedding pipeline
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

from ..core.base import logger, metrics
from .cortex import KnowledgeCortex
from .adapters.embedding_adapter import embedding_adapter
from ..message_queue import message_queue


class EventSummarizer:
    """Handles event compaction and summarization"""

    def __init__(self, cortex: KnowledgeCortex, config: Optional[Dict[str, Any]] = None):
        self.cortex = cortex
        self.config = config or self._default_config()
        self.last_run = 0
        self.summary_stats = {
            "events_processed": 0,
            "summaries_created": 0,
            "embeddings_generated": 0,
            "last_compaction": 0
        }

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for summarizer"""
        return {
            "compaction_interval_hours": 6,  # Run every 6 hours
            "max_events_per_summary": 100,   # Max events to summarize at once
            "summary_retention_days": 30,    # Keep summaries for 30 days
            "embedding_batch_size": 10,      # Process embeddings in batches
            "enable_real_time": True         # Enable real-time event processing
        }

    async def run_compaction_cycle(self) -> Dict[str, Any]:
        """Run a complete event compaction cycle"""
        start_time = time.time()
        logger.log("INFO", "EventSummarizer", "Starting event compaction cycle")

        try:
            # Collect events for summarization
            events = await self._collect_events_for_summarization()

            if not events:
                logger.log("INFO", "EventSummarizer", "No events to summarize")
                return {"status": "no_events", "events_processed": 0}

            # Group events by type/topic
            event_groups = self._group_events_by_topic(events)

            # Generate summaries for each group
            summaries = []
            for topic, topic_events in event_groups.items():
                summary = await self._generate_topic_summary(topic, topic_events)
                if summary:
                    summaries.append(summary)

            # Store summaries with embeddings
            stored_summaries = await self._store_summaries_with_embeddings(summaries)

            # Update statistics
            self.summary_stats["events_processed"] += len(events)
            self.summary_stats["summaries_created"] += len(stored_summaries)
            self.summary_stats["last_compaction"] = start_time

            # Clean up old summaries
            await self._cleanup_old_summaries()

            duration = time.time() - start_time
            logger.log("INFO", "EventSummarizer", f"Compaction cycle completed in {duration:.2f}s. "
                      f"Processed {len(events)} events, created {len(stored_summaries)} summaries")

            return {
                "status": "success",
                "events_processed": len(events),
                "summaries_created": len(stored_summaries),
                "duration_seconds": duration
            }

        except Exception as e:
            logger.log("ERROR", "EventSummarizer", f"Compaction cycle failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _collect_events_for_summarization(self) -> List[Dict[str, Any]]:
        """Collect events that need summarization"""
        # This would typically query a message queue or event store
        # For now, we'll simulate collecting recent events

        events = []

        # Get recent messages from message queue
        try:
            # This is a simplified implementation - in practice you'd have
            # a proper event store with timestamps
            recent_messages = await self._get_recent_events_from_queue()

            for msg in recent_messages:
                events.append({
                    "id": msg.get("id", f"event_{int(time.time())}_{len(events)}"),
                    "timestamp": msg.get("timestamp", time.time()),
                    "type": msg.get("message_type", "unknown"),
                    "content": msg.get("content", ""),
                    "sender": msg.get("sender", "unknown"),
                    "receiver": msg.get("receiver", "unknown"),
                    "metadata": msg.get("metadata", {})
                })

        except Exception as e:
            logger.log("WARNING", "EventSummarizer", f"Failed to collect events from queue: {e}")

        return events

    async def _get_recent_events_from_queue(self) -> List[Dict[str, Any]]:
        """Get recent events from message queue using Redis streams"""
        try:
            # Get recent messages from the message queue stream
            # Use the global message_queue instance
            from ..message_queue import message_queue

            # Get stream info to see recent activity
            stream_info = await message_queue.get_stream_info()
            if not stream_info:
                return []

            # Get recent messages from the stream
            # Read last N messages from the stream
            messages = await message_queue.redis.xrevrange(
                message_queue.stream_name, "+", "-", count=500
            )

            events = []
            cutoff_time = time.time() - (self.config["compaction_interval_hours"] * 3600)

            for message_id, message_data in messages:
                # Convert to event format
                try:
                    event = {
                        "id": message_id,
                        "timestamp": float(message_data.get("timestamp", time.time())),
                        "type": message_data.get("message_type", "unknown"),
                        "content": message_data.get("content", ""),
                        "sender": message_data.get("sender", "unknown"),
                        "receiver": message_data.get("receiver", "unknown"),
                        "metadata": message_data.get("metadata", {})
                    }

                    # Only include events within the compaction window
                    if event["timestamp"] >= cutoff_time:
                        events.append(event)
                    else:
                        break  # Since we're going backwards in time, we can stop

                except (ValueError, KeyError) as e:
                    logger.log("WARNING", "EventSummarizer", f"Failed to parse message {message_id}: {e}")
                    continue

            logger.log("INFO", "EventSummarizer", f"Retrieved {len(events)} events from message queue")
            return events

        except Exception as e:
            logger.log("ERROR", "EventSummarizer", f"Failed to get events from message queue: {e}")
            return []

    def _group_events_by_topic(self, events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group events by topic/type for summarization"""
        groups = {}

        for event in events:
            # Determine topic based on event type and content
            topic = self._determine_event_topic(event)

            if topic not in groups:
                groups[topic] = []

            groups[topic].append(event)

        return groups

    def _determine_event_topic(self, event: Dict[str, Any]) -> str:
        """Determine the topic/category of an event"""
        event_type = event.get("type", "unknown")

        # Simple topic determination based on event type
        if "task" in event_type.lower():
            return "task_execution"
        elif "agent" in event_type.lower():
            return "agent_activity"
        elif "coordination" in event_type.lower():
            return "coordination"
        elif "error" in event_type.lower() or "failure" in event_type.lower():
            return "errors_failures"
        elif "learning" in event_type.lower() or "improvement" in event_type.lower():
            return "learning_adaptation"
        else:
            return "general_activity"

    async def _generate_topic_summary(self, topic: str, events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate a summary for a topic"""
        if not events:
            return None

        try:
            # Extract key information from events
            summary_text = self._create_summary_text(topic, events)

            # Create summary object
            summary = {
                "id": f"summary_{topic}_{int(time.time())}",
                "topic": topic,
                "timestamp": time.time(),
                "event_count": len(events),
                "time_range": {
                    "start": min(e["timestamp"] for e in events),
                    "end": max(e["timestamp"] for e in events)
                },
                "summary_text": summary_text,
                "key_insights": self._extract_key_insights(events),
                "metrics": self._calculate_topic_metrics(events),
                "events_sample": events[:5]  # Sample of events
            }

            return summary

        except Exception as e:
            logger.log("ERROR", "EventSummarizer", f"Failed to generate summary for topic {topic}: {e}")
            return None

    def _create_summary_text(self, topic: str, events: List[Dict[str, Any]]) -> str:
        """Create a textual summary of events"""
        total_events = len(events)
        time_span = max(e["timestamp"] for e in events) - min(e["timestamp"] for e in events)
        time_span_hours = time_span / 3600

        # Count event types
        event_types = {}
        for event in events:
            etype = event.get("type", "unknown")
            event_types[etype] = event_types.get(etype, 0) + 1

        # Create summary
        summary_parts = [
            f"Topic: {topic.replace('_', ' ').title()}",
            f"Total Events: {total_events}",
            f"Time Span: {time_span_hours:.1f} hours",
            f"Event Types: {', '.join(f'{k}({v})' for k, v in event_types.items())}"
        ]

        # Add topic-specific insights
        if topic == "task_execution":
            completed_tasks = sum(1 for e in events if "completed" in str(e.get("content", "")).lower())
            summary_parts.append(f"Tasks Completed: {completed_tasks}")
        elif topic == "errors_failures":
            summary_parts.append("Focus: Error analysis and recovery patterns")
        elif topic == "learning_adaptation":
            summary_parts.append("Focus: System improvement and adaptation")

        return " | ".join(summary_parts)

    def _extract_key_insights(self, events: List[Dict[str, Any]]) -> List[str]:
        """Extract key insights from events"""
        insights = []

        # Simple pattern detection
        error_events = [e for e in events if "error" in str(e.get("content", "")).lower()]
        if error_events:
            insights.append(f"Observed {len(error_events)} error events")

        task_events = [e for e in events if "task" in str(e.get("content", "")).lower()]
        if task_events:
            insights.append(f"Processed {len(task_events)} task-related events")

        # Check for patterns in agent activity
        agent_activity = {}
        for event in events:
            agent = event.get("sender", "unknown")
            agent_activity[agent] = agent_activity.get(agent, 0) + 1

        if len(agent_activity) > 1:
            most_active = max(agent_activity.items(), key=lambda x: x[1])
            insights.append(f"Most active agent: {most_active[0]} ({most_active[1]} events)")

        return insights

    def _calculate_topic_metrics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate metrics for the topic"""
        metrics_data = {
            "event_frequency": len(events) / max(1, (max(e["timestamp"] for e in events) - min(e["timestamp"] for e in events)) / 3600),  # events per hour
            "unique_agents": len(set(e.get("sender", "unknown") for e in events)),
            "avg_event_size": sum(len(str(e.get("content", ""))) for e in events) / max(1, len(events))
        }

        return metrics_data

    async def _store_summaries_with_embeddings(self, summaries: List[Dict[str, Any]]) -> List[str]:
        """Store summaries with embeddings in the cortex"""
        stored_ids = []

        for summary in summaries:
            try:
                # Generate embedding for the summary
                summary_text = summary["summary_text"]
                embeddings = embedding_adapter.embed_texts([summary_text]) if embedding_adapter else []

                # Store in cortex
                metadata = {
                    "type": "event_summary",
                    "topic": summary["topic"],
                    "event_count": summary["event_count"],
                    "time_range": summary["time_range"],
                    "key_insights": summary["key_insights"],
                    "metrics": summary["metrics"],
                    "embedding": embeddings[0] if embeddings else None
                }

                success = self.cortex.store(
                    key=summary["id"],
                    data=summary,
                    metadata=metadata
                )

                if success:
                    stored_ids.append(summary["id"])
                    self.summary_stats["embeddings_generated"] += 1
                    logger.log("DEBUG", "EventSummarizer", f"Stored summary: {summary['id']}")
                else:
                    logger.log("WARNING", "EventSummarizer", f"Failed to store summary: {summary['id']}")

            except Exception as e:
                logger.log("ERROR", "EventSummarizer", f"Failed to store summary {summary['id']}: {e}")

        return stored_ids

    async def _cleanup_old_summaries(self):
        """Clean up old summaries beyond retention period"""
        try:
            retention_seconds = self.config["summary_retention_days"] * 24 * 3600
            cutoff_time = time.time() - retention_seconds

            # This would query the cortex for old summaries and remove them
            # For now, just log the intent
            logger.log("INFO", "EventSummarizer", f"Would cleanup summaries older than {self.config['summary_retention_days']} days")

        except Exception as e:
            logger.log("ERROR", "EventSummarizer", f"Failed to cleanup old summaries: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get summarizer statistics"""
        return {
            **self.summary_stats,
            "config": self.config,
            "next_run_due": self.last_run + (self.config["compaction_interval_hours"] * 3600)
        }


class ScheduledSummarizerJob:
    """Scheduled job for running event summarization"""

    def __init__(self, cortex: KnowledgeCortex, config: Optional[Dict[str, Any]] = None):
        self.cortex = cortex
        self.config = config or self._default_config()
        self.summarizer = EventSummarizer(cortex, self.config.get("summarizer"))
        self.running = False
        self.last_run = 0

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration"""
        return {
            "enabled": True,
            "schedule_type": "interval",  # "interval" or "cron"
            "interval_hours": 6,
            "cron_expression": "0 */6 * * *",  # Every 6 hours
            "max_runtime_seconds": 300,  # 5 minutes max
            "retry_on_failure": True,
            "max_retries": 3,
            "summarizer": {
                "compaction_interval_hours": 6,
                "max_events_per_summary": 100,
                "summary_retention_days": 30,
                "embedding_batch_size": 10,
                "enable_real_time": True
            }
        }

    async def start(self):
        """Start the scheduled job"""
        if self.running:
            logger.log("WARNING", "ScheduledSummarizerJob", "Job already running")
            return

        self.running = True
        logger.log("INFO", "ScheduledSummarizerJob", "Starting scheduled summarizer job")

        if self.config["schedule_type"] == "interval":
            asyncio.create_task(self._run_interval_schedule())
        else:
            asyncio.create_task(self._run_cron_schedule())

    async def stop(self):
        """Stop the scheduled job"""
        self.running = False
        logger.log("INFO", "ScheduledSummarizerJob", "Stopped scheduled summarizer job")

    async def _run_interval_schedule(self):
        """Run on interval schedule"""
        interval_seconds = self.config["interval_hours"] * 3600

        while self.running:
            try:
                # Check if it's time to run
                current_time = time.time()
                if current_time - self.last_run >= interval_seconds:
                    await self._execute_job()
                    self.last_run = current_time

                # Wait before checking again
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.log("ERROR", "ScheduledSummarizerJob", f"Interval schedule error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _run_cron_schedule(self):
        """Run on cron schedule (simplified implementation)"""
        # This would use a proper cron library like croniter
        # For now, fall back to interval
        logger.log("WARNING", "ScheduledSummarizerJob", "Cron schedule not implemented, using interval")
        await self._run_interval_schedule()

    async def _execute_job(self):
        """Execute the summarization job"""
        start_time = time.time()
        logger.log("INFO", "ScheduledSummarizerJob", "Executing summarization job")

        try:
            # Run compaction cycle
            result = await self.summarizer.run_compaction_cycle()

            # Record metrics
            metrics.track_summarizer_job(
                duration=time.time() - start_time,
                events_processed=result.get("events_processed", 0),
                summaries_created=result.get("summaries_created", 0),
                status=result.get("status", "unknown")
            )

            logger.log("INFO", "ScheduledSummarizerJob", f"Job completed: {result}")

        except Exception as e:
            logger.log("ERROR", "ScheduledSummarizerJob", f"Job execution failed: {e}")

            # Retry logic
            if self.config["retry_on_failure"]:
                await self._handle_retry()

    async def _handle_retry(self):
        """Handle job retry on failure"""
        # Simple retry with exponential backoff
        for attempt in range(self.config["max_retries"]):
            try:
                logger.log("INFO", "ScheduledSummarizerJob", f"Retry attempt {attempt + 1}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                result = await self.summarizer.run_compaction_cycle()
                if result.get("status") == "success":
                    logger.log("INFO", "ScheduledSummarizerJob", "Retry successful")
                    return
            except Exception as e:
                logger.log("WARNING", "ScheduledSummarizerJob", f"Retry {attempt + 1} failed: {e}")

        logger.log("ERROR", "ScheduledSummarizerJob", "All retry attempts failed")

    def get_status(self) -> Dict[str, Any]:
        """Get job status"""
        return {
            "running": self.running,
            "last_run": self.last_run,
            "next_run": self.last_run + (self.config["interval_hours"] * 3600),
            "config": self.config,
            "summarizer_stats": self.summarizer.get_stats()
        }


# Global instance
_summarizer_config = {
    "enabled": True,
    "schedule_type": "interval",
    "interval_hours": 6,
    "max_runtime_seconds": 300,
    "retry_on_failure": True,
    "max_retries": 3,
    "summarizer": {
        "compaction_interval_hours": 6,
        "max_events_per_summary": 100,
        "summary_retention_days": 30,
        "embedding_batch_size": 10,
        "enable_real_time": True
    }
}

try:
    # Initialize with cortex instance
    from .cortex import knowledge_cortex
    if knowledge_cortex:
        scheduled_summarizer = ScheduledSummarizerJob(knowledge_cortex, _summarizer_config)
        logger.log("INFO", "ScheduledSummarizerJob", "Scheduled summarizer job initialized")
    else:
        scheduled_summarizer = None
        logger.log("WARNING", "ScheduledSummarizerJob", "Knowledge cortex not available, summarizer not initialized")
except Exception as e:
    scheduled_summarizer = None
    logger.log("ERROR", "ScheduledSummarizerJob", f"Failed to initialize scheduled summarizer: {e}")