
# Generic Metrics System Guide

## Overview

The elasmetrics project now includes a **flexible, generic metrics system** that allows you to collect **any metric from Elasticsearch** without modifying code. The system is:

✅ **Universal** - Works with any Elasticsearch version (7.x, 8.x, etc.)  
✅ **Type-Safe** - Built-in type validation and casting  
✅ **Extensible** - Add new metrics via configuration  
✅ **Adaptable** - Supports custom metrics per cluster  

## Architecture

### Core Components

1. **MetricDefinition** - Defines a metric with type safety
2. **GenericMetrics** - Dynamic container for metrics
3. **MetricRegistry** - Central registry of metric definitions
4. **GenericMetricsCollector** - Configuration-driven collector

### Type System

```python
class MetricType(Enum):
    STRING = "string"          # Text values
    INTEGER = "integer"        # Whole numbers
    FLOAT = "float"           # Decimal numbers
    BOOLEAN = "boolean"       # True/False
    TIMESTAMP = "timestamp"   # Date/time values
    JSON = "json"             # Complex nested data
```

## Quick Start

### 1. Using Pre-defined Metrics

The system comes with 17+ commonly used metrics pre-registered:

**config.yaml:**
```yaml
metrics:
  collect:
    - docs.count
    - docs.deleted
    - store.size_in_bytes
    - pri.store.size_in_bytes
    - indexing.index_total
    - search.query_total
    - segments.count
```

### 2. Adding Custom Metrics

Define custom metrics in your configuration without code changes:

**config.yaml:**
```yaml
metrics:
  # Which metrics to collect
  collect:
    - docs.count
    - store.size_in_bytes
    - my.custom.metric
    
  # Define custom metrics
  custom_definitions:
    - name: my.custom.metric
      es_path: primaries.my_plugin.custom_value
      type: integer
      description: Custom metric from my ES plugin
      unit: count
      aggregatable: true
```

### 3. Different Metrics Per Environment

**Staging - Collect basics:**
```yaml
# .env.staging or config-staging.yaml
metrics:
  collect:
    - docs.count
    - store.size_in_bytes
```

**Production - Collect everything:**
```yaml
# .env.production or config-production.yaml  
metrics:
  collect:
    - docs.count
    - store.size_in_bytes
    - indexing.index_total
    - indexing.index_time_in_millis
    - search.query_total
    - search.query_time_in_millis
    - merges.total
    - segments.count
    - segments.memory_in_bytes
    - translog.size_in_bytes
```

## Pre-registered Metrics

### Document Metrics

| Metric | ES Path | Type | Description |
|--------|---------|------|-------------|
| `docs.count` | `primaries.docs.count` | integer | Number of documents |
| `docs.deleted` | `primaries.docs.deleted` | integer | Deleted documents |

### Storage Metrics

| Metric | ES Path | Type | Description |
|--------|---------|------|-------------|
| `store.size_in_bytes` | `total.store.size_in_bytes` | integer | Total storage size |
| `pri.store.size_in_bytes` | `primaries.store.size_in_bytes` | integer | Primary shards size |

### Indexing Metrics

| Metric | ES Path | Type | Description |
|--------|---------|------|-------------|
| `indexing.index_total` | `primaries.indexing.index_total` | integer | Total index operations |
| `indexing.index_time_in_millis` | `primaries.indexing.index_time_in_millis` | integer | Time spent indexing |

### Search Metrics

| Metric | ES Path | Type | Description |
|--------|---------|------|-------------|
| `search.query_total` | `primaries.search.query_total` | integer | Total search queries |
| `search.query_time_in_millis` | `primaries.search.query_time_in_millis` | integer | Time spent on queries |

### Segment Metrics

| Metric | ES Path | Type | Description |
|--------|---------|------|-------------|
| `segments.count` | `primaries.segments.count` | integer | Number of segments |
| `segments.memory_in_bytes` | `primaries.segments.memory_in_bytes` | integer | Segment memory usage |

### Merge Metrics

| Metric | ES Path | Type | Description |
|--------|---------|------|-------------|
| `merges.total` | `primaries.merges.total` | integer | Total merge operations |
| `merges.total_time_in_millis` | `primaries.merges.total_time_in_millis` | integer | Time spent merging |

### Cache Metrics

| Metric | ES Path | Type | Description |
|--------|---------|------|-------------|
| `request_cache.memory_size_in_bytes` | `total.request_cache.memory_size_in_bytes` | integer | Request cache memory |
| `fielddata.memory_size_in_bytes` | `total.fielddata.memory_size_in_bytes` | integer | Field data memory |
| `query_cache.memory_size_in_bytes` | `total.query_cache.memory_size_in_bytes` | integer | Query cache memory |

### Other Metrics

