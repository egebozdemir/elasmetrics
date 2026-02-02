# SR Usage Integration Plan: Multi-Cluster Aggregation Metrics

## Overview

This document describes the architecture and implementation for ElasMetrics multi-cluster and aggregation query support:
1. **Multiple ES/OpenSearch clusters** (direct VPC + DataHub proxy)
2. **Custom aggregation queries** on index data
3. **New database schema** for flexible metric storage
4. **AWS RDS MySQL** compatibility (already supported)

---

## Architecture Diagram

```
                                    ┌─────────────────────────────────────┐
                                    │           config.yaml               │
                                    │  ┌─────────────────────────────┐    │
                                    │  │ data_sources:               │    │
                                    │  │   main_cluster: ...         │    │
                                    │  │   enterprise_datahub: ...   │    │
                                    │  │ aggregation_queries: [...]  │    │
                                    │  └─────────────────────────────┘    │
                                    └──────────────┬──────────────────────┘
                                                   │
                                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              MetricsService                                   │
│                         (Facade - orchestrates all)                          │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                      DataSourceManager (NEW)                           │  │
│  │   ┌─────────────────┐              ┌─────────────────────────────┐     │  │
│  │   │  main_cluster   │              │   enterprise_datahub        │     │  │
│  │   │  ES Client      │              │   ES Client (DataHub host)  │     │  │
│  │   │  (VPC endpoint) │              │   (proxy endpoint)          │     │  │
│  │   └────────┬────────┘              └──────────────┬──────────────┘     │  │
│  └────────────┼──────────────────────────────────────┼────────────────────┘  │
│               │                                      │                        │
│               ▼                                      ▼                        │
│  ┌────────────────────────┐            ┌────────────────────────────┐        │
│  │  IndexStatsCollector   │            │   AggregationCollector     │        │
│  │  (existing, enhanced)  │            │   (NEW)                    │        │
│  │  - Uses any source     │            │   - Runs ES search queries │        │
│  │  - _cat/indices API    │            │   - Parses aggregations    │        │
│  └───────────┬────────────┘            └─────────────┬──────────────┘        │
│              │                                       │                        │
└──────────────┼───────────────────────────────────────┼────────────────────────┘
               │                                       │
               ▼                                       ▼
┌──────────────────────────┐            ┌────────────────────────────────┐
│   MySQLRepository        │            │   AggregationMetricsRepository │
│   (existing)             │            │   (NEW)                        │
│   index_metrics table    │            │   aggregation_metrics table    │
└──────────────────────────┘            └────────────────────────────────┘
               │                                       │
               └───────────────────┬───────────────────┘
                                   ▼
                        ┌─────────────────────┐
                        │   MySQL / AWS RDS   │
                        │                     │
                        │  - index_metrics    │
                        │  - aggregation_     │
                        │    metrics (NEW)    │
                        └─────────────────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │      Grafana        │
                        │   (dashboards)      │
                        └─────────────────────┘
```

---

## New Database Schema

### Table: `aggregation_metrics`

```sql
CREATE TABLE aggregation_metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Identification
    metric_name VARCHAR(255) NOT NULL,          -- e.g., 'daily_error_count', 'avg_response_time'
    data_source VARCHAR(100) NOT NULL,          -- e.g., 'main_cluster', 'enterprise_datahub'
    index_pattern VARCHAR(255),                 -- e.g., 'logs-*', 'api-requests-*'

    -- Time
    timestamp DATETIME NOT NULL,                -- When the metric was collected
    time_range_start DATETIME,                  -- Query time range start (for context)
    time_range_end DATETIME,                    -- Query time range end

    -- Values (flexible storage)
    value_numeric DOUBLE,                       -- Single numeric result (avg, sum, count)
    value_string VARCHAR(1000),                 -- String result if needed

    -- Dimensions (for grouping/filtering in Grafana)
    dimension_1_name VARCHAR(100),              -- e.g., 'status_code'
    dimension_1_value VARCHAR(255),             -- e.g., '500'
    dimension_2_name VARCHAR(100),              -- e.g., 'host'
    dimension_2_value VARCHAR(255),             -- e.g., 'api-server-1'
    dimension_3_name VARCHAR(100),              -- e.g., 'environment'
    dimension_3_value VARCHAR(255),             -- e.g., 'production'

    -- Complex results (for multi-bucket aggregations)
    result_json JSON,                           -- Full aggregation result if needed

    -- Metadata
    query_duration_ms INT,                      -- How long the ES query took
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes for Grafana queries
    INDEX idx_metric_name (metric_name),
    INDEX idx_data_source (data_source),
    INDEX idx_timestamp (timestamp),
    INDEX idx_metric_source_time (metric_name, data_source, timestamp),
    INDEX idx_dimension_1 (dimension_1_name, dimension_1_value),
    INDEX idx_dimension_2 (dimension_2_name, dimension_2_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### View: `aggregation_metrics_latest`

```sql
CREATE OR REPLACE VIEW aggregation_metrics_latest AS
SELECT am.*
FROM aggregation_metrics am
INNER JOIN (
    SELECT metric_name, data_source, MAX(timestamp) as max_timestamp
    FROM aggregation_metrics
    GROUP BY metric_name, data_source
) latest ON am.metric_name = latest.metric_name
          AND am.data_source = latest.data_source
          AND am.timestamp = latest.max_timestamp;
