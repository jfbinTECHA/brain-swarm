from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import time
import json

class AgentRole(Enum):
    PREFRONTAL_CORTEX = "PrefrontalCortex"
    SHORT_TERM_MEMORY = "ShortTermMemory"
    CORTEX_HIPPOCAMPUS = "CortexHippocampus"
    VISION_AGENT = "VisionAgent"
    LANGUAGE_AGENT = "LanguageAgent"
    MATH_REASONING_AGENT = "MathReasoningAgent"
    SIMULATION_AGENT = "SimulationAgent"
    DEFAULT_MODE_NETWORK = "DefaultModeNetwork"

class MessageType(Enum):
    TASK_ASSIGNMENT = "task_assignment"
    RESULT_REPORT = "result_report"
    DEBATE_CONTRIBUTION = "debate_contribution"
    MEMORY_QUERY = "memory_query"
    MEMORY_STORE = "memory_store"
    SIMULATION_REQUEST = "simulation_request"
    SHARE_KNOWLEDGE = "share_knowledge"

@dataclass
class Message:
    sender: str
    receiver: str
    message_type: MessageType
    content: Any
    timestamp: float
    swarm_id: Optional[str] = None  # Swarm identifier for multi-swarm support
    metadata: Optional[Dict[str, Any]] = None