| Metric | ES Path | Type | Description |
|--------|---------|------|-------------|
| `refresh.total` | `primaries.refresh.total` | integer | Total refresh operations |
| `flush.total` | `primaries.flush.total` | integer | Total flush operations |
| `translog.size_in_bytes` | `primaries.translog.size_in_bytes` | integer | Transaction log size |

## Advanced Usage

### 1. Custom Metric Definition

```yaml
metrics:
  custom_definitions:
    # Performance metric
    - name: query.avg_time_per_query
      es_path: primaries.search.query_time_in_millis
      type: float
      description: Average time per query
      unit: milliseconds
      aggregatable: true
    
    # Plugin metric
    - name: anomaly_detection.score
      es_path: primaries.anomaly_detection.score
      type: float
      description: Anomaly detection score from ML plugin
      unit: score
      aggregatable: true
    
    # Boolean metric
    - name: index.frozen
      es_path: settings.index.frozen
      type: boolean
      description: Is index frozen
      aggregatable: false
```

### 2. Collecting Metrics from Custom Plugins

If you have custom Elasticsearch plugins that expose metrics:

```yaml
metrics:
  collect:
    - my_plugin.request_count
    - my_plugin.avg_response_time
    
  custom_definitions:
    - name: my_plugin.request_count
      es_path: primaries.my_plugin.requests.total
      type: integer
      description: Total requests processed by my plugin
      unit: count
      
    - name: my_plugin.avg_response_time
      es_path: primaries.my_plugin.avg_response_ms
      type: float
      description: Average response time
      unit: milliseconds
```

### 3. Version-Specific Metrics

Different ES versions have different metrics. Configure per version:

**For ES 7.x:**
```yaml
metrics:
  collect:
    - docs.count
    - store.size_in_bytes
    # ES 7.x specific metrics
```

**For ES 8.x:**
```yaml
metrics:
  collect:
    - docs.count
    - store.size_in_bytes
    # ES 8.x specific metrics
    - new_metric_in_8
```

### 4. Cluster-Specific Metrics

Different clusters may have different needs:

**Log Cluster (high ingestion):**
```yaml
metrics:
  collect:
    - docs.count
    - indexing.index_total
    - indexing.index_time_in_millis
    - merges.total
    - segments.count
```

**Search Cluster (high queries):**
```yaml
metrics:
  collect:
    - docs.count
    - search.query_total
    - search.query_time_in_millis
    - query_cache.memory_size_in_bytes
    - request_cache.memory_size_in_bytes
```

## Database Storage

### Option 1: JSON Storage (Recommended)

Store metrics as JSON for maximum flexibility:

```sql
CREATE TABLE generic_metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    index_name VARCHAR(255) NOT NULL,
    timestamp DATETIME NOT NULL,
    metrics_json JSON NOT NULL,
    metadata_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_index_name (index_name),
    INDEX idx_timestamp (timestamp)
);
```

**Benefits:**
- No schema changes needed for new metrics
- Query JSON fields: `JSON_EXTRACT(metrics_json, '$.docs.count')`
- Supports any metric without ALTER TABLE

### Option 2: Hybrid Storage

Core metrics in columns, others in JSON:

```sql
CREATE TABLE hybrid_metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    index_name VARCHAR(255) NOT NULL,
    timestamp DATETIME NOT NULL,
    
    -- Core metrics (frequently queried)
    docs_count BIGINT,
    store_size_bytes BIGINT,
    
    -- Additional metrics as JSON
    additional_metrics JSON,
    metadata JSON,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_index_name (index_name),
    INDEX idx_timestamp (timestamp)
);
```

### Option 3: Key-Value Storage

Ultimate flexibility:

```sql
CREATE TABLE metric_values (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    index_name VARCHAR(255) NOT NULL,
    timestamp DATETIME NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    metric_value TEXT,
    metric_type ENUM('string', 'integer', 'float', 'boolean', 'timestamp', 'json'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_index_timestamp (index_name, timestamp),
    INDEX idx_metric_name (metric_name)
);
```

## Programmatic Usage

### Registering Custom Metrics

```python
from src.models.generic_metrics import (
    MetricRegistry,
    MetricDefinition,
    MetricType,
    get_metric_registry
)

# Get global registry
registry = get_metric_registry()

# Register custom metric
registry.register(MetricDefinition(
    name="my.custom.metric",
    es_path="primaries.custom.value",
    metric_type=MetricType.INTEGER,
    description="My custom metric",
    unit="count"
))
```

### Collecting Metrics

```python
from src.collectors.generic_collector import GenericMetricsCollector
from elasticsearch import Elasticsearch

# Create ES client
es = Elasticsearch(['http://localhost:9200'])

# Configure collector
config = {
    'metrics': {
        'collect': [
            'docs.count',
            'store.size_in_bytes',
            'search.query_total'
        ],
        'include_patterns': ['*'],
        'exclude_patterns': ['.security*'],
        'batch_size': 100
    }
}

# Collect metrics
collector = GenericMetricsCollector(es, config)
metrics_list = collector.collect()

# Use metrics
for metrics in metrics_list:
    print(f"Index: {metrics.index_name}")
    print(f"Docs: {metrics.get_metric('docs.count')}")
    print(f"Size: {metrics.get_metric('store.size_in_bytes')}")
```

