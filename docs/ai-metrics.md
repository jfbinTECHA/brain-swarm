# AI Metrics for Brain Swarm

This document describes the AI-specific metrics that should be exposed by Brain Swarm components for monitoring and insights.

## Metrics Overview

All AI metrics should follow Prometheus naming conventions and include appropriate labels for filtering and aggregation.

## Required AI Metrics

### AI Confidence Scores

**ai_confidence_score** (Histogram)
- **Type**: Histogram
- **Description**: Distribution of AI confidence scores for predictions/decisions
- **Labels**:
  - `service`: The service/component name (e.g., "cortex", "triage")
  - `model`: The AI model name/version
  - `operation`: The operation type (e.g., "classification", "triage")
- **Buckets**: [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
- **Example**:
```python
from prometheus_client import Histogram

ai_confidence = Histogram(
    'ai_confidence_score',
    'AI confidence score distribution',
    ['service', 'model', 'operation'],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# Usage
ai_confidence.labels('cortex', 'gpt-4', 'incident_analysis').observe(0.85)
```

### Triage Success Rates

**ai_triage_total** (Counter)
- **Type**: Counter
- **Description**: Total number of triage operations performed
- **Labels**:
  - `category`: Incident category (e.g., "security", "performance", "error")
  - `outcome`: Triage outcome ("success", "failure", "escalated")
- **Example**:
```python
from prometheus_client import Counter

triage_total = Counter(
    'ai_triage_total',
    'Total triage operations',
    ['category', 'outcome']
)

triage_total.labels('security', 'success').inc()
```

**ai_triage_success_total** (Counter)
- **Type**: Counter
- **Description**: Number of successful triage operations
- **Labels**: Same as `ai_triage_total`
- **Note**: This is a subset of `ai_triage_total` where outcome="success"

### AI Processing Latency

**ai_processing_duration_seconds** (Histogram)
- **Type**: Histogram
- **Description**: Time taken for AI processing operations
- **Labels**:
  - `operation`: The operation type
  - `model`: The AI model used
- **Buckets**: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
- **Example**:
```python
from prometheus_client import Histogram

processing_duration = Histogram(
    'ai_processing_duration_seconds',
    'AI processing duration',
    ['operation', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# Usage
with processing_duration.labels('incident_analysis', 'gpt-4').time():
    # AI processing code here
    pass
```

### AI Model Performance

**ai_model_accuracy** (Gauge)
- **Type**: Gauge
- **Description**: Current accuracy of AI models
- **Labels**:
  - `model`: Model name/version
  - `dataset`: Dataset used for evaluation
- **Example**:
```python
from prometheus_client import Gauge

model_accuracy = Gauge(
    'ai_model_accuracy',
    'AI model accuracy',
    ['model', 'dataset']
)

model_accuracy.labels('gpt-4', 'incident_data').set(0.92)
```

### AI Decision Confidence

**ai_decision_confidence** (Gauge)
- **Type**: Gauge
- **Description**: Confidence level of AI decisions
- **Labels**:
  - `decision_type`: Type of decision (e.g., "priority", "category", "escalation")
  - `confidence_level`: High/Medium/Low
- **Example**:
```python
from prometheus_client import Gauge

decision_confidence = Gauge(
    'ai_decision_confidence',
    'AI decision confidence',
    ['decision_type', 'confidence_level']
)

decision_confidence.labels('priority', 'high').set(0.88)
```

### AI Feedback Loop

**ai_feedback_total** (Counter)
- **Type**: Counter
- **Description**: Total feedback received on AI decisions
- **Labels**:
  - `feedback_type`: "positive", "negative", "neutral"

**ai_feedback_positive_total** (Counter)
- **Type**: Counter
- **Description**: Positive feedback on AI decisions

### AI Model Drift Detection

**ai_model_drift_score** (Gauge)
- **Type**: Gauge
- **Description**: Model drift detection score (0.0 = no drift, 1.0 = high drift)
- **Labels**:
  - `model`: Model name
  - `metric`: Drift metric type

### AI Resource Usage

**ai_tokens_used_total** (Counter)
- **Type**: Counter
- **Description**: Total AI API tokens consumed
- **Labels**:
  - `model`: AI model used
  - `operation`: Operation type

**ai_api_calls_per_second** (Gauge)
- **Type**: Gauge
- **Description**: Current AI API calls per second
- **Labels**:
  - `provider`: AI provider (e.g., "openai", "anthropic")

## Implementation Guidelines

### Python Implementation

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from flask import Flask, Response

app = Flask(__name__)

# Define metrics
ai_confidence = Histogram('ai_confidence_score', 'AI confidence score', ['service'])
triage_total = Counter('ai_triage_total', 'Triage operations', ['outcome'])

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype='text/plain')

# Usage in AI processing
def process_incident(incident_data):
    confidence = ai_model.predict_confidence(incident_data)
    ai_confidence.labels('incident_processor').observe(confidence)

    success = ai_model.triage_incident(incident_data)
    outcome = 'success' if success else 'failure'
    triage_total.labels(outcome).inc()

    return success
```

### Go Implementation

```go
package main

import (
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
    aiConfidence = prometheus.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "ai_confidence_score",
            Help:    "AI confidence score distribution",
            Buckets: prometheus.DefBuckets,
        },
        []string{"service"},
    )

    triageTotal = prometheus.NewCounterVec(
        prometheus.CounterOpts{
            Name: "ai_triage_total",
            Help: "Total triage operations",
        },
        []string{"outcome"},
    )
)

func init() {
    prometheus.MustRegister(aiConfidence, triageTotal)
}

// Usage
func processIncident(data map[string]interface{}) bool {
    confidence := aiModel.PredictConfidence(data)
    aiConfidence.WithLabelValues("incident_processor").Observe(confidence)

    success := aiModel.TriageIncident(data)
    outcome := "failure"
    if success {
        outcome = "success"
    }
    triageTotal.WithLabelValues(outcome).Inc()

    return success
}
```

## Dashboard Panels

The AI Insights Dashboard includes panels for:

1. **AI Confidence Score Distribution**: Histogram showing confidence score distributions
2. **Average AI Confidence Score**: Stat panel with thresholds
3. **Triage Success Rate Over Time**: Time series graph
4. **Triage Success Rate by Category**: Bar gauge by incident category
5. **AI Processing Latency**: Response time histograms
6. **AI Model Performance**: Table of model accuracies
7. **AI Decision Confidence Trend**: Time series of decision confidence
8. **AI Feedback Loop**: Positive feedback rate
9. **AI Model Drift Detection**: Drift score monitoring
10. **AI Resource Usage**: Token usage and API call rates

## Alerting Rules

Consider setting up alerts for:

- AI confidence scores dropping below threshold
- Triage success rate falling below acceptable levels
- AI processing latency exceeding limits
- Model drift detection triggering
- API rate limits approaching

## Best Practices

1. **Consistent Labeling**: Use consistent label names across all metrics
2. **Appropriate Buckets**: Choose histogram buckets based on expected value ranges
3. **Resource Monitoring**: Track AI API usage to manage costs
4. **Model Monitoring**: Monitor model performance and drift over time
5. **Feedback Integration**: Implement feedback loops to improve AI performance
6. **Version Tracking**: Include model versions in labels for performance comparison