```

---

## Configuration Structure

### Enhanced `config/config.yaml`

```yaml
# =============================================================================
# DATA SOURCES - Define your ES/OpenSearch clusters
# =============================================================================
data_sources:
  # Main cluster - direct VPC access
  main_cluster:
    hosts:
      # SSM parameter syntax: ${ssm:/path/to/param}
      - "${ssm:/PREDICTIVE/PRODUCTION/ELASTICSEARCH/PRODUCT_FEED}"
    # Authentication options:
    # 1. Environment variables: ${VAR_NAME}
    # 2. AWS SSM Parameter Store: ${ssm:/path/to/param}
    username: "${ES_MAIN_USERNAME}"
    password: "${ssm:/PREDICTIVE/PRODUCTION/ELASTICSEARCH/PASSWORD}"
    timeout: 30
    verify_certs: true
    use_ssl: true

  # Enterprise cluster via DataHub proxy
  # URL pattern: https://{host}/v1/proxy/{index}/_search
  enterprise_datahub:
    hosts:
      - "https://datahub-api.yourcompany.com"
    # No auth required for DataHub
    timeout: 60
    verify_certs: true
    # Path prefix for proxy endpoints (transforms /{index}/_search to /v1/proxy/{index}/_search)
    path_prefix: "/v1/proxy"

  # Add more clusters as needed
  # analytics_cluster:
  #   hosts: [...]

# =============================================================================
# INDEX METRICS - Existing functionality (enhanced)
# =============================================================================
index_metrics:
  # Which data sources to collect index stats from
  sources:
    - main_cluster
    - enterprise_datahub

  # Patterns (applied per source)
  include_patterns:
    - "*"
  exclude_patterns:
    - ".kibana*"
    - ".security*"
    - ".opendistro*"

  batch_size: 100

# =============================================================================
# AGGREGATION QUERIES - Your custom metrics (NEW)
# =============================================================================
aggregation_queries:
  # ---------------------------------------------
  # Example 1: Count errors by status code
  # ---------------------------------------------
  - name: error_count_by_status
    description: "Count of HTTP errors (4xx, 5xx) by status code"
    data_source: main_cluster
    index_pattern: "logs-*"
    schedule: "daily"  # daily, hourly, or cron expression

    # Time range for the query (relative to execution time)
    time_range:
      gte: "now-1d"
      lte: "now"
      field: "@timestamp"

    # The ES query
    query:
      size: 0
      query:
        bool:
          filter:
            - range:
                "@timestamp":
                  gte: "now-1d"
            - range:
                status:
                  gte: 400
      aggs:
        by_status:
          terms:
            field: "status"
            size: 20

    # How to extract metrics from response
    result_mapping:
      type: "terms_buckets"           # terms_buckets, single_value, nested
      aggregation_path: "by_status"   # Path to aggregation in response
      dimension_field: "status_code"  # Name for the dimension
      value_field: "doc_count"        # Which value to extract

  # ---------------------------------------------
  # Example 2: Average response time
  # ---------------------------------------------
  - name: avg_response_time
    description: "Average API response time in milliseconds"
    data_source: main_cluster
    index_pattern: "api-requests-*"
    schedule: "hourly"

    time_range:
      gte: "now-1h"
      lte: "now"
      field: "@timestamp"

    query:
      size: 0
      aggs:
        avg_latency:
          avg:
            field: "response_time_ms"
        percentiles_latency:
          percentiles:
            field: "response_time_ms"
            percents: [50, 90, 95, 99]

    result_mapping:
      type: "single_value"
      metrics:
        - name: "avg_response_time_ms"
          path: "avg_latency.value"
        - name: "p50_response_time_ms"
          path: "percentiles_latency.values.50\\.0"
        - name: "p99_response_time_ms"
          path: "percentiles_latency.values.99\\.0"

  # ---------------------------------------------
  # Example 3: Enterprise cluster via DataHub
  # ---------------------------------------------
  - name: enterprise_daily_events
    description: "Daily event count from enterprise cluster"
    data_source: enterprise_datahub    # Uses DataHub proxy
    index_pattern: "enterprise-events-*"
    schedule: "daily"

    time_range:
      gte: "now-1d"
      lte: "now"
      field: "event_timestamp"

    query:
      size: 0
      aggs:
        total_events:
          value_count:
            field: "_id"
        by_event_type:
          terms:
            field: "event_type.keyword"
            size: 50

    result_mapping:
      type: "mixed"
      metrics:
        - name: "total_event_count"
          path: "total_events.value"
          type: "single_value"
        - name: "events_by_type"
          path: "by_event_type"
          type: "terms_buckets"
          dimension_field: "event_type"

  # ---------------------------------------------
  # Example 4: Multi-dimensional aggregation
  # ---------------------------------------------
  - name: requests_by_endpoint_and_status
    description: "Request counts grouped by endpoint and status"
    data_source: main_cluster
    index_pattern: "api-logs-*"
    schedule: "0 */4 * * *"  # Every 4 hours (cron)

    time_range:
      gte: "now-4h"
      lte: "now"
      field: "@timestamp"

    query:
      size: 0
      aggs:
        by_endpoint:
          terms:
            field: "endpoint.keyword"
            size: 100
          aggs:
            by_status:
              terms:
                field: "status"
                size: 10

    result_mapping:
      type: "nested_buckets"
      levels:
        - aggregation_path: "by_endpoint"
          dimension_field: "endpoint"
        - aggregation_path: "by_status"
          dimension_field: "status_code"
      value_field: "doc_count"