### Accessing Metrics

```python
from src.models.generic_metrics import GenericMetrics

# Create metrics object
metrics = GenericMetrics(index_name="my-index-2024")

# Add metrics
metrics.add_metric("docs.count", 1000000)
metrics.add_metric("store.size_in_bytes", 5368709120)

# Add metadata
metrics.add_metadata("health", "green")
metrics.add_metadata("status", "open")

# Export formats
dict_data = metrics.to_dict()          # Full dictionary
db_data = metrics.to_db_dict()         # For database insert (JSON fields)
flat_data = metrics.to_flat_dict()     # Flat structure for CSV

# Access metrics
doc_count = metrics.get_metric("docs.count")
size = metrics.get_metric("store.size_in_bytes", default=0)
```

## Migration from Fixed Schema

### Step 1: Add Generic Collector

Update your service to use the generic collector:

```python
# Old way
from src.collectors import IndexStatsCollector

# New way (both work)
from src.collectors import GenericMetricsCollector

# Use generic collector
collector = GenericMetricsCollector(es_client, config)
```

### Step 2: Update Configuration

Migrate your metrics configuration:

```yaml
# Old format (still works)
metrics:
  index_stats:
    - docs.count
    - store.size_in_bytes

# New format (more flexible)
metrics:
  collect:
    - docs.count
    - store.size_in_bytes
    - indexing.index_total
    - search.query_total
```

### Step 3: Update Database (Optional)

Create new table with JSON storage or add JSON columns to existing table.

## Best Practices

### 1. Start with Core Metrics

Don't collect everything at once:

```yaml
# Good: Start simple
metrics:
  collect:
    - docs.count
    - store.size_in_bytes
    - search.query_total
```

### 2. Add Metrics Incrementally

Add metrics as you need them:

```yaml
# Week 1: Basic metrics
metrics:
  collect:
    - docs.count
    - store.size_in_bytes

# Week 2: Add performance metrics
metrics:
  collect:
    - docs.count
    - store.size_in_bytes
    - search.query_total
    - indexing.index_total

# Week 3: Add memory metrics
metrics:
  collect:
    - docs.count
    - store.size_in_bytes
    - search.query_total
    - indexing.index_total
    - segments.memory_in_bytes
    - fielddata.memory_size_in_bytes
```

### 3. Document Custom Metrics

Always document your custom metrics:

```yaml
metrics:
  custom_definitions:
    - name: business.order_count
      es_path: primaries.business_metrics.orders
      type: integer
      description: |
        Number of orders indexed in this index.
        Used by billing team for revenue tracking.
        Added: 2026-01-13
        Owner: data-team@company.com
      unit: count
```

### 4. Use Type Safety

Always specify the correct type:

```yaml
# Good
- name: docs.count
  type: integer

# Bad - will be stored as string
- name: docs.count
  type: string
```

### 5. Consider Query Patterns

Collect metrics you'll actually query:

```yaml
# If you do: SELECT AVG(query_time) FROM metrics
# Then collect:
metrics:
  collect:
    - search.query_time_in_millis
```

## Troubleshooting

### Metric Not Collected

**Issue:** Metric defined but not showing up in results.

**Solution:**
1. Check metric name matches configuration
2. Verify ES path is correct for your ES version
3. Check ES actually has this metric: `GET /my-index/_stats`
4. Check logs for validation errors

### Type Mismatch

**Issue:** "Value does not match type" error.

**Solution:**
```yaml
# Check your metric type matches ES data
- name: docs.count
  type: integer  # Make sure ES returns integer, not string
```

### Performance Issues

**Issue:** Collection is slow.

**Solution:**
- Reduce number of metrics collected
- Increase batch size
- Use _cat API for simple metrics instead of _stats API

### Unknown Metric Path

**Issue:** Don't know the ES path for a metric.

**Solution:**
```bash
# Check ES response structure
curl -X GET "localhost:9200/my-index/_stats?pretty"

# Find your metric in the response, note the path
# Example: response.indices.my-index.primaries.docs.count
# Path would be: primaries.docs.count
```

## Summary

✅ **Universal**: Works with any ES version, any cluster  
✅ **Type-Safe**: Built-in validation and type casting  
✅ **Configuration-Driven**: No code changes for new metrics  
✅ **Flexible Storage**: JSON, hybrid, or key-value  
✅ **Extensible**: Easy to add custom metrics  
✅ **Backward Compatible**: Works alongside existing code  

The generic metrics system makes elasmetrics adaptable to any Elasticsearch monitoring need without code changes!