class BaseAgent(ABC):
    def __init__(self, agent_id: str, role: AgentRole, swarm_id: Optional[str] = None):
        self.agent_id = agent_id
        self.role = role
        self.swarm_id = swarm_id  # Swarm identifier for multi-swarm support
        self.message_queue: List[Message] = []

    @abstractmethod
    def process_message(self, message: Message) -> Optional[Message]:
        """Process incoming message and return response if any"""
        pass

    @abstractmethod
    def execute_task(self, task: Dict[str, Any]) -> Any:
        """Execute assigned task"""
        # Audit logging
        self._audit_log("task_start", {
            "task_id": task.get("task_id", f"task_{id(task)}"),
            "task_type": task.get("type", "unknown"),
            "agent_id": self.agent_id,
            "agent_role": self.role.value,
            "swarm_id": self.swarm_id,
            "task_content": task.get("content", "")[:200]  # Truncate for logging
        })
        pass

    def send_message(self, receiver: str, message_type: MessageType, content: Any,
                    metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Create and queue a message to send"""
        import time
        message = Message(
            sender=self.agent_id,
            receiver=receiver,
            message_type=message_type,
            content=content,
            timestamp=time.time(),
            swarm_id=self.swarm_id,
            metadata=metadata
        )
        self.message_queue.append(message)
        return message

    def receive_message(self, message: Message):
        """Receive and process a message"""
        response = self.process_message(message)
        if response:
            self.message_queue.append(response)

    def share_knowledge(self, recipient: str, knowledge: Dict[str, Any]):
        """Share learned knowledge with another agent"""
        self._audit_log("knowledge_share", {
            "recipient": recipient,
            "knowledge_keys": list(knowledge.keys()) if isinstance(knowledge, dict) else ["unknown"],
            "agent_id": self.agent_id,
            "swarm_id": self.swarm_id
        })
        self.send_message(recipient, MessageType.SHARE_KNOWLEDGE, knowledge)

    def handle_task_failure(self, task: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle task execution failures with comprehensive logging and recovery options"""
        failure_data = {
            "task_id": task.get("task_id", f"task_{id(task)}"),
            "task_type": task.get("type", "unknown"),
            "agent_id": self.agent_id,
            "agent_role": self.role.value,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
            "timestamp": time.time(),
            "retry_count": context.get("retry_count", 0) if context else 0
        }

        # Log failure immediately
        logger.log("ERROR", f"{self.role.value}", f"Task execution failed: {failure_data['error_message']}",
                  {"task_id": failure_data["task_id"], "error_type": failure_data["error_type"]})

        # Log detailed failure information for learning
        # Import at module level to avoid circular imports
        import __main__
        if hasattr(__main__, 'metrics'):
            __main__.metrics.log_failure(failure_data)

        # Send to recursive improvement system
        from .recursive_improvement import recursive_improvement
        improvement_result = recursive_improvement.process_failure(failure_data)
        failure_data["improvement_cycle_id"] = improvement_result["improvement_cycle_id"]

        # Determine recovery strategy
        recovery_strategy = self._determine_recovery_strategy(failure_data)

        failure_data["recovery_strategy"] = recovery_strategy
        failure_data["can_retry"] = recovery_strategy["action"] != "abandon"

        return failure_data

    def _determine_recovery_strategy(self, failure_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the best recovery strategy based on failure analysis"""
        error_type = failure_data["error_type"]
        task_type = failure_data["task_type"]
        retry_count = failure_data["retry_count"]

        # Maximum retry attempts
        max_retries = 3

        if retry_count >= max_retries:
            return {
                "action": "abandon",
                "reason": f"Maximum retries ({max_retries}) exceeded",
                "alternative_action": "escalate_to_coordinator"
            }

        # Strategy based on error type and task type
        if error_type in ["ValueError", "TypeError", "AttributeError"]:
            # Input/data validation errors - try with simplified inputs
            return {
                "action": "retry_with_simplification",
                "reason": "Input validation error - attempting with simplified inputs",
                "simplification_level": min(retry_count + 1, 3),
                "max_retries": max_retries
            }

        elif error_type in ["TimeoutError", "ConnectionError", "URLError"]:
            # Network/external service errors - retry with backoff
            return {
                "action": "retry_with_backoff",
                "reason": "Network/external service error - retrying with backoff",
                "backoff_seconds": min(2 ** retry_count, 30),  # Exponential backoff, max 30s
                "max_retries": max_retries
            }

        elif error_type == "MemoryError":
            # Memory issues - try breaking into smaller subtasks
            return {
                "action": "retry_with_subdivision",
                "reason": "Memory error - breaking task into smaller subtasks",
                "subtask_count": max(2, 4 - retry_count),  # Fewer subtasks on retry
                "max_retries": max_retries
            }

        elif error_type in ["ImportError", "ModuleNotFoundError"]:
            # Missing dependencies - try alternative approach
            return {
                "action": "retry_with_alternative",
                "reason": "Missing dependency - trying alternative approach",
                "alternative_method": self._find_alternative_method(task_type),
                "max_retries": max_retries
            }

        else:
            # Generic errors - try with reduced complexity
            return {
                "action": "retry_with_reduced_complexity",
                "reason": f"Generic {error_type} - retrying with reduced complexity",
                "complexity_reduction": min(retry_count + 1, 3),
                "max_retries": max_retries
            }

    def _find_alternative_method(self, task_type: str) -> str:
        """Find an alternative method for a given task type"""
        alternatives = {
            "image_analysis": "basic_text_analysis",
            "sentiment_analysis": "keyword_matching",
            "calculation": "basic_arithmetic",
            "web_scraping": "mock_response",
            "api_call": "cached_response"
        }
        return alternatives.get(task_type, "basic_fallback")

    def execute_with_error_handling(self, task: Dict[str, Any], max_retries: int = 3) -> Any:
        """Execute task with comprehensive error handling and retry logic"""
        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                # Execute the task
                result = self.execute_task(task)

                # Log successful recovery if this was a retry
                if retry_count > 0:
                    logger.log("INFO", f"{self.role.value}", f"Task recovered after {retry_count} retries",
                              {"task_id": task.get("task_id", f"task_{id(task)}")})

                return result

            except Exception as e:
                # Handle the failure
                context = {"retry_count": retry_count, "max_retries": max_retries}
                failure_data = self.handle_task_failure(task, e, context)

                recovery = failure_data["recovery_strategy"]

                if recovery["action"] == "abandon":
                    # Give up and return error result
                    logger.log("ERROR", f"{self.role.value}", f"Task abandoned after {retry_count} retries: {failure_data['error_message']}")
                    return f"Task failed after {retry_count} retries: {failure_data['error_message']}"

                elif recovery["action"] == "retry_with_backoff":
                    # Wait before retrying
                    backoff_time = recovery.get("backoff_seconds", 1)
                    logger.log("INFO", f"{self.role.value}", f"Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)

                elif recovery["action"] == "retry_with_simplification":
                    # Modify task for simpler execution
                    task = self._simplify_task(task, recovery.get("simplification_level", 1))
                    logger.log("INFO", f"{self.role.value}", f"Retrying with simplified task (level {recovery.get('simplification_level', 1)})")

                elif recovery["action"] == "retry_with_subdivision":
                    # Break task into smaller subtasks
                    subtasks = self._subdivide_task(task, recovery.get("subtask_count", 2))
                    if subtasks and len(subtasks) > 1:
                        logger.log("INFO", f"{self.role.value}", f"Retrying by subdividing into {len(subtasks)} subtasks")
                        # Execute subtasks and combine results
                        sub_results = []
                        for subtask in subtasks:
                            try:
                                sub_result = self.execute_task(subtask)
                                sub_results.append(sub_result)
                            except Exception as sub_e:
                                logger.log("WARNING", f"{self.role.value}", f"Subtask failed: {str(sub_e)}")
                                sub_results.append(f"Subtask failed: {str(sub_e)}")

                        return self._combine_subtask_results(sub_results)
                    else:
                        logger.log("WARNING", f"{self.role.value}", "Could not subdivide task, retrying as-is")

                elif recovery["action"] == "retry_with_alternative":
                    # Try alternative method
                    alt_method = recovery.get("alternative_method")
                    if alt_method:
                        task = self._switch_to_alternative_method(task, alt_method)
                        logger.log("INFO", f"{self.role.value}", f"Retrying with alternative method: {alt_method}")

                elif recovery["action"] == "retry_with_reduced_complexity":
                    # Reduce task complexity
                    complexity_level = recovery.get("complexity_reduction", 1)
                    task = self._reduce_task_complexity(task, complexity_level)
                    logger.log("INFO", f"{self.role.value}", f"Retrying with reduced complexity (level {complexity_level})")

                retry_count += 1
                last_error = e

        # All retries exhausted - log final failure to recursive improvement system
        final_failure_data = {
            "task_id": task.get("task_id", f"task_{id(task)}"),
            "task_type": task.get("type", "unknown"),
            "agent_id": self.agent_id,
            "agent_role": self.role.value,
            "error_type": type(last_error).__name__ if last_error else "UnknownError",
            "error_message": str(last_error) if last_error else "Unknown error after retries",
            "context": {"total_retries": max_retries, "final_attempt": True},
            "timestamp": time.time(),
            "retry_count": max_retries
        }

        # Send to recursive improvement system
        from .recursive_improvement import recursive_improvement
        recursive_improvement.process_failure(final_failure_data)

        return f"Task failed after {max_retries} retries. Final error: {str(last_error)}"

    def _simplify_task(self, task: Dict[str, Any], level: int) -> Dict[str, Any]:
        """Simplify task based on level (1-3, higher = more simplified)"""
        simplified = task.copy()

        if level >= 1:
            # Remove optional parameters
            content = simplified.get("content", "")
            if isinstance(content, str) and len(content) > 100:
                simplified["content"] = content[:100] + "..."

        if level >= 2:
            # Use basic task type
            if "type" in simplified:
                simplified["type"] = "basic_" + simplified["type"].replace("advanced_", "").replace("complex_", "")

        if level >= 3:
            # Minimal viable task
            simplified["content"] = "Basic execution test"
            simplified["type"] = "basic_test"

        return simplified

    def _subdivide_task(self, task: Dict[str, Any], num_subtasks: int) -> List[Dict[str, Any]]:
        """Break task into smaller subtasks"""
        # This is a basic implementation - subclasses should override for specific logic
        content = task.get("content", "")
        if isinstance(content, str) and len(content.split()) > 10:
            words = content.split()
            chunk_size = max(1, len(words) // num_subtasks)

            subtasks = []
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                subtask = task.copy()
                subtask["content"] = chunk
                subtask["subtask_index"] = len(subtasks)
                subtask["parent_task_id"] = task.get("task_id")
                subtasks.append(subtask)

            return subtasks

        return [task]  # Cannot subdivide

    def _combine_subtask_results(self, results: List[Any]) -> Any:
        """Combine results from subtasks"""
        # Basic combination - subclasses should override for specific logic
        if len(results) == 1:
            return results[0]
        elif all(isinstance(r, str) for r in results):
            return " ".join(str(r) for r in results)
        else:
            return {"combined_results": results, "subtask_count": len(results)}

    def _switch_to_alternative_method(self, task: Dict[str, Any], alternative: str) -> Dict[str, Any]:
        """Switch task to use alternative method"""
        modified = task.copy()
        modified["type"] = alternative
        modified["original_type"] = task.get("type")
        return modified

    def _reduce_task_complexity(self, task: Dict[str, Any], level: int) -> Dict[str, Any]:
        """Reduce task complexity"""
        return self._simplify_task(task, level)  # Use same logic as simplification

    def _audit_log(self, action: str, details: Dict[str, Any]):
        """Log agent actions for audit and monitoring"""
        audit_entry = {
            "timestamp": time.time(),
            "agent_id": self.agent_id,
            "agent_role": self.role.value,
            "swarm_id": self.swarm_id,
            "action": action,
            "details": details
        }

        # Output as JSON line for log aggregation systems
        import json
        print(json.dumps(audit_entry), file=open("/dev/stdout", "w"))

        # Also log to swarm logger with Prometheus labels
        logger.log("INFO", f"{self.role.value}_audit", f"Agent action: {action}",
                  {**details, "prometheus_labels": {
                      "agent_id": self.agent_id,
                      "agent_role": self.role.value,
                      "swarm_id": self.swarm_id or "default",
                      "action": action
                  }})

    def self_ask_guidance(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Self-ask prompts to clarify task execution and avoid dead-ends"""
        task_description = task.get("content", task.get("description", ""))

        guidance = {
            "next_actionable_step": self._identify_next_step(task_description),
            "required_inputs_check": self._validate_required_inputs(task, task_description),
            "recommended_tool": self._select_appropriate_tool(task_description),
            "confidence_score": 0.0,
            "clarification_needed": []
        }

        # Calculate confidence based on clarity of guidance
        if guidance["next_actionable_step"]["action"]:
            guidance["confidence_score"] += 0.4
        if guidance["required_inputs_check"]["all_inputs_available"]:
            guidance["confidence_score"] += 0.4
        if guidance["recommended_tool"]["tool_selected"]:
            guidance["confidence_score"] += 0.2

        # Identify areas needing clarification
        if not guidance["next_actionable_step"]["action"]:
            guidance["clarification_needed"].append("unclear_next_step")
        if not guidance["required_inputs_check"]["all_inputs_available"]:
            guidance["clarification_needed"].extend(guidance["required_inputs_check"]["missing_inputs"])
        if not guidance["recommended_tool"]["tool_selected"]:
            guidance["clarification_needed"].append("no_suitable_tool")

        return guidance

    def _identify_next_step(self, task_description: str) -> Dict[str, Any]:
        """Identify the next actionable step from task description"""
        desc_lower = task_description.lower()

        # Common action patterns
        action_patterns = {
            "analyze": ["analyze", "examine", "review", "assess", "evaluate"],
            "process": ["process", "transform", "convert", "handle", "manage"],
            "generate": ["generate", "create", "produce", "make", "build"],
            "search": ["search", "find", "locate", "discover", "lookup"],
            "calculate": ["calculate", "compute", "solve", "determine"],
            "communicate": ["explain", "describe", "summarize", "report"]
        }

        identified_action = None
        confidence = 0.0

        for action, keywords in action_patterns.items():
            if any(keyword in desc_lower for keyword in keywords):
                identified_action = action
                confidence = 0.8
                break

        # If no specific action found, try to extract from sentence structure
        if not identified_action:
            if "what" in desc_lower or "how" in desc_lower or "?" in task_description:
                identified_action = "investigate"
                confidence = 0.6
            else:
                identified_action = "execute"
                confidence = 0.4

        return {
            "action": identified_action,
            "confidence": confidence,
            "rationale": f"Identified primary action '{identified_action}' from task keywords"
        }

    def _validate_required_inputs(self, task: Dict[str, Any], task_description: str) -> Dict[str, Any]:
        """Check if all required inputs are available"""
        required_inputs = []
        available_inputs = []
        missing_inputs = []

        # Extract potential input requirements from task description
        desc_lower = task_description.lower()

        # Common input indicators
        input_indicators = {
            "data": ["data", "information", "content", "text", "file"],
            "parameters": ["parameters", "settings", "config", "options"],
            "context": ["context", "background", "history", "previous"],
            "target": ["target", "goal", "objective", "aim"],
            "constraints": ["constraints", "limits", "requirements", "rules"]
        }

        for input_type, keywords in input_indicators.items():
            if any(keyword in desc_lower for keyword in keywords):
                required_inputs.append(input_type)

        # Check what inputs are actually provided in the task
        task_content = task.get("content", "")
        if isinstance(task_content, dict):
            available_inputs = list(task_content.keys())
        elif isinstance(task_content, str) and len(task_content.strip()) > 0:
            available_inputs = ["content"]
        elif task_description and len(task_description.strip()) > 0:
            available_inputs = ["description"]

        # Determine missing inputs
        for required in required_inputs:
            if not any(required in available.lower() for available in available_inputs):
                missing_inputs.append(required)

        all_available = len(missing_inputs) == 0

        return {
            "required_inputs": required_inputs,
            "available_inputs": available_inputs,
            "missing_inputs": missing_inputs,
            "all_inputs_available": all_available,
            "assessment": "sufficient" if all_available else "insufficient"
        }

    def _select_appropriate_tool(self, task_description: str) -> Dict[str, Any]:
        """Select the most appropriate tool/plugin for the task"""
        desc_lower = task_description.lower()

        # Tool mapping based on task type (this would be expanded based on available tools)
        tool_mappings = {
            "VisionAgent": {
                "keywords": ["image", "visual", "picture", "photo", "scene", "detect", "analyze"],
                "capabilities": ["image_analysis", "object_detection", "scene_description"]
            },
            "LanguageAgent": {
                "keywords": ["text", "language", "summarize", "sentiment", "dialogue", "translate"],
                "capabilities": ["summarization", "sentiment_analysis", "dialogue_generation"]
            },
            "MathReasoningAgent": {
                "keywords": ["calculate", "math", "solve", "equation", "logic", "reason"],
                "capabilities": ["calculation", "logical_reasoning", "problem_solving"]
            },
            "SimulationAgent": {
                "keywords": ["simulate", "scenario", "predict", "model", "outcome"],
                "capabilities": ["scenario_simulation", "outcome_prediction"]
            }
        }

        best_tool = None
        best_score = 0
        recommended_capabilities = []

        for tool_name, tool_info in tool_mappings.items():
            score = sum(1 for keyword in tool_info["keywords"] if keyword in desc_lower)
            if score > best_score:
                best_score = score
                best_tool = tool_name
                recommended_capabilities = tool_info["capabilities"]

        tool_selected = best_tool is not None and best_score > 0

        return {
            "tool_selected": tool_selected,
            "recommended_tool": best_tool,
            "capabilities": recommended_capabilities,
            "confidence": min(best_score * 0.3, 1.0),  # Scale confidence
            "rationale": f"Selected {best_tool} based on {best_score} matching keywords" if tool_selected else "No suitable tool identified"
        }

class MemorySystem(ABC):
    @abstractmethod
    def store(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None):
        """Store data in memory"""
        pass

    @abstractmethod
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve data from memory"""
        pass

    @abstractmethod
    def search(self, query: str, **kwargs) -> List[Any]:
        """Search memory for relevant information"""
        pass

class Task:
    def __init__(self, task_id: str, description: str, requirements: Dict[str, Any],
                 assigned_agent: Optional[str] = None, swarm_id: Optional[str] = None):
        self.task_id = task_id
        self.description = description
        self.requirements = requirements
        self.assigned_agent = assigned_agent
        self.swarm_id = swarm_id  # Swarm identifier for multi-swarm support
        self.status = "pending"
        self.result = None
        self.created_at = None
        self.completed_at = None

    def assign(self, agent_id: str):
        self.assigned_agent = agent_id
        self.status = "assigned"

    def complete(self, result: Any):
        self.result = result
        self.status = "completed"
        import time
        self.completed_at = time.time()

class DebateResult:
    def __init__(self, topic: str, contributions: List[Dict[str, Any]], consensus: Any):
        self.topic = topic
        self.contributions = contributions
        self.consensus = consensus
        self.timestamp = time.time()

class SwarmLogger:
    """Central logging system for comprehensive swarm activity tracking"""

    def __init__(self):
        self.logs = []
        self.max_logs = 10000  # Increased for comprehensive logging
        self.log_categories = {
            "reasoning": [],
            "decision": [],
            "subtask": [],
            "memory": [],
            "agent": [],
            "coordinator": [],
            "system": []
        }

    def log(self, level: str, component: str, event: str, data: Dict[str, Any] = None):
        """Log structured event with enhanced categorization and JSON output"""
        log_entry = {
            "timestamp": time.time(),
            "level": level,
            "component": component,
            "event": event,
            "data": data or {},
            "log_id": f"{component}_{int(time.time() * 1000000)}",  # Unique ID
            "category": self._categorize_log(component, event)
        }

        # Categorize log entry
        category = log_entry["category"]
        if category in self.log_categories:
            self.log_categories[category].append(log_entry)

        self.logs.append(log_entry)

        # Maintain log size per category
        for cat_logs in self.log_categories.values():
            if len(cat_logs) > self.max_logs // len(self.log_categories):
                cat_logs.pop(0)

        # Maintain overall log size
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)

        # Output structured JSON log for monitoring systems
        import json
        print(json.dumps(log_entry, default=str))

    def _categorize_log(self, component: str, event: str) -> str:
        """Categorize log entry based on component and event"""
        # Reasoning logs
        if any(keyword in event.lower() for keyword in ["reason", "think", "analyze", "evaluate", "consider"]):
            return "reasoning"
        if any(keyword in component.lower() for keyword in ["tree_of_thought", "chain_of_thought"]):
            return "reasoning"

        # Decision logs
        if any(keyword in event.lower() for keyword in ["decide", "choose", "select", "determine", "conclude"]):
            return "decision"

        # Subtask logs
        if any(keyword in event.lower() for keyword in ["subtask", "task", "execute", "delegate", "assign"]):
            return "subtask"

        # Memory logs
        if any(keyword in component.lower() for keyword in ["memory", "stm", "ltm", "store", "retrieve"]):
            return "memory"
        if any(keyword in event.lower() for keyword in ["store", "retrieve", "update", "checkpoint"]):
            return "memory"

        # Agent logs
        if any(keyword in component for keyword in ["VisionAgent", "LanguageAgent", "MathReasoningAgent", "SimulationAgent"]):
            return "agent"

        # Coordinator logs
        if "Coordinator" in component:
            return "coordinator"

        return "system"

    def log_reasoning_step(self, agent_id: str, task_id: str, step_number: int,
                           step_type: str, description: str, evidence: Optional[Any] = None,
                           conclusion: Optional[str] = None, confidence: Optional[float] = None):
        """Log individual reasoning step"""
        reasoning_data = {
            "agent_id": agent_id,
            "task_id": task_id,
            "step_number": step_number,
            "step_type": step_type,
            "description": description,
            "evidence": evidence,
            "conclusion": conclusion,
            "confidence": confidence,
            "reasoning_method": "tree_of_thought"  # Could be dynamic
        }

        self.log("INFO", f"{agent_id}_reasoning", f"Reasoning step {step_number}: {step_type}",
                reasoning_data)

    def log_decision(self, agent_id: str, task_id: str, decision: str,
                    alternatives: List[str], justification: Dict[str, Any],
                    confidence: float, decision_method: str = "analysis"):
        """Log decision-making process"""
        decision_data = {
            "agent_id": agent_id,
            "task_id": task_id,
            "decision": decision,
            "alternatives_considered": alternatives,
            "justification": justification,
            "confidence": confidence,
            "decision_method": decision_method,
            "timestamp": time.time()
        }

        self.log("INFO", f"{agent_id}_decision", f"Decision made: {decision[:50]}...",
                decision_data)

    def log_subtask(self, subtask_id: str, parent_task_id: str, agent_id: str,
                    action: str, status: str, priority: int = 1, metadata: Optional[Dict[str, Any]] = None):
        """Log subtask lifecycle events"""
        subtask_data = {
            "subtask_id": subtask_id,
            "parent_task_id": parent_task_id,
            "agent_id": agent_id,
            "action": action,
            "status": status,
            "priority": priority,
            "metadata": metadata or {},
            "timestamp": time.time()
        }

        level = "INFO" if status in ["assigned", "completed"] else "DEBUG" if status == "in_progress" else "WARNING"
        self.log(level, f"{agent_id}_subtask", f"Subtask {subtask_id}: {status} - {action}",
                subtask_data)

    def log_memory_operation(self, operation: str, key: str, component: str,
                           data_size: int = None, success: bool = True,
                           metadata: Dict[str, Any] = None):
        """Log memory operations (store, retrieve, update)"""
        memory_data = {
            "operation": operation,
            "key": key,
            "component": component,
            "data_size": data_size,
            "success": success,
            "metadata": metadata or {},
            "timestamp": time.time()
        }

        level = "INFO" if success else "WARNING"
        self.log(level, f"{component}_memory", f"Memory {operation}: {key}",
                memory_data)

    def log_agent_activity(self, agent_id: str, activity: str, task_id: Optional[str] = None,
                           duration: Optional[float] = None, success: Optional[bool] = None,
                           details: Optional[Dict[str, Any]] = None):
        """Log comprehensive agent activity"""
        activity_data = {
            "agent_id": agent_id,
            "activity": activity,
            "task_id": task_id,
            "duration": duration,
            "success": success,
            "details": details or {},
            "timestamp": time.time()
        }

        level = "INFO" if success is None or success else "WARNING" if not success else "DEBUG"
        self.log(level, agent_id, f"Activity: {activity}", activity_data)

    def log_coordinator_action(self, action: str, target_agent: Optional[str] = None,
                              task_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """Log coordinator actions and decisions"""
        coordinator_data = {
            "action": action,
            "target_agent": target_agent,
            "task_id": task_id,
            "details": details or {},
            "timestamp": time.time()
        }

        self.log("INFO", "SwarmCoordinator", f"Coordinator action: {action}", coordinator_data)

    def get_logs(self, component: Optional[str] = None, level: Optional[str] = None, limit: int = 50,
                 category: Optional[str] = None, start_time: Optional[float] = None, end_time: Optional[float] = None) -> List[Dict]:
        """Retrieve logs with enhanced filtering"""
        filtered_logs = self.logs

        # Category filter
        if category and category in self.log_categories:
            filtered_logs = self.log_categories[category]

        # Other filters
        if component:
            filtered_logs = [log for log in filtered_logs if log["component"] == component]
        if level:
            filtered_logs = [log for log in filtered_logs if log["level"] == level]
        if start_time:
            filtered_logs = [log for log in filtered_logs if log["timestamp"] >= start_time]
        if end_time:
            filtered_logs = [log for log in filtered_logs if log["timestamp"] <= end_time]

        return filtered_logs[-limit:] if limit else filtered_logs

    def get_reasoning_trace(self, task_id: str, agent_id: str = None) -> List[Dict]:
        """Get complete reasoning trace for a task"""
        reasoning_logs = self.get_logs(category="reasoning", limit=None)
        trace = [log for log in reasoning_logs if log["data"].get("task_id") == task_id]

        if agent_id:
            trace = [log for log in trace if log["data"].get("agent_id") == agent_id]

        # Sort by step number
        trace.sort(key=lambda x: x["data"].get("step_number", 0))
        return trace

    def get_decision_history(self, task_id: str = None, agent_id: str = None) -> List[Dict]:
        """Get decision history with optional filtering"""
        decision_logs = self.get_logs(category="decision", limit=None)

        if task_id:
            decision_logs = [log for log in decision_logs if log["data"].get("task_id") == task_id]
        if agent_id:
            decision_logs = [log for log in decision_logs if log["data"].get("agent_id") == agent_id]

        return decision_logs

    def get_subtask_timeline(self, task_id: str) -> List[Dict]:
        """Get subtask execution timeline for a task"""
        subtask_logs = self.get_logs(category="subtask", limit=None)
        timeline = [log for log in subtask_logs if log["data"].get("parent_task_id") == task_id]

        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])
        return timeline

    def get_memory_operations(self, component: str = None, operation: str = None,
                            time_window: float = None) -> List[Dict]:
        """Get memory operation logs with filtering"""
        memory_logs = self.get_logs(category="memory", limit=None)

        if component:
            memory_logs = [log for log in memory_logs if log["data"].get("component") == component]
        if operation:
            memory_logs = [log for log in memory_logs if log["data"].get("operation") == operation]
        if time_window:
            cutoff_time = time.time() - time_window
            memory_logs = [log for log in memory_logs if log["timestamp"] >= cutoff_time]

        return memory_logs

    def export_logs_json(self, filename: str, category: Optional[str] = None,
                         start_time: Optional[float] = None, end_time: Optional[float] = None):
        """Export logs to JSON file for analytics dashboard and monitoring systems"""
        export_data = {
            "@timestamp": time.time(),
            "export_type": "swarm_activity_logs",
            "total_logs": len(self.logs),
            "categories": list(self.log_categories.keys()),
            "filters_applied": {
                "category": category,
                "start_time": start_time,
                "end_time": end_time
            }
        }

        # Get filtered logs
        if category:
            export_data["logs"] = self.get_logs(category=category, limit=None,
                                               start_time=start_time, end_time=end_time)
        else:
            export_data["logs"] = self.get_logs(limit=None, start_time=start_time, end_time=end_time)

        # Add summary statistics
        export_data["summary"] = self._generate_log_summary(export_data["logs"])

        # Ensure all timestamps are in ISO format for better compatibility
        for log in export_data["logs"]:
            if "timestamp" in log:
                log["@timestamp"] = log["timestamp"]
                # Keep both for backward compatibility

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str, ensure_ascii=False)

        # Log the export operation
        self.log("INFO", "SwarmLogger", f"Exported {len(export_data['logs'])} logs to {filename}",
                {"filename": filename, "log_count": len(export_data["logs"]), "category": category})

    def _generate_log_summary(self, logs: List[Dict]) -> Dict[str, Any]:
        """Generate summary statistics for exported logs"""
        if not logs:
            return {"total_logs": 0}

        summary = {
            "total_logs": len(logs),
            "time_range": {
                "start": min(log["timestamp"] for log in logs),
                "end": max(log["timestamp"] for log in logs),
                "duration_hours": (max(log["timestamp"] for log in logs) - min(log["timestamp"] for log in logs)) / 3600
            },
            "level_distribution": {},
            "component_distribution": {},
            "category_distribution": {},
            "event_types": {}
        }

        for log in logs:
            # Level distribution
            level = log.get("level", "UNKNOWN")
            summary["level_distribution"][level] = summary["level_distribution"].get(level, 0) + 1

            # Component distribution
            component = log.get("component", "UNKNOWN")
            summary["component_distribution"][component] = summary["component_distribution"].get(component, 0) + 1

            # Event types
            event = log.get("event", "UNKNOWN")
            summary["event_types"][event] = summary["event_types"].get(event, 0) + 1

        # Category distribution (based on our categorization)
        for log in logs:
            category = self._categorize_log(log.get("component", ""), log.get("event", ""))
            summary["category_distribution"][category] = summary["category_distribution"].get(category, 0) + 1

        return summary

    def save_logs(self, filename: str):
        """Save logs to file for analysis (legacy method)"""
        self.export_logs_json(filename)

# Global logger instance
logger = SwarmLogger()

class SwarmManager:
    """Central manager for multiple swarms"""

    def __init__(self):
        self.swarms: Dict[str, 'SwarmCoordinator'] = {}  # swarm_id -> coordinator
        self.message_router: Dict[str, List[Message]] = {}  # swarm_id -> message_queue
        self.shared_memory = None  # Optional shared long-term memory

    def create_swarm(self, swarm_id: str, coordinator: 'SwarmCoordinator') -> bool:
        """Create a new swarm with the given coordinator"""
        if swarm_id in self.swarms:
            logger.log("WARNING", "SwarmManager", f"Swarm {swarm_id} already exists")
            return False

        self.swarms[swarm_id] = coordinator
        self.message_router[swarm_id] = []
        coordinator.swarm_id = swarm_id  # Set swarm_id on coordinator

        logger.log("INFO", "SwarmManager", f"Created swarm {swarm_id}")
        return True

    def remove_swarm(self, swarm_id: str) -> bool:
        """Remove a swarm"""
        if swarm_id not in self.swarms:
            logger.log("WARNING", "SwarmManager", f"Swarm {swarm_id} does not exist")
            return False

        del self.swarms[swarm_id]
        del self.message_router[swarm_id]

        logger.log("INFO", "SwarmManager", f"Removed swarm {swarm_id}")
        return True

    def get_swarm(self, swarm_id: str) -> Optional['SwarmCoordinator']:
        """Get a swarm coordinator by ID"""
        return self.swarms.get(swarm_id)

    def route_message(self, message: Message) -> bool:
        """Route a message to the appropriate swarm"""
        swarm_id = message.swarm_id
        if not swarm_id:
            logger.log("WARNING", "SwarmManager", f"Message without swarm_id: {message.sender} -> {message.receiver}")
            return False

        if swarm_id not in self.message_router:
            logger.log("WARNING", "SwarmManager", f"Unknown swarm {swarm_id} for message routing")
            return False

        self.message_router[swarm_id].append(message)

        # Deliver message to the appropriate agent in the swarm
        coordinator = self.swarms.get(swarm_id)
        if coordinator:
            coordinator.receive_message(message)

        return True

    def broadcast_to_swarm(self, swarm_id: str, message: Message) -> bool:
        """Broadcast a message to all agents in a swarm"""
        coordinator = self.swarms.get(swarm_id)
        if not coordinator:
            return False

        # Send to all registered agents in the swarm
        for agent_id in coordinator.registered_agents:
            swarm_message = Message(
                sender=message.sender,
                receiver=agent_id,
                message_type=message.message_type,
                content=message.content,
                timestamp=message.timestamp,
                swarm_id=swarm_id,
                metadata=message.metadata
            )
            coordinator.receive_message_for_agent(agent_id, swarm_message)

        return True

    def get_all_swarms(self) -> List[str]:
        """Get list of all swarm IDs"""
        return list(self.swarms.keys())

    def get_swarm_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all swarms"""
        stats = {}
        for swarm_id, coordinator in self.swarms.items():
            stats[swarm_id] = {
                "agent_count": len(coordinator.registered_agents),
                "active_tasks": len(coordinator.delegation_system.active_tasks),
                "mini_coordinators": len(coordinator.mini_coordinators),
                "load_balance": coordinator.get_load_balance_report()
            }
        return stats

    def set_shared_memory(self, memory_system):
        """Set shared long-term memory for all swarms"""
        self.shared_memory = memory_system

class FederationManager:
    """Manages coordination between multiple swarms in a federation"""

    def __init__(self):
        self.swarm_manager = SwarmManager()
        self.federation_policies = {
            "resource_sharing": True,
            "task_delegation": True,
            "conflict_resolution": "consensus_based",
            "communication_protocol": "federated_messaging"
        }
        self.inter_swarm_communications = []
        self.resource_pool = {}  # Shared resources across swarms
        self.federation_goals = []
        self.conflict_history = []

    def create_federation_swarm(self, swarm_id: str, coordinator, capabilities: List[str] = None) -> bool:
        """Create a new swarm within the federation"""
        success = self.swarm_manager.create_swarm(swarm_id, coordinator)
        if success:
            # Register swarm capabilities for federation-level coordination
            self.resource_pool[swarm_id] = {
                "capabilities": capabilities or [],
                "available_resources": {},
                "shared_knowledge": {},
                "cooperation_score": 1.0
            }
            logger.log("INFO", "FederationManager", f"Created federation swarm: {swarm_id}", {"capabilities": capabilities})
        return success

    def federated_task_delegation(self, task: Dict[str, Any], source_swarm: str = None) -> Dict[str, Any]:
        """Delegate tasks across the federation for optimal execution"""
        # Analyze task requirements
        task_requirements = task.get("requirements", {})
        task_type = task.get("type", "general")

        # Find best swarm for this task
        best_swarm = self._find_optimal_swarm(task_requirements, task_type, source_swarm)

        if best_swarm and best_swarm != source_swarm:
            # Delegate to another swarm
            result = self._delegate_to_swarm(task, best_swarm, source_swarm)
            logger.log("INFO", "FederationManager", f"Federated task delegation: {source_swarm} -> {best_swarm}",
                      {"task_type": task_type, "delegation_reason": "optimal_resource_allocation"})
            return result
        else:
            # Execute in source swarm or current swarm
            return {"status": "executed_locally", "swarm": source_swarm or "default"}

    def _find_optimal_swarm(self, requirements: Dict[str, Any], task_type: str, exclude_swarm: str = None) -> Optional[str]:
        """Find the optimal swarm for a given task"""
        best_swarm = None
        best_score = 0

        for swarm_id, resources in self.resource_pool.items():
            if exclude_swarm and swarm_id == exclude_swarm:
                continue

            # Calculate fitness score based on capabilities and current load
            capability_score = self._calculate_capability_match(resources["capabilities"], task_type)
            load_score = self._calculate_load_score(swarm_id)
            cooperation_score = resources["cooperation_score"]

            total_score = (capability_score * 0.5) + (load_score * 0.3) + (cooperation_score * 0.2)

            if total_score > best_score:
                best_score = total_score
                best_swarm = swarm_id

        return best_swarm if best_score > 0.6 else None  # Minimum threshold

    def _calculate_capability_match(self, capabilities: List[str], task_type: str) -> float:
        """Calculate how well swarm capabilities match task requirements"""
        capability_mapping = {
            "analysis": ["VisionAgent", "LanguageAgent", "MathReasoningAgent"],
            "computation": ["MathReasoningAgent", "SimulationAgent"],
            "communication": ["LanguageAgent"],
            "simulation": ["SimulationAgent"],
            "vision": ["VisionAgent"]
        }

        required_capabilities = capability_mapping.get(task_type, [])
        if not required_capabilities:
            return 0.5  # Neutral score for unknown task types

        matches = sum(1 for cap in required_capabilities if cap in capabilities)
        return matches / len(required_capabilities) if required_capabilities else 0

    def _calculate_load_score(self, swarm_id: str) -> float:
        """Calculate load score (lower load = higher score)"""
        try:
            stats = self.swarm_manager.get_swarm_stats().get(swarm_id, {})
            active_tasks = stats.get("active_tasks", 0)
            agent_count = stats.get("agent_count", 1)

            # Normalize load (0-1 scale, lower is better)
            load_ratio = min(active_tasks / (agent_count * 2), 1.0)  # Assume 2 tasks per agent capacity
            return 1.0 - load_ratio  # Invert so lower load = higher score
        except:
            return 0.5  # Neutral score if stats unavailable

    def _delegate_to_swarm(self, task: Dict[str, Any], target_swarm: str, source_swarm: str = None) -> Dict[str, Any]:
        """Delegate a task to another swarm"""
        # Create federation message
        federation_message = {
            "type": "task_delegation",
            "task": task,
            "source_swarm": source_swarm,
            "target_swarm": target_swarm,
            "delegation_timestamp": time.time(),
            "federation_metadata": {
                "reason": "resource_optimization",
                "expected_benefits": ["load_balancing", "capability_matching"]
            }
        }

        # Record the delegation
        self.inter_swarm_communications.append(federation_message)

        # In a real implementation, this would send the message to the target swarm
        # For now, return success status
        return {
            "status": "delegated",
            "target_swarm": target_swarm,
            "delegation_id": f"fed_del_{int(time.time())}_{len(self.inter_swarm_communications)}"
        }

    def resolve_conflicts(self, conflict_description: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflicts between swarms using federation policies"""
        conflict_type = conflict_description.get("type", "resource")
        involved_swarms = conflict_description.get("swarms", [])

        resolution_strategy = self.federation_policies.get("conflict_resolution", "consensus_based")

        if resolution_strategy == "consensus_based":
            resolution = self._consensus_resolution(conflict_description)
        elif resolution_strategy == "priority_based":
            resolution = self._priority_resolution(conflict_description)
        else:
            resolution = self._default_resolution(conflict_description)

        # Record conflict resolution
        self.conflict_history.append({
            "conflict": conflict_description,
            "resolution": resolution,
            "timestamp": time.time(),
            "strategy_used": resolution_strategy
        })

        logger.log("INFO", "FederationManager", f"Resolved {conflict_type} conflict between swarms",
                  {"involved_swarms": involved_swarms, "resolution_strategy": resolution_strategy})

        return resolution

    def _consensus_resolution(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflicts through consensus among involved swarms"""
        # Simplified consensus mechanism
        return {
            "decision": "shared_resource_usage",
            "rationale": "Consensus-based resource sharing",
            "agreements": ["equal_access", "cooperative_usage"],
            "monitoring_required": True
        }

    def _priority_resolution(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflicts based on swarm priorities"""
        # Use swarm cooperation scores to determine priority
        involved_swarms = conflict.get("swarms", [])
        if involved_swarms:
            # Give priority to swarm with higher cooperation score
            prioritized_swarm = max(involved_swarms,
                                  key=lambda s: self.resource_pool.get(s, {}).get("cooperation_score", 0))
            return {
                "decision": f"priority_to_{prioritized_swarm}",
                "rationale": f"Higher cooperation score for {prioritized_swarm}",
                "prioritized_swarm": prioritized_swarm
            }
        return {"decision": "no_resolution", "rationale": "Unable to determine priority"}

    def _default_resolution(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Default conflict resolution strategy"""
        return {
            "decision": "escalate_to_human",
            "rationale": "Default escalation for unresolved conflicts",
            "requires_human_intervention": True
        }

    def share_resources(self, resource_request: Dict[str, Any]) -> Dict[str, Any]:
        """Facilitate resource sharing between swarms"""
        resource_type = resource_request.get("type", "agent")
        requesting_swarm = resource_request.get("requesting_swarm")
        required_capability = resource_request.get("capability")

        # Find swarms with available resources
        available_swarms = []
        for swarm_id, resources in self.resource_pool.items():
            if swarm_id != requesting_swarm and required_capability in resources.get("capabilities", []):
                available_swarms.append(swarm_id)

        if available_swarms:
            # Select best swarm to share from
            selected_swarm = self._select_resource_sharing_swarm(available_swarms, resource_type)

            return {
                "status": "resource_available",
                "providing_swarm": selected_swarm,
                "resource_type": resource_type,
                "sharing_agreement": {
                    "duration": "temporary",
                    "conditions": ["fair_usage", "return_when_complete"],
                    "monitoring": True
                }
            }
        else:
            return {
                "status": "resource_unavailable",
                "reason": f"No swarm available with capability: {required_capability}"
            }

    def _select_resource_sharing_swarm(self, available_swarms: List[str], resource_type: str) -> str:
        """Select the best swarm for resource sharing"""
        # Simple selection based on cooperation score and current load
        return max(available_swarms,
                  key=lambda s: self.resource_pool.get(s, {}).get("cooperation_score", 0))

    def update_cooperation_scores(self, swarm_interactions: Dict[str, Any]):
        """Update cooperation scores based on swarm interactions"""
        for swarm_id, interactions in swarm_interactions.items():
            if swarm_id in self.resource_pool:
                # Calculate cooperation score based on successful interactions
                successful_interactions = interactions.get("successful", 0)
                total_interactions = interactions.get("total", 1)

                cooperation_score = successful_interactions / total_interactions
                self.resource_pool[swarm_id]["cooperation_score"] = cooperation_score

                logger.log("INFO", "FederationManager", f"Updated cooperation score for {swarm_id}",
                          {"new_score": cooperation_score})

    def get_federation_metrics(self) -> Dict[str, Any]:
        """Get comprehensive federation-level metrics"""
        swarm_stats = self.swarm_manager.get_swarm_stats()

        federation_metrics = {
            "total_swarms": len(swarm_stats),
            "federation_health": self._calculate_federation_health(swarm_stats),
            "resource_utilization": self._calculate_resource_utilization(swarm_stats),
            "inter_swarm_communications": len(self.inter_swarm_communications),
            "conflict_resolution_rate": self._calculate_conflict_resolution_rate(),
            "cooperation_scores": {swarm_id: resources["cooperation_score"]
                                 for swarm_id, resources in self.resource_pool.items()},
            "federation_goals_progress": self._calculate_goals_progress()
        }

        return federation_metrics

    def _calculate_federation_health(self, swarm_stats: Dict[str, Any]) -> float:
        """Calculate overall federation health score"""
        if not swarm_stats:
            return 0.0

        health_scores = []
        for swarm_id, stats in swarm_stats.items():
            # Calculate individual swarm health
            active_tasks = stats.get("active_tasks", 0)
            agent_count = stats.get("agent_count", 1)
            load_ratio = active_tasks / agent_count if agent_count > 0 else 0

            # Health score based on load balance (ideal load is 1-2 tasks per agent)
            if load_ratio <= 2:
                health = 1.0
            elif load_ratio <= 4:
                health = 0.7
            else:
                health = 0.4

            health_scores.append(health)

        return sum(health_scores) / len(health_scores) if health_scores else 0.0

    def _calculate_resource_utilization(self, swarm_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate federation-wide resource utilization"""
        total_agents = sum(stats.get("agent_count", 0) for stats in swarm_stats.values())
        total_active_tasks = sum(stats.get("active_tasks", 0) for stats in swarm_stats.values())
        total_mini_coordinators = sum(stats.get("mini_coordinators", 0) for stats in swarm_stats.values())

        return {
            "total_agents": total_agents,
            "total_active_tasks": total_active_tasks,
            "total_mini_coordinators": total_mini_coordinators,
            "avg_tasks_per_agent": total_active_tasks / total_agents if total_agents > 0 else 0,
            "utilization_efficiency": min(total_active_tasks / (total_agents * 2), 1.0) if total_agents > 0 else 0  # Assuming 2 tasks/agent capacity
        }

    def _calculate_conflict_resolution_rate(self) -> float:
        """Calculate the rate of successful conflict resolution"""
        if not self.conflict_history:
            return 1.0  # No conflicts = perfect resolution rate

        resolved_conflicts = sum(1 for conflict in self.conflict_history
                               if conflict.get("resolution", {}).get("decision") != "escalate_to_human")
        return resolved_conflicts / len(self.conflict_history)

    def _calculate_goals_progress(self) -> Dict[str, Any]:
        """Calculate progress toward federation goals"""
        # Placeholder for federation goals tracking
        return {
            "goals_defined": len(self.federation_goals),
            "goals_achieved": 0,  # Would be calculated based on actual goal tracking
            "progress_percentage": 0.0
        }

    def optimize_federation(self) -> Dict[str, Any]:
        """Perform federation-wide optimization"""
        optimizations = {
            "load_balancing_actions": [],
            "resource_reallocations": [],
            "capability_gaps": [],
            "efficiency_improvements": []
        }

        swarm_stats = self.swarm_manager.get_swarm_stats()

        # Identify load imbalances
        for swarm_id, stats in swarm_stats.items():
            active_tasks = stats.get("active_tasks", 0)
            agent_count = stats.get("agent_count", 1)
            load_ratio = active_tasks / agent_count if agent_count > 0 else 0

            if load_ratio > 3:  # Overloaded
                optimizations["load_balancing_actions"].append({
                    "swarm": swarm_id,
                    "action": "reduce_load",
                    "current_load": load_ratio,
                    "recommendation": "Delegate tasks to less loaded swarms"
                })
            elif load_ratio < 0.5:  # Underutilized
                optimizations["load_balancing_actions"].append({
                    "swarm": swarm_id,
                    "action": "increase_utilization",
                    "current_load": load_ratio,
                    "recommendation": "Accept more tasks from federation"
                })

        # Identify capability gaps
        all_capabilities = set()
        for resources in self.resource_pool.values():
            all_capabilities.update(resources.get("capabilities", []))

        # Check for missing critical capabilities
        critical_capabilities = ["VisionAgent", "LanguageAgent", "MathReasoningAgent"]
        missing_capabilities = set(critical_capabilities) - all_capabilities

        if missing_capabilities:
            optimizations["capability_gaps"].extend([
                {"capability": cap, "severity": "high", "recommendation": "Add swarm with this capability"}
                for cap in missing_capabilities
            ])

        logger.log("INFO", "FederationManager", "Federation optimization completed",
                  {"optimizations_found": sum(len(actions) for actions in optimizations.values())})

        return optimizations

# Global instances
swarm_manager = SwarmManager()
federation_manager = FederationManager()

class MetricsTracker:
    """Track performance metrics for agents and reasoning processes"""

    def __init__(self):
        self.agent_metrics = {}
        self.reasoning_metrics = {}
        self.consensus_metrics = []
        self.task_metrics = []
        self.scoring_feedback = []  # For fine-tuning scoring methods
        self.performance_history = []  # Historical performance data
        self.meta_learning_patterns = {}  # Track successful patterns across tasks
        self.strategy_success_rates = {}  # Track strategy effectiveness
        self.agent_combination_success = {}  # Track successful agent combinations
        self.reasoning_logs = {}  # Store detailed reasoning traces
        self.decision_audit_trail = []  # Audit trail for all decisions

    def track_agent_performance(self, agent_id: str, task_type: str, success: bool, execution_time: float, result_quality: float = 0.5):
        """Track agent performance metrics"""
        if agent_id not in self.agent_metrics:
            self.agent_metrics[agent_id] = {
                "total_tasks": 0,
                "successful_tasks": 0,
                "total_execution_time": 0,
                "avg_quality": 0,
                "task_types": {}
            }

        metrics = self.agent_metrics[agent_id]
        metrics["total_tasks"] += 1
        metrics["total_execution_time"] += execution_time
        if success:
            metrics["successful_tasks"] += 1

        # Update average quality
        metrics["avg_quality"] = (metrics["avg_quality"] * (metrics["total_tasks"] - 1) + result_quality) / metrics["total_tasks"]

        # Track by task type
        if task_type not in metrics["task_types"]:
            metrics["task_types"][task_type] = {"count": 0, "success": 0}
        metrics["task_types"][task_type]["count"] += 1
        if success:
            metrics["task_types"][task_type]["success"] += 1

    def track_reasoning_performance(self, reasoning_type: str, steps: int, execution_time: float, success: bool):
        """Track reasoning performance"""
        if reasoning_type not in self.reasoning_metrics:
            self.reasoning_metrics[reasoning_type] = {
                "total_runs": 0,
                "successful_runs": 0,
                "total_steps": 0,
                "total_time": 0
            }

        metrics = self.reasoning_metrics[reasoning_type]
        metrics["total_runs"] += 1
        metrics["total_steps"] += steps
        metrics["total_time"] += execution_time
        if success:
            metrics["successful_runs"] += 1

    def track_consensus(self, topic: str, participants: int, consensus_score: float, execution_time: float):
        """Track consensus performance"""
        self.consensus_metrics.append({
            "timestamp": time.time(),
            "topic": topic,
            "participants": participants,
            "consensus_score": consensus_score,
            "execution_time": execution_time
        })

    def track_task_performance(self, task_id: str, description: str, total_time: float,
                             subtasks_completed: int, total_subtasks: int, final_quality: float):
        """Track overall task performance"""
        success_rate = subtasks_completed / total_subtasks if total_subtasks > 0 else 0
        self.task_metrics.append({
            "task_id": task_id,
            "description": description,
            "total_time": total_time,
            "success_rate": success_rate,
            "final_quality": final_quality,
            "timestamp": time.time()
        })

    def add_scoring_feedback(self, task_type: str, actual_quality: float, predicted_quality: float,
                           scoring_weights: Dict[str, float], outcome: str):
        """Add feedback for fine-tuning scoring methods"""
        feedback = {
            "task_type": task_type,
            "actual_quality": actual_quality,
            "predicted_quality": predicted_quality,
            "error": abs(actual_quality - predicted_quality),
            "scoring_weights": scoring_weights.copy(),
            "outcome": outcome,
            "timestamp": time.time()
        }
        self.scoring_feedback.append(feedback)

        # Store in performance history for analysis
        self.performance_history.append(feedback)

    def get_scoring_adjustments(self, task_type: str) -> Dict[str, float]:
        """Analyze feedback and suggest scoring weight adjustments"""
        relevant_feedback = [f for f in self.scoring_feedback if f["task_type"] == task_type]

        if len(relevant_feedback) < 5:  # Need minimum data
            return {}

        # Analyze error patterns
        avg_error = sum(f["error"] for f in relevant_feedback) / len(relevant_feedback)

        # Suggest adjustments based on error analysis
        adjustments = {}
        if avg_error > 0.3:  # High error, need adjustment
            # Simple adjustment logic - could be more sophisticated
            adjustments["accuracy"] = 0.1 if avg_error > 0.4 else 0.05
            adjustments["reliability"] = -0.05 if avg_error < 0.2 else 0.0

        return adjustments

    def track_strategy_success(self, task_type: str, strategy_used: str, success_score: float,
                              agents_used: List[str], execution_time: float):
        """Track strategy success for meta-learning"""
        key = f"{task_type}_{strategy_used}"

        if key not in self.strategy_success_rates:
            self.strategy_success_rates[key] = {
                "total_uses": 0,
                "total_success": 0,
                "avg_success": 0,
                "avg_time": 0,
                "agent_combinations": []
            }

        strategy_data = self.strategy_success_rates[key]
        strategy_data["total_uses"] += 1
        strategy_data["total_success"] += success_score
        strategy_data["avg_success"] = strategy_data["total_success"] / strategy_data["total_uses"]
        strategy_data["avg_time"] = (strategy_data["avg_time"] * (strategy_data["total_uses"] - 1) + execution_time) / strategy_data["total_uses"]

        # Track agent combinations
        agent_combo = tuple(sorted(agents_used))
        strategy_data["agent_combinations"].append({
            "combination": agent_combo,
            "success": success_score,
            "time": execution_time
        })

        # Update agent combination success rates
        combo_key = agent_combo
        if combo_key not in self.agent_combination_success:
            self.agent_combination_success[combo_key] = {
                "uses": 0,
                "total_success": 0,
                "avg_success": 0
            }

        combo_data = self.agent_combination_success[combo_key]
        combo_data["uses"] += 1
        combo_data["total_success"] += success_score
        combo_data["avg_success"] = combo_data["total_success"] / combo_data["uses"]

    def get_optimal_strategy(self, task_type: str, available_agents: List[str]) -> Dict[str, Any]:
        """Get the optimal strategy and agent combination for a task type based on meta-learning"""
        # Find best strategy for task type
        best_strategy = None
        best_score = 0

        for key, data in self.strategy_success_rates.items():
            if key.startswith(f"{task_type}_"):
                strategy_name = key.split("_", 1)[1]
                # Score based on success rate and efficiency (lower time is better)
                efficiency_score = data["avg_success"] / max(data["avg_time"], 0.1)  # Avoid division by zero

                if efficiency_score > best_score:
                    best_score = efficiency_score
                    best_strategy = {
                        "strategy": strategy_name,
                        "expected_success": data["avg_success"],
                        "expected_time": data["avg_time"],
                        "confidence": min(data["total_uses"] / 10, 1.0)  # Confidence based on sample size
                    }

        # Find best agent combination
        best_combo = None
        best_combo_score = 0

        for combo, data in self.agent_combination_success.items():
            # Check if all agents in combo are available
            if all(agent in available_agents for agent in combo):
                if data["avg_success"] > best_combo_score:
                    best_combo_score = data["avg_success"]
                    best_combo = {
                        "agents": list(combo),
                        "expected_success": data["avg_success"],
                        "confidence": min(data["uses"] / 5, 1.0)
                    }

        return {
            "recommended_strategy": best_strategy,
            "recommended_agents": best_combo,
            "meta_learning_confidence": min(len(self.strategy_success_rates), len(self.agent_combination_success)) / 10
        }

    def adapt_heuristics_from_meta_learning(self):
        """Adapt system heuristics based on meta-learning patterns"""
        adaptations = {}

        # Analyze strategy preferences
        if self.strategy_success_rates:
            # Find most successful strategies
            strategy_performance = {}
            for key, data in self.strategy_success_rates.items():
                task_type = key.split("_")[0]
                if task_type not in strategy_performance:
                    strategy_performance[task_type] = []
                strategy_performance[task_type].append((key, data["avg_success"]))

            # Update strategy weights based on performance
            for task_type, strategies in strategy_performance.items():
                if len(strategies) > 1:
                    strategies.sort(key=lambda x: x[1], reverse=True)
                    best_strategy = strategies[0][0]
                    adaptations[f"prefer_{best_strategy}"] = f"Increased preference for {best_strategy} based on {len(strategies)} trials"

        # Analyze agent combination patterns
        if self.agent_combination_success:
            # Find most successful combinations
            sorted_combos = sorted(self.agent_combination_success.items(),
                                 key=lambda x: x[1]["avg_success"], reverse=True)

            if sorted_combos:
                best_combo = sorted_combos[0][0]
                adaptations["best_agent_combo"] = f"Most successful agent combination: {best_combo}"

        return adaptations

    def log_reasoning_trace(self, agent_id: str, task_id: str, reasoning_steps: List[Dict[str, Any]],
                           final_decision: str, confidence: float):
        """Log detailed reasoning trace for an agent's decision"""
        trace_id = f"{agent_id}_{task_id}_{int(time.time())}"

        reasoning_trace = {
            "trace_id": trace_id,
            "agent_id": agent_id,
            "task_id": task_id,
            "timestamp": time.time(),
            "reasoning_steps": reasoning_steps,
            "final_decision": final_decision,
            "confidence": confidence,
            "step_count": len(reasoning_steps)
        }

        if task_id not in self.reasoning_logs:
            self.reasoning_logs[task_id] = []

        self.reasoning_logs[task_id].append(reasoning_trace)

        # Also log to audit trail
        self.decision_audit_trail.append({
            "type": "reasoning_trace",
            "trace_id": trace_id,
            "agent_id": agent_id,
            "task_id": task_id,
            "decision": final_decision,
            "confidence": confidence,
            "timestamp": time.time()
        })

    def log_decision_justification(self, agent_id: str, task_id: str, decision: str,
                                  justification: Dict[str, Any], alternatives_considered: List[str] = None):
        """Log detailed justification for a decision"""
        justification_entry = {
            "agent_id": agent_id,
            "task_id": task_id,
            "decision": decision,
            "justification": justification,
            "alternatives_considered": alternatives_considered or [],
            "timestamp": time.time()
        }

        self.decision_audit_trail.append({
            "type": "decision_justification",
            "data": justification_entry
        })

    def log_decision_card(self, task_id: str, decision_type: str, decision_made: str,
                         confidence: float, self_ask_prompts: List[str] = None,
                         reasoning_snippets: List[str] = None, alternatives: List[str] = None,
                         justification: str = ""):
        """Log decision card data for visualization"""
        if not hasattr(self, 'decision_cards'):
            self.decision_cards = []

        decision_card = {
            "task_id": task_id,
            "decision_type": decision_type,
            "decision_made": decision_made,
            "confidence": confidence,
            "self_ask_prompts": self_ask_prompts or [],
            "reasoning_snippets": reasoning_snippets or [],
            "alternatives_considered": alternatives or [],
            "justification": justification,
            "timestamp": time.time()
        }

        self.decision_cards.append(decision_card)

        # Keep only recent decision cards (last 50)
        if len(self.decision_cards) > 50:
            self.decision_cards.pop(0)

        # Also log to audit trail
        self.decision_audit_trail.append({
            "type": "decision_card",
            "data": decision_card
        })

    def get_reasoning_explanation(self, task_id: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve reasoning explanation for a task"""
        if task_id not in self.reasoning_logs:
            return {"error": "No reasoning logs found for task"}

        traces = self.reasoning_logs[task_id]
        if agent_id:
            traces = [t for t in traces if t["agent_id"] == agent_id]

        if not traces:
            return {"error": f"No reasoning logs found for agent {agent_id}"}

        # Return the most recent trace
        latest_trace = max(traces, key=lambda x: x["timestamp"])

        explanation = {
            "task_id": task_id,
            "agent_id": latest_trace["agent_id"],
            "reasoning_steps": latest_trace["reasoning_steps"],
            "final_decision": latest_trace["final_decision"],
            "confidence": latest_trace["confidence"],
            "step_count": latest_trace["step_count"],
            "timestamp": latest_trace["timestamp"]
        }

        return explanation

    def get_audit_trail(self, task_id: Optional[str] = None, agent_id: Optional[str] = None,
                        start_time: Optional[float] = None, end_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve audit trail with optional filtering"""
        trail = self.decision_audit_trail.copy()

        # Apply filters
        if task_id:
            trail = [entry for entry in trail if entry.get("task_id") == task_id or
                    (entry.get("type") == "decision_justification" and entry["data"].get("task_id") == task_id)]

        if agent_id:
            trail = [entry for entry in trail if entry.get("agent_id") == agent_id or
                    (entry.get("type") == "decision_justification" and entry["data"].get("agent_id") == agent_id)]

        if start_time:
            trail = [entry for entry in trail if entry.get("timestamp", 0) >= start_time]

        if end_time:
            trail = [entry for entry in trail if entry.get("timestamp", 0) <= end_time]

        # Sort by timestamp
        trail.sort(key=lambda x: x.get("timestamp", 0))

        return trail

    def generate_transparency_report(self, task_id: str) -> str:
        """Generate comprehensive transparency report for a task"""
        report = f"TRANSPARENCY REPORT FOR TASK: {task_id}\n"
        report += "=" * 60 + "\n\n"

        # Get reasoning explanations
        reasoning_explanation = self.get_reasoning_explanation(task_id)
        if "error" not in reasoning_explanation:
            report += "REASONING ANALYSIS:\n"
            report += f"Agent: {reasoning_explanation['agent_id']}\n"
            report += f"Confidence: {reasoning_explanation['confidence']:.2f}\n"
            report += f"Reasoning Steps: {reasoning_explanation['step_count']}\n"
            report += f"Final Decision: {reasoning_explanation['final_decision']}\n\n"

            report += "REASONING TRACE:\n"
            for i, step in enumerate(reasoning_explanation['reasoning_steps'], 1):
                report += f"Step {i}: {step.get('description', 'Unknown')}\n"
                if 'evidence' in step:
                    report += f"  Evidence: {step['evidence']}\n"
                if 'conclusion' in step:
                    report += f"  Conclusion: {step['conclusion']}\n"
            report += "\n"

        # Get audit trail
        audit_trail = self.get_audit_trail(task_id=task_id)
        if audit_trail:
            report += "AUDIT TRAIL:\n"
            for entry in audit_trail:
                timestamp = time.strftime('%H:%M:%S', time.localtime(entry.get('timestamp', 0)))
                if entry['type'] == 'reasoning_trace':
                    report += f"[{timestamp}] {entry['agent_id']}: Reasoning trace logged (confidence: {entry['confidence']:.2f})\n"
                elif entry['type'] == 'decision_justification':
                    decision_data = entry['data']
                    report += f"[{timestamp}] {decision_data['agent_id']}: Decision '{decision_data['decision']}' justified\n"
            report += "\n"

        # Performance metrics
        task_metrics = [m for m in self.task_metrics if m['task_id'] == task_id]
        if task_metrics:
            metric = task_metrics[0]
            report += "PERFORMANCE METRICS:\n"
            report += f"Execution Time: {metric['total_time']:.2f}s\n"
            report += f"Success Rate: {metric['success_rate']*100:.1f}%\n"
            report += f"Quality Score: {metric['final_quality']:.2f}\n"

        return report

    def get_comprehensive_traceability_report(self, task_id: Optional[str] = None, agent_id: Optional[str] = None,
                                            start_time: Optional[float] = None, end_time: Optional[float] = None) -> Dict[str, Any]:
        """Generate comprehensive traceability report with full reasoning chains"""
        report = {
            "report_type": "comprehensive_traceability",
            "generated_at": time.time(),
            "time_range": {"start": start_time, "end": end_time},
            "filters": {"task_id": task_id, "agent_id": agent_id}
        }

        # Collect all reasoning traces
        reasoning_traces = []
        if task_id:
            trace = self.get_reasoning_explanation(task_id)
            if "error" not in trace:
                reasoning_traces.append(trace)
        else:
            # Get traces for all tasks in time range
            for task_traces in self.reasoning_logs.values():
                for trace in task_traces:
                    if self._trace_matches_filters(trace, agent_id, start_time, end_time):
                        reasoning_traces.append(trace)

        report["reasoning_traces"] = reasoning_traces

        # Collect decision audit trail
        audit_trail = self.get_audit_trail(task_id, agent_id, start_time, end_time)
        report["decision_audit_trail"] = audit_trail

        # Collect failure analysis
        failures = []
        if hasattr(self, 'failure_logs'):
            for failure in self.failure_logs:
                if self._failure_matches_filters(failure, task_id, agent_id, start_time, end_time):
                    failures.append(failure)
        report["failure_analysis"] = failures

        # Collect performance metrics
        performance_data = {
            "agent_performance": self.agent_metrics.copy(),
            "reasoning_performance": self.reasoning_metrics.copy(),
            "task_performance": [m for m in self.task_metrics
                               if self._task_matches_filters(m, task_id, agent_id, start_time, end_time)],
            "consensus_performance": self.consensus_metrics.copy() if hasattr(self, 'consensus_metrics') else []
        }
        report["performance_metrics"] = performance_data

        # Generate reasoning flow visualization data
        report["reasoning_flow"] = self._generate_reasoning_flow_data(reasoning_traces)

        return report

    def _trace_matches_filters(self, trace: Dict[str, Any], agent_id: str = None,
                             start_time: float = None, end_time: float = None) -> bool:
        """Check if reasoning trace matches filter criteria"""
        if agent_id and trace.get("agent_id") != agent_id:
            return False
        if start_time and trace.get("timestamp", 0) < start_time:
            return False
        if end_time and trace.get("timestamp", 0) > end_time:
            return False
        return True

    def _failure_matches_filters(self, failure: Dict[str, Any], task_id: str = None, agent_id: str = None,
                               start_time: float = None, end_time: float = None) -> bool:
        """Check if failure matches filter criteria"""
        if task_id and failure.get("task_id") != task_id:
            return False
        if agent_id and failure.get("agent_id") != agent_id:
            return False
        if start_time and failure.get("timestamp", 0) < start_time:
            return False
        if end_time and failure.get("timestamp", 0) > end_time:
            return False
        return True

    def _task_matches_filters(self, task_metric: Dict[str, Any], task_id: str = None, agent_id: str = None,
                            start_time: float = None, end_time: float = None) -> bool:
        """Check if task metric matches filter criteria"""
        if task_id and task_metric.get("task_id") != task_id:
            return False
        if start_time and task_metric.get("timestamp", 0) < start_time:
            return False
        if end_time and task_metric.get("timestamp", 0) > end_time:
            return False
        return True

    def _generate_reasoning_flow_data(self, reasoning_traces: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate data for reasoning flow visualization"""
        flow_data = {
            "nodes": [],
            "edges": [],
            "decision_points": [],
            "confidence_distribution": []
        }

        for trace in reasoning_traces:
            agent_id = trace["agent_id"]
            task_id = trace["task_id"]

            # Add agent node
            if not any(n["id"] == agent_id for n in flow_data["nodes"]):
                flow_data["nodes"].append({
                    "id": agent_id,
                    "type": "agent",
                    "label": agent_id,
                    "confidence": trace.get("confidence", 0)
                })

            # Add task node
            if not any(n["id"] == task_id for n in flow_data["nodes"]):
                flow_data["nodes"].append({
                    "id": task_id,
                    "type": "task",
                    "label": f"Task: {task_id[:20]}..."
                })

            # Add reasoning steps as nodes
            for i, step in enumerate(trace.get("reasoning_steps", [])):
                step_id = f"{task_id}_step_{i}"
                flow_data["nodes"].append({
                    "id": step_id,
                    "type": "reasoning_step",
                    "label": step.get("description", "Unknown")[:50],
                    "step_number": i + 1
                })

                # Connect to previous step or agent
                if i == 0:
                    flow_data["edges"].append({
                        "from": agent_id,
                        "to": step_id,
                        "type": "initiated"
                    })
                else:
                    prev_step_id = f"{task_id}_step_{i-1}"
                    flow_data["edges"].append({
                        "from": prev_step_id,
                        "to": step_id,
                        "type": "reasoned_to"
                    })

            # Connect final step to task outcome
            if trace.get("reasoning_steps"):
                final_step_id = f"{task_id}_step_{len(trace['reasoning_steps'])-1}"
                flow_data["edges"].append({
                    "from": final_step_id,
                    "to": task_id,
                    "type": "produced_result",
                    "result": trace.get("final_decision", "Unknown")
                })

            # Track confidence distribution
            flow_data["confidence_distribution"].append({
                "agent": agent_id,
                "task": task_id,
                "confidence": trace.get("confidence", 0),
                "step_count": trace.get("step_count", 0)
            })

        return flow_data

    def get_performance_report(self) -> str:
        """Generate comprehensive text-based performance dashboard"""
        report = "=== Brain Swarm Executive Performance Dashboard ===\n"
        report += f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # System Overview
        total_agents = len(self.agent_metrics)
        total_tasks = sum(m["total_tasks"] for m in self.agent_metrics.values())
        overall_success = sum(m["successful_tasks"] for m in self.agent_metrics.values()) / total_tasks * 100 if total_tasks > 0 else 0

        report += "SYSTEM OVERVIEW:\n"
        report += f"  Total Agents: {total_agents}\n"
        report += f"  Total Tasks Processed: {total_tasks}\n"
        report += f"  Overall Success Rate: {overall_success:.1f}%\n"
        report += f"  Active Consensus Sessions: {len(self.consensus_metrics)}\n\n"

        # Agent Performance with Rankings
        report += "AGENT PERFORMANCE RANKINGS:\n"
        agent_rankings = []
        for agent_id, metrics in self.agent_metrics.items():
            success_rate = (metrics["successful_tasks"] / metrics["total_tasks"]) * 100 if metrics["total_tasks"] > 0 else 0
            avg_time = metrics["total_execution_time"] / metrics["total_tasks"] if metrics["total_tasks"] > 0 else 0
            efficiency_score = success_rate / (avg_time + 1)  # Simple efficiency metric
            agent_rankings.append((agent_id, success_rate, avg_time, efficiency_score, metrics))

        agent_rankings.sort(key=lambda x: x[3], reverse=True)  # Sort by efficiency

        for rank, (agent_id, success_rate, avg_time, efficiency, metrics) in enumerate(agent_rankings, 1):
            report += f"  #{rank} {agent_id}:\n"
            report += f"    Success Rate: {success_rate:.1f}% | Avg Time: {avg_time:.2f}s | Efficiency: {efficiency:.2f}\n"
            report += f"    Quality Score: {metrics['avg_quality']:.2f} | Tasks: {metrics['total_tasks']}\n"

        # Reasoning Performance Analysis
        report += "\nREASONING PERFORMANCE ANALYSIS:\n"
        for reasoning_type, metrics in self.reasoning_metrics.items():
            success_rate = (metrics["successful_runs"] / metrics["total_runs"]) * 100 if metrics["total_runs"] > 0 else 0
            avg_steps = metrics["total_steps"] / metrics["total_runs"] if metrics["total_runs"] > 0 else 0
            avg_time = metrics["total_time"] / metrics["total_runs"] if metrics["total_runs"] > 0 else 0

            # Performance indicators
            perf_indicator = "🟢" if success_rate > 80 else "🟡" if success_rate > 60 else "🔴"

            report += f"  {perf_indicator} {reasoning_type}:\n"
            report += f"    Success: {success_rate:.1f}% | Avg Steps: {avg_steps:.1f} | Avg Time: {avg_time:.2f}s\n"
            report += f"    Total Runs: {metrics['total_runs']} | Efficiency: {success_rate/avg_time:.2f} success/sec\n"

        # Consensus Quality Analysis
        report += "\nCONSENSUS QUALITY ANALYSIS:\n"
        if self.consensus_metrics:
            avg_consensus_score = sum(c["consensus_score"] for c in self.consensus_metrics) / len(self.consensus_metrics)
            avg_participants = sum(c["participants"] for c in self.consensus_metrics) / len(self.consensus_metrics)
            avg_consensus_time = sum(c["execution_time"] for c in self.consensus_metrics) / len(self.consensus_metrics)

            report += f"  Average Consensus Score: {avg_consensus_score:.2f}/1.0\n"
            report += f"  Average Participants: {avg_participants:.1f}\n"
            report += f"  Average Decision Time: {avg_consensus_time:.2f}s\n"

            # Recent consensus trends
            recent_scores = [c["consensus_score"] for c in self.consensus_metrics[-10:]]
            if len(recent_scores) > 1:
                trend = "↗️ Improving" if recent_scores[-1] > recent_scores[0] else "↘️ Declining" if recent_scores[-1] < recent_scores[0] else "➡️ Stable"
                report += f"  Recent Trend: {trend}\n"

        # Task Performance Summary
        report += "\nTASK PERFORMANCE SUMMARY:\n"
        if self.task_metrics:
            recent_tasks = self.task_metrics[-5:]  # Last 5 tasks
            avg_task_time = sum(t["total_time"] for t in recent_tasks) / len(recent_tasks)
            avg_task_success = sum(t["success_rate"] for t in recent_tasks) / len(recent_tasks) * 100
            avg_task_quality = sum(t["final_quality"] for t in recent_tasks) / len(recent_tasks)

            report += f"  Recent Tasks (last 5): Avg Time: {avg_task_time:.2f}s\n"
            report += f"  Subtask Success Rate: {avg_task_success:.1f}% | Quality: {avg_task_quality:.2f}\n"

        # Scoring Feedback & Recommendations
        report += "\nSCORING SYSTEM FEEDBACK:\n"
        if self.scoring_feedback:
            avg_error = sum(f["error"] for f in self.scoring_feedback) / len(self.scoring_feedback)
            report += f"  Average Scoring Error: {avg_error:.3f}\n"

            # Show recommended adjustments
            task_types = set(f["task_type"] for f in self.scoring_feedback)
            for task_type in task_types:
                adjustments = self.get_scoring_adjustments(task_type)
                if adjustments:
                    report += f"  {task_type} Adjustments: {adjustments}\n"

        # Performance Alerts
        report += "\nPERFORMANCE ALERTS:\n"
        alerts = []

        # Check for underperforming agents
        for agent_id, metrics in self.agent_metrics.items():
            success_rate = (metrics["successful_tasks"] / metrics["total_tasks"]) * 100 if metrics["total_tasks"] > 0 else 0
            if success_rate < 50 and metrics["total_tasks"] > 3:
                alerts.append(f"⚠️  {agent_id} success rate below 50%")

        # Check for slow consensus
        if self.consensus_metrics:
            slow_consensus = [c for c in self.consensus_metrics if c["execution_time"] > 10.0]
            if len(slow_consensus) > len(self.consensus_metrics) * 0.3:
                alerts.append("⚠️  Consensus decisions taking too long (>30% over 10s)")

        if not alerts:
            alerts.append("✅ All systems performing within acceptable parameters")

        for alert in alerts:
            report += f"  {alert}\n"

        return report

    def log_failure(self, failure_data: Dict[str, Any]):
        """Log task failure for learning and improvement"""
        if not hasattr(self, 'failure_logs'):
            self.failure_logs = []

        self.failure_logs.append(failure_data)

        # Keep only recent failures for analysis
        if len(self.failure_logs) > 100:
            self.failure_logs.pop(0)

        # Trigger improvement analysis if we have enough data
        if len(self.failure_logs) >= 10:
            self._analyze_failure_patterns()

    def _analyze_failure_patterns(self):
        """Analyze failure patterns and generate improvement recommendations"""
        if len(self.failure_logs) < 5:
            return

        # Analyze failure patterns
        error_types = {}
        task_types = {}
        agent_roles = {}

        for failure in self.failure_logs[-50:]:  # Analyze last 50 failures
            error_types[failure["error_type"]] = error_types.get(failure["error_type"], 0) + 1
            task_types[failure["task_type"]] = task_types.get(failure["task_type"], 0) + 1
            agent_roles[failure["agent_role"]] = agent_roles.get(failure["agent_role"], 0) + 1

        # Generate improvement recommendations
        recommendations = []

        # Most common error types
        if error_types:
            most_common_error = max(error_types.items(), key=lambda x: x[1])
            if most_common_error[1] > len(self.failure_logs) * 0.2:  # >20% of failures
                recommendations.append(f"Address frequent {most_common_error[0]} errors")

        # Task types with high failure rates
        if task_types:
            for task_type, count in task_types.items():
                if count > 5:  # More than 5 failures for this task type
                    recommendations.append(f"Improve {task_type} task handling")

        # Agent roles with issues
        if agent_roles:
            for role, count in agent_roles.items():
                if count > 3:  # More than 3 failures for this role
                    recommendations.append(f"Enhance {role} agent capabilities")

        if recommendations:
            logger.log("INFO", "MetricsTracker", f"Generated {len(recommendations)} improvement recommendations",
                       {"recommendations": recommendations})

# Global metrics tracker
metrics = MetricsTracker()