# =============================================================================
# MYSQL - Same as before, works with AWS RDS
# Supports both env vars ${VAR} and SSM ${ssm:/path}
# =============================================================================
mysql:
  host: "${ssm:/PREDICTIVE/PRODUCTION/SR/MYSQL/HOST}"
  port: 3306
  database: "predictive"
  user: "${ssm:/PREDICTIVE/PRODUCTION/SR_API/USER}"
  password: "${ssm:/PREDICTIVE/PRODUCTION/SR_API/PASSWORD}"
  charset: "utf8mb4"

# =============================================================================
# SCHEDULING
# =============================================================================
scheduling:
  enabled: true
  timezone: "UTC"

  # Default schedule for index metrics collection
  index_metrics_cron: "0 2 * * *"  # Daily at 2 AM

  # Aggregation queries use their own schedules defined above

# =============================================================================
# LOGGING
# =============================================================================
logging:
  level: "INFO"
  file: "logs/elasmetrics.log"
  console: true
```

---

## Key Features

### AWS SSM Parameter Store Integration

Configuration values can reference AWS SSM Parameter Store using the `${ssm:/path}` syntax:

```yaml
data_sources:
  main_cluster:
    hosts:
      - "${ssm:/PREDICTIVE/PRODUCTION/ELASTICSEARCH/PRODUCT_FEED}"
    password: "${ssm:/PREDICTIVE/PRODUCTION/ELASTICSEARCH/PASSWORD}"

mysql:
  host: "${ssm:/PREDICTIVE/PRODUCTION/SR/MYSQL/HOST}"
  password: "${ssm:/PREDICTIVE/PRODUCTION/SR_API/PASSWORD}"
```

**How it works:**
- The `DataSourceManager._resolve_value()` method detects `${ssm:...}` syntax
- Uses `boto3` to fetch parameters from AWS SSM with decryption enabled
- Requires AWS credentials configured (IAM role, env vars, or credentials file)
- Falls back to environment variable syntax: `${VAR_NAME}`

### Path Prefix for Proxy Endpoints

For proxy endpoints like DataHub that use non-standard URL patterns, use the `path_prefix` option:

```yaml
data_sources:
  enterprise_datahub:
    hosts:
      - "https://datahub-api.yourcompany.com"
    path_prefix: "/v1/proxy"  # Transforms /{index}/_search to /v1/proxy/{index}/_search
```

**Standard ES URL:**
```
https://es-host/{index}/_search
```

**DataHub proxy URL (with path_prefix):**
```
https://datahub-api.yourcompany.com/v1/proxy/{index}/_search
```

The `AggregationCollector` automatically uses raw transport requests when `path_prefix` is configured.

---

## File Structure (New & Modified)

```
elasmetrics/
├── main.py                                    # MODIFY: Add --source flag, aggregation command
├── config/
│   └── config.yaml                            # MODIFY: Add data_sources, aggregation_queries
│
├── src/
│   ├── services/
│   │   ├── metrics_service.py                 # MODIFY: Support multiple collectors/sources
│   │   └── data_source_manager.py             # NEW: Manages ES clients for multiple sources
│   │
│   ├── collectors/
│   │   ├── base_collector.py                  # MODIFY: Accept data_source parameter
│   │   ├── index_stats_collector.py           # MODIFY: Work with any data source
│   │   └── aggregation_collector.py           # NEW: Runs aggregation queries
│   │
│   ├── repositories/
│   │   ├── mysql_repository.py                # EXISTING: For index_metrics
│   │   └── aggregation_repository.py          # NEW: For aggregation_metrics table
│   │
│   └── models/
│       ├── index_metrics.py                   # EXISTING
│       └── aggregation_metric.py              # NEW: Data model for aggregation results
│
├── scripts/
│   └── airflow_runner.py                      # MODIFY: Support aggregation collection
│
└── docs/
    └── SR_USAGE_INTEGRATION_PLAN.md           # This file
