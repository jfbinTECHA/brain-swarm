import pytest
import time
from unittest.mock import Mock, patch
from brain_swarm.coordination.coordinator import RetryManager


class TestRetryManager:
    """Test suite for RetryManager edge cases and queue handling"""

    def setup_method(self):
        """Set up test fixtures"""
        self.retry_manager = RetryManager()

    def test_initialization(self):
        """Test RetryManager initializes with correct defaults"""
        assert self.retry_manager.max_retries == 3
        assert self.retry_manager.base_delay == 2.0
        assert self.retry_manager.max_delay == 300.0
        assert self.retry_manager.jitter_range == 0.25
        assert len(self.retry_manager.retry_history) == 0
        assert len(self.retry_manager.circuit_breakers) == 0

    def test_successful_task_no_retry(self):
        """Test that successful tasks don't trigger retries"""
        task_id = "task_123"
        agent_id = "agent_1"

        # Simulate successful task
        result = self.retry_manager.handle_task_result(task_id, agent_id, "success", None)

        assert result is None  # No retry needed
        assert task_id not in self.retry_manager.retry_history

    def test_failed_task_triggers_retry(self):
        """Test that failed tasks trigger retry logic"""
        task_id = "task_123"
        agent_id = "agent_1"
        error = Exception("Task failed")

        with patch.object(self.retry_manager, '_find_alternative_agent') as mock_find_agent:
            mock_find_agent.return_value = "agent_2"

            result = self.retry_manager.handle_task_result(task_id, agent_id, "failed", error)

            assert result is not None
            assert result['action'] == 'retry'
            assert result['task_id'] == task_id
            assert result['retry_count'] == 1
            assert 'delay' in result
            assert task_id in self.retry_manager.retry_history

    def test_max_retries_exceeded(self):
        """Test that tasks exceeding max retries are not retried further"""
        task_id = "task_123"
        agent_id = "agent_1"
        error = Exception("Persistent failure")

        # Simulate max retries exceeded
        self.retry_manager.retry_history[task_id] = {
            'retry_count': self.retry_manager.max_retries,
            'last_retry_time': time.time(),
            'agents_tried': ['agent_1', 'agent_2', 'agent_3']
        }

        result = self.retry_manager.handle_task_result(task_id, agent_id, "failed", error)

        assert result is None  # No more retries

    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after consecutive failures"""
        agent_id = "agent_1"

        # Simulate consecutive failures
        for i in range(self.retry_manager.circuit_breaker_threshold + 1):
            task_id = f"task_{i}"
            self.retry_manager.handle_task_result(task_id, agent_id, "failed", Exception("Failure"))

        # Check circuit breaker opened
        assert agent_id in self.retry_manager.circuit_breakers
        assert self.retry_manager.circuit_breakers[agent_id]['state'] == 'open'

    def test_circuit_breaker_half_open_after_timeout(self):
        """Test circuit breaker transitions to half-open after timeout"""
        agent_id = "agent_1"

        # Open circuit breaker
        self.retry_manager.circuit_breakers[agent_id] = {
            'state': 'open',
            'failure_count': 5,
            'last_failure_time': time.time() - (self.retry_manager.circuit_breaker_timeout + 1),
            'next_attempt_time': time.time() - 1
        }

        # Check if circuit breaker should transition
        should_retry = self.retry_manager._should_retry_with_agent(agent_id)
        assert should_retry is True  # Should allow retry in half-open state

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation"""
        # First retry
        delay1 = self.retry_manager._calculate_delay(1)
        expected_min1 = 2.0 * (2 ** 0) * (1 - 0.25)  # 2^0 = 1
        expected_max1 = 2.0 * (2 ** 0) * (1 + 0.25)  # 2^0 = 1
        assert expected_min1 <= delay1 <= expected_max1

        # Second retry
        delay2 = self.retry_manager._calculate_delay(2)
        expected_min2 = 2.0 * (2 ** 1) * (1 - 0.25)  # 2^1 = 2
        expected_max2 = 2.0 * (2 ** 1) * (1 + 0.25)  # 2^1 = 2
        assert expected_min2 <= delay2 <= expected_max2

        # Verify delay increases
        assert delay2 > delay1

    def test_max_delay_cap(self):
        """Test that delays are capped at max_delay"""
        # High retry count should still be capped
        delay = self.retry_manager._calculate_delay(10)  # Very high retry count
        assert delay <= self.retry_manager.max_delay

    def test_agent_rotation_logic(self):
        """Test that failed agents are avoided in rotation"""
        task_id = "task_123"
        failed_agent = "agent_1"
        available_agents = ["agent_1", "agent_2", "agent_3"]

        # Mark agent_1 as failed recently
        self.retry_manager.retry_history[task_id] = {
            'retry_count': 1,
            'agents_tried': [failed_agent],
            'last_retry_time': time.time()
        }

        # Find alternative agent
        alternative = self.retry_manager._find_alternative_agent(task_id, failed_agent, available_agents)

        assert alternative != failed_agent
        assert alternative in available_agents

    def test_all_agents_exhausted(self):
        """Test behavior when all agents have been tried"""
        task_id = "task_123"
        available_agents = ["agent_1", "agent_2"]

        # Mark all agents as tried
        self.retry_manager.retry_history[task_id] = {
            'retry_count': 2,
            'agents_tried': available_agents.copy(),
            'last_retry_time': time.time()
        }

        # Try to find alternative when all exhausted
        alternative = self.retry_manager._find_alternative_agent(task_id, "agent_1", available_agents)

        # Should still return an agent (could be the same one after sufficient time)
        assert alternative in available_agents

    def test_retry_success_resets_circuit_breaker(self):
        """Test that successful retry resets circuit breaker failure count"""
        agent_id = "agent_1"
        task_id = "task_123"

        # Set up circuit breaker with failures
        self.retry_manager.circuit_breakers[agent_id] = {
            'state': 'half_open',
            'failure_count': 2,
            'last_failure_time': time.time()
        }

        # Simulate successful retry
        self.retry_manager.handle_task_result(task_id, agent_id, "success", None)

        # Circuit breaker should be reset or have reduced failure count
        cb_state = self.retry_manager.circuit_breakers.get(agent_id)
        if cb_state:
            assert cb_state['failure_count'] < 3  # Should be reduced

    def test_concurrent_retry_requests(self):
        """Test handling of concurrent retry requests for same task"""
        task_id = "task_123"
        agent_id = "agent_1"

        # Simulate concurrent retry requests
        results = []
        for i in range(3):
            result = self.retry_manager.handle_task_result(task_id, agent_id, "failed", Exception("Concurrent failure"))
            results.append(result)

        # All should return retry results, but with increasing retry counts
        retry_counts = [r['retry_count'] for r in results if r is not None]
        assert len(set(retry_counts)) == len(retry_counts)  # All retry counts should be unique

    def test_memory_cleanup_old_entries(self):
        """Test that old retry history entries are cleaned up"""
        old_time = time.time() - (self.retry_manager.history_cleanup_days * 24 * 3600 + 1)

        # Add old entries
        for i in range(5):
            task_id = f"old_task_{i}"
            self.retry_manager.retry_history[task_id] = {
                'retry_count': 1,
                'last_retry_time': old_time,
                'agents_tried': ['agent_1']
            }

        # Add recent entry
        self.retry_manager.retry_history['recent_task'] = {
            'retry_count': 1,
            'last_retry_time': time.time(),
            'agents_tried': ['agent_1']
        }

        # Trigger cleanup
        self.retry_manager._cleanup_old_history()

        # Old entries should be removed, recent should remain
        assert 'recent_task' in self.retry_manager.retry_history
        assert len([k for k in self.retry_manager.retry_history.keys() if k.startswith('old_task_')]) < 5

    def test_zero_max_retries_configuration(self):
        """Test behavior with zero max retries (no retries allowed)"""
        retry_manager = RetryManager(max_retries=0)
        task_id = "task_123"
        agent_id = "agent_1"

        result = retry_manager.handle_task_result(task_id, agent_id, "failed", Exception("Failure"))

        assert result is None  # No retry should be attempted

    def test_empty_agent_list(self):
        """Test behavior when no alternative agents are available"""
        task_id = "task_123"
        agent_id = "agent_1"

        alternative = self.retry_manager._find_alternative_agent(task_id, agent_id, [])

        assert alternative is None

    def test_circuit_breaker_recovery_success(self):
        """Test circuit breaker recovery after successful attempts"""
        agent_id = "agent_1"

        # Open circuit breaker
        self.retry_manager.circuit_breakers[agent_id] = {
            'state': 'open',
            'failure_count': 5,
            'last_failure_time': time.time()
        }

        # Simulate successful operations
        for i in range(self.retry_manager.circuit_breaker_recovery_threshold):
            task_id = f"recovery_task_{i}"
            self.retry_manager.handle_task_result(task_id, agent_id, "success", None)

        # Circuit breaker should be closed
        cb_state = self.retry_manager.circuit_breakers.get(agent_id)
        assert cb_state is None or cb_state['state'] == 'closed'

    def test_jitter_randomization(self):
        """Test that jitter introduces randomization in delays"""
        delays = []
        for i in range(10):
            delay = self.retry_manager._calculate_delay(1)  # Same retry count
            delays.append(delay)

        # Should have some variation due to jitter
        unique_delays = set(delays)
        assert len(unique_delays) > 1  # Should have variation

    def test_large_scale_retry_scenario(self):
        """Test retry manager under high load with many concurrent tasks"""
        num_tasks = 100
        num_agents = 10

        # Simulate high load scenario
        for task_num in range(num_tasks):
            task_id = f"task_{task_num}"
            agent_id = f"agent_{task_num % num_agents}"

            # Alternate between success and failure
            status = "success" if task_num % 3 == 0 else "failed"
            error = Exception("Load test failure") if status == "failed" else None

            result = self.retry_manager.handle_task_result(task_id, agent_id, status, error)

            if status == "failed":
                assert result is not None
                assert 'delay' in result

        # Check that circuit breakers opened for some agents
        open_breakers = [agent for agent, state in self.retry_manager.circuit_breakers.items()
                        if state['state'] == 'open']
        assert len(open_breakers) > 0  # Some agents should have open circuit breakers