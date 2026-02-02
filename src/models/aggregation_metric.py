"""
Data models for aggregation query results.
Supports flexible metric storage from ES _count and _search aggregation queries.
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class QueryType(Enum):
    """Supported ES query types."""
    COUNT = "count"      # _count API
    SEARCH = "search"    # _search API with aggregations


class ResultMappingType(Enum):
    """Types of result parsing strategies."""
    SINGLE_VALUE = "single_value"      # Single numeric result (count, avg, sum)
    TERMS_BUCKETS = "terms_buckets"    # Terms aggregation buckets
    NESTED_BUCKETS = "nested_buckets"  # Multi-level nested aggregations
    MIXED = "mixed"                    # Combination of above


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

    # Time range of the query (for context)
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None

    # Values - flexible storage
    value_numeric: Optional[float] = None
    value_string: Optional[str] = None

    # Dimensions (for grouping/filtering in Grafana)
    # Supports up to 3 dimensions (e.g., locale, status_code, endpoint)
    dimensions: Dict[str, str] = field(default_factory=dict)

    # Full result for complex aggregations (stored as JSON)
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

        # Map dimensions to dimension columns (max 3)
        dim_list = list(self.dimensions.items())
        for i in range(1, 4):
            if i <= len(dim_list):
                name, value = dim_list[i - 1]
                data[f'dimension_{i}_name'] = name
                data[f'dimension_{i}_value'] = str(value) if value is not None else None
            else:
                data[f'dimension_{i}_name'] = None
                data[f'dimension_{i}_value'] = None

        return data

    def to_dict(self) -> Dict[str, Any]:
        """Convert to regular dictionary."""
        return {
            'metric_name': self.metric_name,
            'data_source': self.data_source,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'index_pattern': self.index_pattern,
            'value_numeric': self.value_numeric,
            'value_string': self.value_string,
            'dimensions': self.dimensions,
            'result_json': self.result_json,
            'query_duration_ms': self.query_duration_ms,
        }

    def __repr__(self) -> str:
        dims = ', '.join(f"{k}={v}" for k, v in self.dimensions.items())
        dims_str = f", dims=[{dims}]" if dims else ""
        return (f"AggregationMetric(name='{self.metric_name}', "
                f"source='{self.data_source}', "
                f"value={self.value_numeric}{dims_str})")


@dataclass
class AggregationQueryConfig:
    """
    Configuration for an aggregation query.
    Loaded from config.yaml aggregation_queries section.
    """
    name: str
    data_source: str
    index_pattern: str
    query: Dict[str, Any]
    result_mapping: Dict[str, Any]

    description: Optional[str] = None
    query_type: QueryType = QueryType.SEARCH
    schedule: str = "daily"
    time_range: Optional[Dict[str, str]] = None
    enabled: bool = True

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'AggregationQueryConfig':
        """Create from YAML config dictionary."""
        # Parse query_type
        query_type_str = config.get('query_type', 'search').lower()
        try:
            query_type = QueryType(query_type_str)
        except ValueError:
            query_type = QueryType.SEARCH

        return cls(
            name=config['name'],
            data_source=config['data_source'],
            index_pattern=config['index_pattern'],
            query=config['query'],
            result_mapping=config['result_mapping'],
            description=config.get('description'),
            query_type=query_type,
            schedule=config.get('schedule', 'daily'),
            time_range=config.get('time_range'),
            enabled=config.get('enabled', True),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert back to dictionary."""
        return {
            'name': self.name,
            'data_source': self.data_source,
            'index_pattern': self.index_pattern,
            'query': self.query,
            'result_mapping': self.result_mapping,
            'description': self.description,
            'query_type': self.query_type.value,
            'schedule': self.schedule,
            'time_range': self.time_range,
            'enabled': self.enabled,
        }


def load_query_configs(config: Dict[str, Any]) -> List[AggregationQueryConfig]:
    """
    Load aggregation query configurations from main config.

    Args:
        config: Full configuration dictionary

    Returns:
        List of AggregationQueryConfig objects
    """
    query_configs = []
    queries = config.get('aggregation_queries', [])

    logger = logging.getLogger(__name__)

    for query_dict in queries:
        try:
            query_config = AggregationQueryConfig.from_dict(query_dict)
            if query_config.enabled:
                query_configs.append(query_config)
        except KeyError as e:
            logger.warning(f"Invalid query config, missing required field: {e}")
        except Exception as e:
            logger.warning(f"Failed to parse query config: {e}")

    return query_configs