```

---

## New Files to Create

### 1. `src/services/data_source_manager.py`

```python
"""
Manages multiple Elasticsearch/OpenSearch data sources.
Creates and caches ES clients for each configured source.
"""
from typing import Dict, Any, Optional
from elasticsearch import Elasticsearch
import logging


class DataSourceManager:
    """
    Singleton manager for ES/OpenSearch data source connections.
    Handles multiple clusters (direct VPC + proxy endpoints).
    """
    _instance = None
    _clients: Dict[str, Elasticsearch] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def initialize(self, config: Dict[str, Any]):
        """
        Initialize all data sources from configuration.

        Args:
            config: Full configuration dictionary
        """
        data_sources = config.get('data_sources', {})

        for source_name, source_config in data_sources.items():
            try:
                client = self._create_client(source_name, source_config)
                self._clients[source_name] = client
                self.logger.info(f"Initialized data source: {source_name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize source '{source_name}': {e}")
                raise

    def get_client(self, source_name: str) -> Elasticsearch:
        """
        Get ES client for a data source.

        Args:
            source_name: Name of the data source

        Returns:
            Elasticsearch client instance

        Raises:
            KeyError: If source not found
        """
        if source_name not in self._clients:
            raise KeyError(f"Data source '{source_name}' not found. "
                          f"Available: {list(self._clients.keys())}")
        return self._clients[source_name]

    def get_all_sources(self) -> Dict[str, Elasticsearch]:
        """Get all initialized clients."""
        return self._clients.copy()

    def list_sources(self) -> list:
        """List all available source names."""
        return list(self._clients.keys())

    def _create_client(self, name: str, config: Dict[str, Any]) -> Elasticsearch:
        """
        Create ES client from source configuration.
        Works with both direct ES and proxy endpoints (like DataHub).
        """
        connection_params = {
            'hosts': config.get('hosts', ['http://localhost:9200']),
            'timeout': config.get('timeout', 30),
            'verify_certs': config.get('verify_certs', True),
        }

        # Authentication
        if 'username' in config and 'password' in config:
            connection_params['basic_auth'] = (
                config['username'],
                config['password']
            )
        elif 'api_key' in config:
            connection_params['api_key'] = config['api_key']

        # Custom headers (for proxy authentication)
        if 'headers' in config:
            connection_params['headers'] = config['headers']

        # SSL settings
        if config.get('use_ssl', False):
            connection_params['use_ssl'] = True

        client = Elasticsearch(**connection_params)

        # Validate connection
        self._validate_connection(name, client)

        return client

    def _validate_connection(self, name: str, client: Elasticsearch) -> bool:
        """Validate that a client can connect."""
        try:
            client.cluster.health()
            return True
        except Exception as e:
            # Handle AWS OpenSearch product check errors
            error_msg = str(e)
            if 'not Elasticsearch' in error_msg or 'unknown product' in error_msg:
                self.logger.warning(f"Source '{name}' is AWS OpenSearch (product check bypassed)")
                return True
            raise

    @classmethod
    def reset(cls):
        """Reset singleton (for testing)."""
        if cls._instance:
            cls._instance._clients.clear()
        cls._instance = None
