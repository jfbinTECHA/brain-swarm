from typing import Any, Dict, List, Optional
from ..core.base import MemorySystem, logger, metrics
from .backends import MemoryBackend, MemoryBackendFactory, InMemoryBackend
import time
import os

class WorkingMemory(MemorySystem):
    def __init__(self, backend: Optional[MemoryBackend] = None):
        # Use provided backend or create default in-memory backend
        self.backend = backend or InMemoryBackend()

        # Keep local state for reasoning branches and intermediate results
        # These are runtime state, not persistent data
        self.rehearsal_buffer: List[Dict[str, Any]] = []
        self.active_reasoning_branches: Dict[str, int] = {}
        self.max_concurrent_branches = 2  # Reduced limit for better resource management
        self.intermediate_results: Dict[str, Dict[str, Any]] = {}  # Task-specific intermediate storage
        self.max_memory_entries = 50  # Limit total memory entries
        self.pruning_interval = 300  # Prune every 5 minutes
        self.last_pruning_time = time.time()

        # Backend health monitoring
        self.backend_health = self.backend.health_check()

    def store(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None):
        """Store data in working memory with automatic pruning and logging"""
        # Check if we need to prune before storing
        self._check_and_prune_memory()

        # Calculate relevance score for the data
        relevance_score = self._calculate_relevance_score(data, metadata or {})

        # Estimate data size for logging
        data_size = len(str(data).encode('utf-8')) if data is not None else 0

        # Prepare entry for backend storage
        entry = {
            "data": data,
            "metadata": metadata or {},
            "timestamp": time.time(),
            "relevance_score": relevance_score,
            "access_count": 0
        }

        # Store using backend
        success = self.backend.store(key, entry)

        # Log memory operation
        from ..core.base import logger
        logger.log_memory_operation("store", key, "WorkingMemory", data_size, success, metadata)

        # Limit total memory entries
        if success and len(self.backend.keys()) > self.max_memory_entries:
            self._prune_low_value_entries()

    def _calculate_relevance_score(self, data: Any, metadata: Dict[str, Any]) -> float:
        """Calculate relevance score for memory retention"""
        score = 0.5  # Base score

        # Boost score based on metadata
        if metadata.get("type") == "intermediate":
            score += 0.2  # Intermediate results are valuable
        if metadata.get("task_id"):
            score += 0.1  # Task-related data is more relevant
        if metadata.get("priority", 1) >= 3:
            score += 0.2  # High priority items

        # Boost score based on data content
        data_str = str(data).lower()
        if any(keyword in data_str for keyword in ["result", "outcome", "conclusion", "summary"]):
            score += 0.3  # Results and conclusions are highly relevant
        if len(data_str) > 100:
            score += 0.1  # Substantial content is more valuable

        return min(score, 1.0)  # Cap at 1.0

    def _check_and_prune_memory(self):
        """Check if memory pruning is needed and perform it"""
        current_time = time.time()
        if current_time - self.last_pruning_time > self.pruning_interval:
            self._perform_memory_pruning()
            self.last_pruning_time = current_time

    def _perform_memory_pruning(self):
        """Prune old and low-value memory entries"""
        current_time = time.time()
        entries_to_remove = []

        # Get all keys from backend
        all_keys = self.backend.keys()

        for key in all_keys:
            entry = self.backend.retrieve(key)
            if not entry:
                continue

            age_hours = (current_time - entry.get("timestamp", 0)) / 3600
            relevance = entry.get("relevance_score", 0.5)
            access_count = entry.get("access_count", 0)

            # Remove if old and low relevance, or very old regardless of relevance
            if (age_hours > 24 and relevance < 0.6) or age_hours > 168:  # 7 days
                entries_to_remove.append(key)
            # Remove if old, low relevance, and rarely accessed
            elif age_hours > 12 and relevance < 0.4 and access_count < 2:
                entries_to_remove.append(key)

        # Remove the entries
        for key in entries_to_remove:
            self.backend.delete(key)

        if entries_to_remove:
            logger.log("INFO", "WorkingMemory", f"Pruned {len(entries_to_remove)} old/low-value memory entries")

    def _prune_low_value_entries(self):
        """Prune the lowest value entries when memory limit is reached"""
        all_keys = self.backend.keys()
        if len(all_keys) <= self.max_memory_entries:
            return

        # Sort by combined score (relevance + access bonus - age penalty)
        current_time = time.time()
        scored_entries = []

        for key in all_keys:
            entry = self.backend.retrieve(key)
            if not entry:
                continue

            age_hours = (current_time - entry.get("timestamp", 0)) / 3600
            relevance = entry.get("relevance_score", 0.5)
            access_count = entry.get("access_count", 0)

            # Combined score: relevance + access bonus - age penalty
            combined_score = relevance + (access_count * 0.1) - (age_hours * 0.05)
            scored_entries.append((key, combined_score))

        # Sort by score (lowest first) and remove bottom entries
        scored_entries.sort(key=lambda x: x[1])
        entries_to_remove = scored_entries[:len(scored_entries) - self.max_memory_entries + 10]  # Keep some buffer

        for key, _ in entries_to_remove:
            self.backend.delete(key)

        logger.log("INFO", "WorkingMemory", f"Pruned {len(entries_to_remove)} lowest-value memory entries")

    def _prune_intermediate_results(self):
        """Prune old and low-relevance intermediate results to maintain STM buffer efficiency"""
        current_time = time.time()
        max_intermediate_entries = 10  # Limit intermediate results
        max_age_hours = 1  # Prune results older than 1 hour

        entries_to_remove = []

        # First, remove old entries
        for key, entry in self.intermediate_results.items():
            age_hours = (current_time - entry.get("timestamp", 0)) / 3600
            if age_hours > max_age_hours:
                entries_to_remove.append(key)

        # Remove old entries
        for key in entries_to_remove:
            del self.intermediate_results[key]

        # If still over limit, remove least relevant (oldest first)
        if len(self.intermediate_results) > max_intermediate_entries:
            # Sort by timestamp (oldest first)
            sorted_entries = sorted(
                self.intermediate_results.items(),
                key=lambda x: x[1].get("timestamp", 0)
            )
            entries_to_remove = [key for key, _ in sorted_entries[:len(sorted_entries) - max_intermediate_entries]]

            for key in entries_to_remove:
                del self.intermediate_results[key]

        if entries_to_remove:
            logger.log("INFO", "WorkingMemory", f"Pruned {len(entries_to_remove)} intermediate results")

    def cleanup_task_intermediates(self, task_id: str, keep_top: int = 2):
        """Clean up intermediate results for a completed task, keeping only top results"""
        task_prefix = f"tree_of_thought_{task_id}"
        checkpoint_prefix = f"checkpoint_{task_id}"

        # Collect all task-related entries
        entries_to_remove = []
        entries_to_keep = []

        for key, entry in self.intermediate_results.items():
            if task_prefix in key or checkpoint_prefix in key:
                if len(entries_to_keep) < keep_top:
                    entries_to_keep.append(key)
                else:
                    entries_to_remove.append(key)

        # Remove excess entries
        for key in entries_to_remove:
            del self.intermediate_results[key]

        if entries_to_remove:
            logger.log("INFO", "WorkingMemory", f"Cleaned up {len(entries_to_remove)} intermediate results for task {task_id}")

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve data from working memory and track access with logging"""
        entry = self.backend.retrieve(key)
        if entry:
            # Track access for relevance scoring
            entry["access_count"] = entry.get("access_count", 0) + 1
            entry["last_accessed"] = time.time()

            # Update entry in backend with new access info
            self.backend.store(key, entry)

            # Log memory retrieval
            data_size = len(str(entry["data"]).encode('utf-8')) if entry["data"] is not None else 0
            from ..core.base import logger
            logger.log_memory_operation("retrieve", key, "WorkingMemory", data_size, True, entry["metadata"])

            return entry["data"]

        # Log failed retrieval
        from ..core.base import logger
        logger.log_memory_operation("retrieve", key, "WorkingMemory", 0, False, {"error": "key_not_found"})

        return None

    def search(self, query: str, **kwargs) -> List[Any]:
        """Search memory for relevant information using backend"""
        return self.backend.search(query, **kwargs)

    def chain_of_thought(self, initial_thought: str, steps: int = 5) -> List[str]:
        """Perform chain of thought reasoning"""
        start_time = time.time()
        logger.log("INFO", "WorkingMemory", "Chain of thought started", {"initial_thought": initial_thought, "steps": steps})

        thoughts = [initial_thought]
        current_thought = initial_thought

        for i in range(steps - 1):
            # Simple heuristic: extend thought based on keywords
            if "analyze" in current_thought.lower():
                next_thought = "Considering implications and patterns in the data"
            elif "decide" in current_thought.lower():
                next_thought = "Evaluating options and weighing pros and cons"
            elif "plan" in current_thought.lower():
                next_thought = "Breaking down into actionable steps"
            else:
                next_thought = f"Further developing: {current_thought}"

            thoughts.append(next_thought)
            current_thought = next_thought
            logger.log("DEBUG", "WorkingMemory", f"Chain step {i+1}", {"thought": next_thought})

        execution_time = time.time() - start_time
        success = len(thoughts) == steps  # Success if completed all steps

        metrics.track_reasoning_performance("chain_of_thought", len(thoughts), execution_time, success)

        logger.log("INFO", "WorkingMemory", "Chain of thought completed", {"total_steps": len(thoughts)})
        return thoughts

    def self_ask(self, question: str) -> List[str]:
        """Decompose question into subquestions using self-ask technique"""
        subquestions = []

        # Simple decomposition based on keywords
        if "why" in question.lower():
            subquestions.append("What are the underlying causes?")
        if "how" in question.lower():
            subquestions.append("What are the step-by-step processes involved?")
        if "what" in question.lower():
            subquestions.append("What are the key components or facts?")
        if "when" in question.lower():
            subquestions.append("What is the timeline or sequence?")
        if "where" in question.lower():
            subquestions.append("What is the location or context?")

        if not subquestions:
            subquestions = [f"Basic question: {question}"]

        return subquestions

    def tree_of_thought(self, root_idea: str, branches: int = 3, depth: int = 2, agent_id: str = None) -> Dict[str, Any]:
        """Explore multiple reasoning paths using tree of thought with strict resource limits and comprehensive logging"""
        task_id = f"tree_of_thought_{agent_id or 'unknown'}_{int(time.time())}"

        # Log reasoning start
        from ..core.base import logger
        logger.log_reasoning_step(agent_id or "system", task_id, 0, "initialization",
                                 f"Starting tree of thought reasoning for: {root_idea[:50]}...",
                                 None, root_idea, 0.5)

        # Check if we can allocate reasoning branches
        if agent_id:
            if not self.request_reasoning_branch(agent_id):
                logger.log("WARNING", "WorkingMemory", f"Branch limit reached for agent {agent_id}, reducing branches")
                branches = 1  # Fallback to single branch if limit reached
            else:
                # Limit branches based on current system load
                total_active_branches = sum(self.active_reasoning_branches.values())
                available_slots = max(0, self.max_concurrent_branches - total_active_branches)
                branches = min(branches, available_slots + 1)  # +1 for the requesting agent

        # Further limit based on complexity of root idea and agent constraints
        max_branches = 1  # Default to minimal branching for resource efficiency
        if len(root_idea.split()) <= 10:  # Simple ideas can have slightly more branches
            max_branches = 2
        elif len(root_idea.split()) > 30:  # Very complex ideas get minimal branches
            max_branches = 1

        # Additional constraint: reduce branches if system is heavily loaded
        system_load = sum(self.active_reasoning_branches.values()) / self.max_concurrent_branches
        if system_load > 0.7:  # Over 70% capacity
            max_branches = min(max_branches, 1)

        actual_branches = min(branches, max_branches)

        tree = {
            "root": root_idea,
            "branches": [],
            "branch_limit_applied": branches > actual_branches,
            "agent_restricted": agent_id is not None,
            "system_load": system_load,
            "max_branches_allowed": max_branches
        }

        # Store intermediate results in STM buffer with task-specific key
        self.intermediate_results[task_id] = {
            "root_idea": root_idea,
            "branches": [],
            "timestamp": time.time(),
            "agent_id": agent_id
        }

        step_counter = 1
        for i in range(actual_branches):
            branch = {"path": i + 1, "nodes": [root_idea], "depth_limit": min(depth, 2)}  # Reduced max depth

            current_node = root_idea
            for d in range(1, min(depth, 2)):  # Cap depth at 2 for better resource management
                # Generate alternative perspectives with minimal branching
                if "problem" in current_node.lower():
                    alternatives = ["Direct solution approach"]
                    evidence = "Problem detected in current reasoning path"
                elif "decision" in current_node.lower():
                    alternatives = ["Conservative choice"]
                    evidence = "Decision point identified requiring careful consideration"
                else:
                    alternatives = ["Continue current direction"]
                    evidence = "Continuing established reasoning trajectory"

                selected_alternative = alternatives[0]  # Only one alternative per branch

                # Log reasoning step
                logger.log_reasoning_step(agent_id or "system", task_id, step_counter,
                                        f"branch_{i+1}_depth_{d}", f"Exploring: {selected_alternative}",
                                        evidence, selected_alternative, 0.7)

                branch["nodes"].append(selected_alternative)
                current_node = selected_alternative
                step_counter += 1

            tree["branches"].append(branch)
            self.intermediate_results[task_id]["branches"].append(branch)

        # Log final decision
        final_conclusion = f"Generated {actual_branches} reasoning branches with depth {min(depth, 2)}"
        logger.log_decision(agent_id or "system", task_id, final_conclusion,
                          [f"{b} branches" for b in range(1, branches + 1)],
                          {"branch_limit_applied": tree["branch_limit_applied"],
                           "system_load": system_load}, 0.8, "tree_of_thought")

        # Prune old intermediate results after processing
        self._prune_intermediate_results()

        # Release branch allocation if we allocated one
        if agent_id and branches > 1:
            self.release_reasoning_branch(agent_id)

        return tree

    def request_reasoning_branch(self, agent_id: str) -> bool:
        """Request allocation of a reasoning branch for an agent"""
        current_branches = self.active_reasoning_branches.get(agent_id, 0)
        total_active = sum(self.active_reasoning_branches.values())

        # Check if we can allocate (per-agent limit and global limit)
        max_per_agent = 2  # Limit per agent to prevent monopolization
        if current_branches >= max_per_agent:
            logger.log("WARNING", "WorkingMemory", f"Agent {agent_id} reached per-agent branch limit ({max_per_agent})")
            return False

        if total_active >= self.max_concurrent_branches:
            logger.log("WARNING", "WorkingMemory", f"Global branch limit reached ({self.max_concurrent_branches})")
            return False

        # Allocate branch
        self.active_reasoning_branches[agent_id] = current_branches + 1
        logger.log("INFO", "WorkingMemory", f"Allocated reasoning branch for agent {agent_id} (total: {current_branches + 1})")
        return True

    def release_reasoning_branch(self, agent_id: str):
        """Release a reasoning branch for an agent"""
        current_branches = self.active_reasoning_branches.get(agent_id, 0)
        if current_branches > 0:
            self.active_reasoning_branches[agent_id] = current_branches - 1
            logger.log("INFO", "WorkingMemory", f"Released reasoning branch for agent {agent_id} (remaining: {current_branches - 1})")
            # Clean up if no branches left
            if self.active_reasoning_branches[agent_id] == 0:
                del self.active_reasoning_branches[agent_id]

    def get_branch_utilization(self) -> Dict[str, Any]:
        """Get current branch utilization statistics"""
        total_branches = sum(self.active_reasoning_branches.values())
        return {
            "active_branches": total_branches,
            "max_branches": self.max_concurrent_branches,
            "utilization_percent": (total_branches / self.max_concurrent_branches) * 100,
            "agent_distribution": self.active_reasoning_branches.copy()
        }

class LongTermMemory(MemorySystem):
    def __init__(self, backend: Optional[MemoryBackend] = None):
        # Use provided backend or create default in-memory backend
        self.backend = backend or InMemoryBackend()

        # Keep separate key prefixes for different memory types
        self.episodic_prefix = "episodic:"
        self.semantic_prefix = "semantic:"
        self.tool_use_prefix = "tool_use:"
        self.reflection_prefix = "reflection:"

    def store(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None):
        """Store data in long-term memory - route to appropriate subsystem using backend"""
        memory_type = metadata.get("type", "semantic") if metadata else "semantic"

        # Determine prefix based on memory type
        if memory_type == "episodic":
            prefixed_key = f"{self.episodic_prefix}{key}"
        elif memory_type == "tool_use":
            prefixed_key = f"{self.tool_use_prefix}{key}"
        elif memory_type == "reflection":
            prefixed_key = f"{self.reflection_prefix}{key}"
        else:  # semantic
            prefixed_key = f"{self.semantic_prefix}{key}"

        # Store using backend
        entry = {
            "data": data,
            "metadata": metadata or {},
            "timestamp": time.time(),
            "memory_type": memory_type
        }
        return self.backend.store(prefixed_key, entry)

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve data from long-term memory using backend"""
        # Try each prefix
        for prefix in [self.episodic_prefix, self.semantic_prefix, self.tool_use_prefix, self.reflection_prefix]:
            prefixed_key = f"{prefix}{key}"
            entry = self.backend.retrieve(prefixed_key)
            if entry:
                return entry["data"]
        return None

    def search(self, query: str, **kwargs) -> List[Any]:
        """Search long-term memory across all subsystems using backend"""
        return self.backend.search(query, **kwargs)

    def episodic_memory(self, event: str, context: Dict[str, Any]) -> str:
        """Store and retrieve episodic memories (personal experiences)"""
        key = f"episodic_{int(time.time())}"
        self.store(key, {"event": event, "context": context}, {"type": "episodic"})
        return f"Stored episodic memory: {event}"

    def semantic_memory(self, fact: str, category: str = "general") -> str:
        """Store semantic knowledge (facts and concepts)"""
        key = f"semantic_{category}_{hash(fact) % 10000}"
        self.store(key, {"fact": fact, "category": category}, {"type": "semantic"})
        return f"Stored semantic fact: {fact}"

    def tool_use_memory(self, tool_name: str, usage_pattern: Dict[str, Any]) -> str:
        """Store tool usage patterns and learning"""
        key = f"tool_{tool_name}"
        self.store(key, {"tool": tool_name, "pattern": usage_pattern}, {"type": "tool_use"})
        return f"Stored tool use memory for: {tool_name}"

    def reflection_on_action(self, action: str, outcome: str, lesson: str) -> str:
        """Store reflections on past actions for learning"""
        key = f"reflection_{int(time.time())}"
        self.store(key, {"action": action, "outcome": outcome, "lesson": lesson}, {"type": "reflection"})
        return f"Stored reflection: {lesson}"

    def store_completed_task(self, task_id: str, task_data: Dict[str, Any], metadata: Dict[str, Any]):
        """Archive completed tasks with metadata"""
        key = f"completed_task_{task_id}"
        self.store(key, {"task_data": task_data, "metadata": metadata}, {"type": "episodic"})

    def update_semantic_memory(self, knowledge: str, category: str = "general"):
        """Add new knowledge to semantic memory"""
    def semantic_search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Vector embedding simulation: Find semantically similar knowledge using Jaccard similarity"""
        query_words = set(query.lower().split())
        results = []

        for key, entry in self.semantic_store.items():
            fact = entry["data"].get("fact", "").lower()
            fact_words = set(fact.split())
            if fact_words and query_words:
                # Jaccard similarity
                similarity = len(query_words.intersection(fact_words)) / len(query_words.union(fact_words))
                if similarity > 0.1:  # Minimum threshold
                    results.append({
                        "fact": entry["data"]["fact"],
                        "category": entry["data"]["category"],
                        "similarity": similarity,
                        "metadata": entry["metadata"]
                    })

        # Sort by similarity and return top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
        self.semantic_memory(knowledge, category)

# Configuration for memory backends
MEMORY_CONFIG = {
    "working_memory": {
        "backend": "memory",  # Options: "memory", "redis", "postgres"
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "key_prefix": "brain_swarm:working:"
        },
        "postgres": {
            "host": "localhost",
            "port": 5432,
            "database": "brain_swarm",
            "user": "postgres",
            "password": "",
            "table_name": "working_memory"
        }
    },
    "long_term_memory": {
        "backend": "memory",  # Options: "memory", "redis", "postgres"
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 1,
            "key_prefix": "brain_swarm:ltm:"
        },
        "postgres": {
            "host": "localhost",
            "port": 5432,
            "database": "brain_swarm",
            "user": "postgres",
            "password": "",
            "table_name": "long_term_memory"
        }
    }
}

def create_memory_backend(config: Dict[str, Any]) -> MemoryBackend:
    """Create a memory backend from configuration"""
    backend_type = config.get("backend", "memory")

    if backend_type == "redis":
        redis_config = config.get("redis", {})
        return MemoryBackendFactory.create_backend("redis", **redis_config)
    elif backend_type == "postgres":
        postgres_config = config.get("postgres", {})
        return MemoryBackendFactory.create_backend("postgres", **postgres_config)
    else:
        return MemoryBackendFactory.create_backend("memory")

# Create backends based on configuration
_working_memory_backend = create_memory_backend(MEMORY_CONFIG["working_memory"])
_long_term_memory_backend = create_memory_backend(MEMORY_CONFIG["long_term_memory"])

# Global memory instances for agent access
working_memory = WorkingMemory(backend=_working_memory_backend)
long_term_memory = LongTermMemory(backend=_long_term_memory_backend)