```

### 2. `src/models/aggregation_metric.py`

```python
"""
Data model for aggregation query results.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import json


@dataclass
class AggregationMetric:
    """
    Represents a single metric result from an aggregation query.
    Designed for flexible storage and easy Grafana integration.
    """
    metric_name: str
    data_source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # The index pattern queried
    index_pattern: Optional[str] = None

    # Time range of the query
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None

    # Values
    value_numeric: Optional[float] = None
    value_string: Optional[str] = None

    # Dimensions (for grouping in Grafana)
    dimensions: Dict[str, str] = field(default_factory=dict)

    # Full result for complex aggregations
    result_json: Optional[Dict[str, Any]] = None

    # Metadata
    query_duration_ms: Optional[int] = None

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database-compatible dictionary."""
        data = {
            'metric_name': self.metric_name,
            'data_source': self.data_source,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'index_pattern': self.index_pattern,
            'time_range_start': self.time_range_start.isoformat() if self.time_range_start else None,
            'time_range_end': self.time_range_end.isoformat() if self.time_range_end else None,
            'value_numeric': self.value_numeric,
            'value_string': self.value_string,
            'query_duration_ms': self.query_duration_ms,
            'result_json': json.dumps(self.result_json) if self.result_json else None,
        }

        # Map dimensions to dimension columns
        dim_list = list(self.dimensions.items())
        for i, (name, value) in enumerate(dim_list[:3], 1):  # Max 3 dimensions
            data[f'dimension_{i}_name'] = name
            data[f'dimension_{i}_value'] = str(value)

        # Fill empty dimension columns
        for i in range(len(dim_list) + 1, 4):
            data[f'dimension_{i}_name'] = None
            data[f'dimension_{i}_value'] = None

        return data

    def __repr__(self) -> str:
        dims = ', '.join(f"{k}={v}" for k, v in self.dimensions.items())
        return (f"AggregationMetric(name='{self.metric_name}', "
                f"source='{self.data_source}', "
                f"value={self.value_numeric}, dims=[{dims}])")


@dataclass
class AggregationQueryConfig:
    """Configuration for an aggregation query."""
    name: str
    data_source: str
    index_pattern: str
    query: Dict[str, Any]
    result_mapping: Dict[str, Any]

    description: Optional[str] = None
    schedule: str = "daily"
    time_range: Optional[Dict[str, str]] = None

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'AggregationQueryConfig':
        """Create from YAML config dictionary."""
        return cls(
            name=config['name'],
            data_source=config['data_source'],
            index_pattern=config['index_pattern'],
            query=config['query'],
            result_mapping=config['result_mapping'],
            description=config.get('description'),
            schedule=config.get('schedule', 'daily'),
            time_range=config.get('time_range'),
        )
```

### 3. `src/collectors/aggregation_collector.py`

```python
"""
Collector for custom aggregation queries against ES/OpenSearch.
Runs search queries and extracts metrics from aggregation results.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
import time
import logging

from ..models.aggregation_metric import AggregationMetric, AggregationQueryConfig


class AggregationCollector:
    """
    Executes configured aggregation queries and returns metrics.
    Supports multiple result mapping types for flexible metric extraction.
    """

    def __init__(self, es_client: Elasticsearch, data_source: str):
        """
        Initialize collector with ES client.

        Args:
            es_client: Elasticsearch client for this data source
            data_source: Name of the data source
        """
        self.es_client = es_client
        self.data_source = data_source
        self.logger = logging.getLogger(f"{self.__class__.__name__}[{data_source}]")

    def collect(self, query_configs: List[AggregationQueryConfig]) -> List[AggregationMetric]:
        """
        Execute aggregation queries and collect metrics.

        Args:
            query_configs: List of query configurations to execute

        Returns:
            List of AggregationMetric objects
        """
        all_metrics = []

        for config in query_configs:
            # Only process queries for this data source
            if config.data_source != self.data_source:
                continue

            try:
                self.logger.info(f"Executing query: {config.name}")
                metrics = self._execute_query(config)
                all_metrics.extend(metrics)
                self.logger.info(f"Query '{config.name}' produced {len(metrics)} metrics")
            except Exception as e:
                self.logger.error(f"Failed to execute query '{config.name}': {e}")
                continue

        return all_metrics

    def _execute_query(self, config: AggregationQueryConfig) -> List[AggregationMetric]:
        """Execute a single aggregation query."""
        start_time = time.time()

        # Build the query with time range substitution
        query_body = self._prepare_query(config)

        # Execute search
        response = self.es_client.search(
            index=config.index_pattern,
            body=query_body
        )

        query_duration_ms = int((time.time() - start_time) * 1000)

        # Parse results based on mapping type
        metrics = self._parse_results(config, response, query_duration_ms)

        return metrics

    def _prepare_query(self, config: AggregationQueryConfig) -> Dict[str, Any]:
        """Prepare query body, substituting time range if configured."""
        query = config.query.copy()

        # Time range handling is done in the query itself using ES date math
        # (e.g., "now-1d", "now-1h")

        return query

    def _parse_results(
        self,
        config: AggregationQueryConfig,
        response: Dict[str, Any],
        query_duration_ms: int
    ) -> List[AggregationMetric]:
        """
        Parse ES response based on result_mapping configuration.
        """
        mapping = config.result_mapping
        mapping_type = mapping.get('type', 'single_value')

        base_metric = {
            'metric_name': config.name,
            'data_source': self.data_source,
            'index_pattern': config.index_pattern,
            'query_duration_ms': query_duration_ms,
        }

        if mapping_type == 'single_value':
            return self._parse_single_value(mapping, response, base_metric)
        elif mapping_type == 'terms_buckets':
            return self._parse_terms_buckets(mapping, response, base_metric)
        elif mapping_type == 'nested_buckets':
            return self._parse_nested_buckets(mapping, response, base_metric)
        elif mapping_type == 'mixed':
            return self._parse_mixed(mapping, response, base_metric)
        else:
            self.logger.warning(f"Unknown mapping type: {mapping_type}")
            return []

    def _parse_single_value(
        self,
        mapping: Dict,
        response: Dict,
        base: Dict
    ) -> List[AggregationMetric]:
        """Parse single value aggregations (avg, sum, count, etc.)."""
        metrics = []
        aggs = response.get('aggregations', {})

        for metric_config in mapping.get('metrics', []):
            value = self._get_nested_value(aggs, metric_config['path'])

            if value is not None:
                metric = AggregationMetric(
                    metric_name=f"{base['metric_name']}_{metric_config['name']}"
                               if len(mapping.get('metrics', [])) > 1
                               else base['metric_name'],
                    data_source=base['data_source'],
                    index_pattern=base['index_pattern'],
                    value_numeric=float(value) if value is not None else None,
                    query_duration_ms=base['query_duration_ms'],
                )
                metrics.append(metric)

        return metrics

    def _parse_terms_buckets(
        self,
        mapping: Dict,
        response: Dict,
        base: Dict
    ) -> List[AggregationMetric]:
        """Parse terms aggregation buckets."""
        metrics = []
        aggs = response.get('aggregations', {})

        agg_path = mapping.get('aggregation_path')
        dimension_field = mapping.get('dimension_field', 'key')
        value_field = mapping.get('value_field', 'doc_count')

        buckets = self._get_nested_value(aggs, f"{agg_path}.buckets") or []

        for bucket in buckets:
            metric = AggregationMetric(
                metric_name=base['metric_name'],
                data_source=base['data_source'],
                index_pattern=base['index_pattern'],
                value_numeric=float(bucket.get(value_field, 0)),
                dimensions={dimension_field: str(bucket.get('key', ''))},
                query_duration_ms=base['query_duration_ms'],
            )
            metrics.append(metric)

        return metrics

    def _parse_nested_buckets(
        self,
        mapping: Dict,
        response: Dict,
        base: Dict
    ) -> List[AggregationMetric]:
        """Parse nested/multi-level bucket aggregations."""
        metrics = []
        aggs = response.get('aggregations', {})
        levels = mapping.get('levels', [])
        value_field = mapping.get('value_field', 'doc_count')

        def recurse_buckets(current_aggs, level_idx, dimensions):
            if level_idx >= len(levels):
                # At leaf level, create metric
                value = current_aggs.get(value_field, 0)
                metric = AggregationMetric(
                    metric_name=base['metric_name'],
                    data_source=base['data_source'],
                    index_pattern=base['index_pattern'],
                    value_numeric=float(value),
                    dimensions=dimensions.copy(),
                    query_duration_ms=base['query_duration_ms'],
                )
                metrics.append(metric)
                return

            level = levels[level_idx]
            agg_path = level['aggregation_path']
            dim_field = level['dimension_field']

            buckets = current_aggs.get(agg_path, {}).get('buckets', [])
            for bucket in buckets:
                dimensions[dim_field] = str(bucket.get('key', ''))
                recurse_buckets(bucket, level_idx + 1, dimensions)

        recurse_buckets(aggs, 0, {})
        return metrics

    def _parse_mixed(
        self,
        mapping: Dict,
        response: Dict,
        base: Dict
    ) -> List[AggregationMetric]:
        """Parse mixed result types (combination of single values and buckets)."""
        metrics = []

        for metric_config in mapping.get('metrics', []):
            metric_type = metric_config.get('type', 'single_value')

            if metric_type == 'single_value':
                sub_mapping = {'metrics': [metric_config]}
                metrics.extend(self._parse_single_value(sub_mapping, response, base))
            elif metric_type == 'terms_buckets':
                sub_mapping = {
                    'aggregation_path': metric_config['path'],
                    'dimension_field': metric_config.get('dimension_field', 'key'),
                    'value_field': metric_config.get('value_field', 'doc_count'),
                }
                # Update base metric name for this sub-metric
                sub_base = base.copy()
                sub_base['metric_name'] = f"{base['metric_name']}_{metric_config['name']}"
                metrics.extend(self._parse_terms_buckets(sub_mapping, response, sub_base))

        return metrics

    @staticmethod
    def _get_nested_value(data: Dict, path: str) -> Any:
        """Get value from nested dict using dot notation."""
        keys = path.replace('\\', '').split('.')
        current = data
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if current is None:
                return None
        return current
```

### 4. `src/repositories/aggregation_repository.py`

```python
"""
Repository for aggregation metrics persistence.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager

from ..models.aggregation_metric import AggregationMetric


class AggregationRepository:
    """
    Repository for storing and querying aggregation metrics.
    """

    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS aggregation_metrics (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        metric_name VARCHAR(255) NOT NULL,
        data_source VARCHAR(100) NOT NULL,
        index_pattern VARCHAR(255),
        timestamp DATETIME NOT NULL,
        time_range_start DATETIME,
        time_range_end DATETIME,
        value_numeric DOUBLE,
        value_string VARCHAR(1000),
        dimension_1_name VARCHAR(100),
        dimension_1_value VARCHAR(255),
        dimension_2_name VARCHAR(100),
        dimension_2_value VARCHAR(255),
        dimension_3_name VARCHAR(100),
        dimension_3_value VARCHAR(255),
        result_json JSON,
        query_duration_ms INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_metric_name (metric_name),
        INDEX idx_data_source (data_source),
        INDEX idx_timestamp (timestamp),
        INDEX idx_metric_source_time (metric_name, data_source, timestamp),
        INDEX idx_dimension_1 (dimension_1_name, dimension_1_value),
        INDEX idx_dimension_2 (dimension_2_name, dimension_2_value)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """

    CREATE_LATEST_VIEW_SQL = """
    CREATE OR REPLACE VIEW aggregation_metrics_latest AS
    SELECT am.*
    FROM aggregation_metrics am
    INNER JOIN (
        SELECT metric_name, data_source,
               dimension_1_name, dimension_1_value,
               dimension_2_name, dimension_2_value,
               MAX(timestamp) as max_timestamp
        FROM aggregation_metrics
        GROUP BY metric_name, data_source,
                 dimension_1_name, dimension_1_value,
                 dimension_2_name, dimension_2_value
    ) latest ON am.metric_name = latest.metric_name
              AND am.data_source = latest.data_source
              AND am.timestamp = latest.max_timestamp
              AND COALESCE(am.dimension_1_name, '') = COALESCE(latest.dimension_1_name, '')
              AND COALESCE(am.dimension_1_value, '') = COALESCE(latest.dimension_1_value, '')
    """

    INSERT_SQL = """
    INSERT INTO aggregation_metrics (
        metric_name, data_source, index_pattern, timestamp,
        time_range_start, time_range_end,
        value_numeric, value_string,
        dimension_1_name, dimension_1_value,
        dimension_2_name, dimension_2_value,
        dimension_3_name, dimension_3_value,
        result_json, query_duration_ms
    ) VALUES (
        %(metric_name)s, %(data_source)s, %(index_pattern)s, %(timestamp)s,
        %(time_range_start)s, %(time_range_end)s,
        %(value_numeric)s, %(value_string)s,
        %(dimension_1_name)s, %(dimension_1_value)s,
        %(dimension_2_name)s, %(dimension_2_value)s,
        %(dimension_3_name)s, %(dimension_3_value)s,
        %(result_json)s, %(query_duration_ms)s
    )
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize repository with MySQL config."""
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._connection_params = self._build_connection_params()
        self._ensure_table_exists()

    def _build_connection_params(self) -> Dict[str, Any]:
        """Build connection parameters from config."""
        return {
            'host': self.config.get('host', 'localhost'),
            'port': self.config.get('port', 3306),
            'user': self.config.get('user'),
            'password': self.config.get('password'),
            'database': self.config.get('database'),
            'charset': self.config.get('charset', 'utf8mb4'),
            'cursorclass': DictCursor,
            'autocommit': False,
        }

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        connection = None
        try:
            connection = pymysql.connect(**self._connection_params)
            yield connection
        finally:
            if connection:
                connection.close()

    def _ensure_table_exists(self):
        """Ensure the aggregation_metrics table exists."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(self.CREATE_TABLE_SQL)
                    self.logger.info("Table 'aggregation_metrics' is ready")

                    cursor.execute(self.CREATE_LATEST_VIEW_SQL)
                    self.logger.info("View 'aggregation_metrics_latest' is ready")

                    conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to ensure table exists: {e}")
            raise

    def save_metrics_batch(self, metrics: List[AggregationMetric]) -> int:
        """
        Save multiple metrics in a batch.

        Args:
            metrics: List of AggregationMetric objects

        Returns:
            Number of records inserted
        """
        if not metrics:
            return 0

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    batch_data = [m.to_db_dict() for m in metrics]
                    cursor.executemany(self.INSERT_SQL, batch_data)
                    conn.commit()

                    self.logger.info(f"Saved {len(metrics)} aggregation metrics")
                    return len(metrics)
        except Exception as e:
            self.logger.error(f"Failed to save metrics batch: {e}")
            raise

    def get_metrics_by_name(
        self,
        metric_name: str,
        data_source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query metrics by name with optional filters."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = "SELECT * FROM aggregation_metrics WHERE metric_name = %s"
                    params = [metric_name]

                    if data_source:
                        sql += " AND data_source = %s"
                        params.append(data_source)

                    if start_date:
                        sql += " AND timestamp >= %s"
                        params.append(start_date)

                    if end_date:
                        sql += " AND timestamp <= %s"
                        params.append(end_date)

                    sql += " ORDER BY timestamp DESC LIMIT %s"
                    params.append(limit)

                    cursor.execute(sql, params)
                    return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Failed to get metrics: {e}")
            raise

    def delete_old_metrics(self, days: int = 90) -> int:
        """Delete metrics older than specified days."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    DELETE FROM aggregation_metrics
                    WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)
                    """
                    cursor.execute(sql, (days,))
                    conn.commit()
                    deleted = cursor.rowcount
                    self.logger.info(f"Deleted {deleted} old aggregation metrics")
                    return deleted
        except Exception as e:
            self.logger.error(f"Failed to delete old metrics: {e}")
            raise
```

---

## Modified Files

### 1. `main.py` - Add aggregation command

```python
# Add to argument parser:
parser.add_argument(
    'command',
    choices=['collect', 'collect-aggregations', 'health-check', 'cleanup'],
    help='Command to execute'
)

parser.add_argument(
    '--source',
    type=str,
    default=None,
    help='Specific data source to use (default: all configured sources)'
)

parser.add_argument(
    '--query',
    type=str,
    default=None,
    help='Specific aggregation query to run (default: all configured queries)'
)
```

### 2. CLI Usage After Implementation

```bash
# Collect index metrics from all sources
python main.py collect

# Collect index metrics from specific source
python main.py collect --source main_cluster

# Collect aggregation metrics (all queries)
python main.py collect-aggregations

# Collect specific aggregation query
python main.py collect-aggregations --query error_count_by_status

# Collect aggregations from specific source only
python main.py collect-aggregations --source enterprise_datahub

# Health check all sources
python main.py health-check

# Cleanup old data (both tables)
python main.py cleanup --days 90
```

---

## Grafana Query Examples

### Query 1: Error counts over time by status code

```sql
SELECT
    timestamp,
    dimension_1_value AS status_code,
    value_numeric AS error_count
FROM aggregation_metrics
WHERE metric_name = 'error_count_by_status'
  AND data_source = 'main_cluster'
  AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY timestamp, status_code;
```

### Query 2: Average response time trend

```sql
SELECT
    timestamp,
    value_numeric AS avg_response_time_ms
FROM aggregation_metrics
WHERE metric_name = 'avg_response_time'
  AND timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
ORDER BY timestamp;
```

### Query 3: Compare metrics across clusters

```sql
SELECT
    data_source,
    timestamp,
    value_numeric AS event_count
FROM aggregation_metrics
WHERE metric_name LIKE '%event_count%'
  AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY timestamp, data_source;
```

### Query 4: Latest values per metric (for single stat panels)

```sql
SELECT
    metric_name,
    data_source,
    value_numeric,
    timestamp
FROM aggregation_metrics_latest
WHERE metric_name IN ('avg_response_time', 'error_count_by_status')
ORDER BY metric_name;
```

---

## Implementation Status

All phases have been completed:

| Phase | Tasks | Status |
|-------|-------|--------|
| **Phase 1** | DataSourceManager + multi-cluster config | ✅ Complete |
| **Phase 2** | AggregationMetric model + repository + table | ✅ Complete |
| **Phase 3** | AggregationCollector with result parsing | ✅ Complete |
| **Phase 4** | MetricsService integration + CLI commands | ✅ Complete |
| **Phase 5** | Testing | ✅ Complete |

---

## Summary

| Requirement | Solution | Complexity |
|-------------|----------|------------|
| Daily runs | Existing cron/Airflow support | None |
| Time-series MySQL | Existing + new table | Low |
| Grafana dashboards | Both tables have timestamp indexes | Low |
| Aggregation queries | New AggregationCollector | Medium |
| Multi-cluster (VPC + DataHub) | DataSourceManager (ES-compatible) | Low |
| AWS RDS MySQL | Already supported | None |
| Custom metrics table | New aggregation_metrics table | Low |

The architecture is **clean and extensible** because:
1. DataHub is ES-compatible (same client, different host)
2. Strategy pattern allows easy collector addition
3. Repository pattern keeps data access separate
4. Configuration-driven queries (no code changes for new queries)