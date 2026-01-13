"""
Generic metrics model for flexible metric collection.
Allows collecting any metric from Elasticsearch without code changes.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from enum import Enum
import json


class MetricType(Enum):
    """Supported metric data types for type safety."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    TIMESTAMP = "timestamp"
    JSON = "json"


@dataclass
class MetricDefinition:
    """
    Definition of a metric to be collected.
    Provides type safety and validation.
    """
    name: str                           # Metric name (e.g., 'docs.count')
    es_path: str                        # Path in ES response (e.g., 'primaries.docs.count')
    metric_type: MetricType             # Data type
    description: Optional[str] = None   # Human-readable description
    unit: Optional[str] = None          # Unit of measurement (bytes, count, etc.)
    aggregatable: bool = True           # Can this metric be aggregated?
    
    def validate_value(self, value: Any) -> bool:
        """Validate that a value matches the metric type."""
        if value is None:
            return True
        
        try:
            if self.metric_type == MetricType.STRING:
                return isinstance(value, str)
            elif self.metric_type == MetricType.INTEGER:
                return isinstance(value, int) or (isinstance(value, str) and value.isdigit())
            elif self.metric_type == MetricType.FLOAT:
                float(value)
                return True
            elif self.metric_type == MetricType.BOOLEAN:
                return isinstance(value, bool)
            elif self.metric_type == MetricType.TIMESTAMP:
                return isinstance(value, (str, int, datetime))
            elif self.metric_type == MetricType.JSON:
                return True
            return False
        except (ValueError, TypeError):
            return False
    
    def cast_value(self, value: Any) -> Any:
        """Cast value to the appropriate type."""
        if value is None:
            return None
        
        try:
            if self.metric_type == MetricType.STRING:
                return str(value)
            elif self.metric_type == MetricType.INTEGER:
                return int(value)
            elif self.metric_type == MetricType.FLOAT:
                return float(value)
            elif self.metric_type == MetricType.BOOLEAN:
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ('true', '1', 'yes')
            elif self.metric_type == MetricType.TIMESTAMP:
                if isinstance(value, datetime):
                    return value
                elif isinstance(value, int):
                    return datetime.fromtimestamp(value / 1000.0)  # ES timestamps are in ms
                else:
                    return datetime.fromisoformat(str(value))
            elif self.metric_type == MetricType.JSON:
                if isinstance(value, (dict, list)):
                    return value
                return json.loads(str(value))
        except (ValueError, TypeError) as e:
            return None
        
        return value


@dataclass
class GenericMetrics:
    """
    Generic metrics container that can hold any metrics dynamically.
    Provides type safety through MetricDefinitions while remaining flexible.
    """
    index_name: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_metric(self, name: str, value: Any, definition: Optional[MetricDefinition] = None):
        """
        Add a metric with optional type validation.
        
        Args:
            name: Metric name
            value: Metric value
            definition: Optional metric definition for type safety
        """
        if definition:
            if not definition.validate_value(value):
                raise ValueError(f"Value {value} does not match type {definition.metric_type} for metric {name}")
            value = definition.cast_value(value)
        
        self.metrics[name] = value
    
    def get_metric(self, name: str, default: Any = None) -> Any:
        """Get a metric value by name."""
        return self.metrics.get(name, default)
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata (health, status, uuid, etc.)."""
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'index_name': self.index_name,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'metrics': self.metrics,
            'metadata': self.metadata
        }
    
    def to_db_dict(self) -> Dict[str, Any]:
        """
        Convert to database-compatible dictionary.
        Separates core fields from dynamic metrics stored as JSON.
        """
        return {
            'index_name': self.index_name,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'metrics_json': json.dumps(self.metrics),
            'metadata_json': json.dumps(self.metadata)
        }
    
    def to_flat_dict(self) -> Dict[str, Any]:
        """
        Convert to flat dictionary with all metrics at top level.
        Useful for CSV export or flat database schemas.
        """
        result = {
            'index_name': self.index_name,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
        }
        
        # Add all metrics with prefix
        for key, value in self.metrics.items():
            result[f'metric_{key}'] = value
        
        # Add metadata
        for key, value in self.metadata.items():
            result[f'meta_{key}'] = value
        
        return result
    
    @classmethod
    def from_es_response(
        cls,
        index_name: str,
        stats: Dict[str, Any],
        metric_definitions: List[MetricDefinition]
    ) -> 'GenericMetrics':
        """
        Create GenericMetrics from ES response using metric definitions.
        
        Args:
            index_name: Index name
            stats: ES response data
            metric_definitions: List of metrics to extract
            
        Returns:
            GenericMetrics instance
        """
        metrics = cls(index_name=index_name)
        
        for definition in metric_definitions:
            value = cls._extract_nested_value(stats, definition.es_path)
            if value is not None:
                try:
                    metrics.add_metric(definition.name, value, definition)
                except (ValueError, TypeError) as e:
                    # Log warning but continue
                    continue
        
        return metrics
    
    @staticmethod
    def _extract_nested_value(data: Dict[str, Any], path: str) -> Any:
        """
        Extract value from nested dictionary using dot notation path.
        
        Args:
            data: Dictionary to extract from
            path: Dot-separated path (e.g., 'primaries.docs.count')
            
        Returns:
            Value at path or None
        """
        keys = path.split('.')
        current = data
        
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if current is None:
                return None
        
        return current
    
    def __repr__(self) -> str:
        """String representation."""
        return (f"GenericMetrics(index='{self.index_name}', "
                f"metrics={len(self.metrics)}, "
                f"metadata={len(self.metadata)})")


class MetricRegistry:
    """
    Registry for metric definitions.
    Provides a central place to define and manage metrics.
    """
    
    def __init__(self):
        self._metrics: Dict[str, MetricDefinition] = {}
        self._register_default_metrics()
    
    def register(self, definition: MetricDefinition):
        """Register a metric definition."""
        self._metrics[definition.name] = definition
    
    def get(self, name: str) -> Optional[MetricDefinition]:
        """Get a metric definition by name."""
        return self._metrics.get(name)
    
    def get_all(self) -> List[MetricDefinition]:
        """Get all registered metrics."""
        return list(self._metrics.values())
    
    def get_by_names(self, names: List[str]) -> List[MetricDefinition]:
        """Get metric definitions by names."""
        return [self._metrics[name] for name in names if name in self._metrics]
    
    def _register_default_metrics(self):
        """Register commonly used ES metrics."""
        # Document metrics
        self.register(MetricDefinition(
            name="docs.count",
            es_path="primaries.docs.count",
            metric_type=MetricType.INTEGER,
            description="Number of documents",
            unit="count"
        ))
        
        self.register(MetricDefinition(
            name="docs.deleted",
            es_path="primaries.docs.deleted",
            metric_type=MetricType.INTEGER,
            description="Number of deleted documents",
            unit="count"
        ))
        
        # Store metrics
        self.register(MetricDefinition(
            name="store.size_in_bytes",
            es_path="total.store.size_in_bytes",
            metric_type=MetricType.INTEGER,
            description="Total store size",
            unit="bytes"
        ))
        
        self.register(MetricDefinition(
            name="pri.store.size_in_bytes",
            es_path="primaries.store.size_in_bytes",
            metric_type=MetricType.INTEGER,
            description="Primary shards store size",
            unit="bytes"
        ))
        
        # Indexing metrics
        self.register(MetricDefinition(
            name="indexing.index_total",
            es_path="primaries.indexing.index_total",
            metric_type=MetricType.INTEGER,
            description="Total indexing operations",
            unit="count"
        ))
        
        self.register(MetricDefinition(
            name="indexing.index_time_in_millis",
            es_path="primaries.indexing.index_time_in_millis",
            metric_type=MetricType.INTEGER,
            description="Time spent indexing",
            unit="milliseconds"
        ))
        
        # Search metrics
        self.register(MetricDefinition(
            name="search.query_total",
            es_path="primaries.search.query_total",
            metric_type=MetricType.INTEGER,
            description="Total search queries",
            unit="count"
        ))
        
        self.register(MetricDefinition(
            name="search.query_time_in_millis",
            es_path="primaries.search.query_time_in_millis",
            metric_type=MetricType.INTEGER,
            description="Time spent on search queries",
            unit="milliseconds"
        ))
        
        # Merge metrics
        self.register(MetricDefinition(
            name="merges.total",
            es_path="primaries.merges.total",
            metric_type=MetricType.INTEGER,
            description="Total merge operations",
            unit="count"
        ))
        
        self.register(MetricDefinition(
            name="merges.total_time_in_millis",
            es_path="primaries.merges.total_time_in_millis",
            metric_type=MetricType.INTEGER,
            description="Time spent on merges",
            unit="milliseconds"
        ))
        
        # Refresh metrics
        self.register(MetricDefinition(
            name="refresh.total",
            es_path="primaries.refresh.total",
            metric_type=MetricType.INTEGER,
            description="Total refresh operations",
            unit="count"
        ))
        
        # Flush metrics
        self.register(MetricDefinition(
            name="flush.total",
            es_path="primaries.flush.total",
            metric_type=MetricType.INTEGER,
            description="Total flush operations",
            unit="count"
        ))
        
        # Segment metrics
        self.register(MetricDefinition(
            name="segments.count",
            es_path="primaries.segments.count",
            metric_type=MetricType.INTEGER,
            description="Number of segments",
            unit="count"
        ))
        
        self.register(MetricDefinition(
            name="segments.memory_in_bytes",
            es_path="primaries.segments.memory_in_bytes",
            metric_type=MetricType.INTEGER,
            description="Memory used by segments",
            unit="bytes"
        ))
        
        # Translog metrics  
        self.register(MetricDefinition(
            name="translog.size_in_bytes",
            es_path="primaries.translog.size_in_bytes",
            metric_type=MetricType.INTEGER,
            description="Transaction log size",
            unit="bytes"
        ))
        
        # Request cache metrics
        self.register(MetricDefinition(
            name="request_cache.memory_size_in_bytes",
            es_path="total.request_cache.memory_size_in_bytes",
            metric_type=MetricType.INTEGER,
            description="Request cache memory",
            unit="bytes"
        ))
        
        # Field data metrics
        self.register(MetricDefinition(
            name="fielddata.memory_size_in_bytes",
            es_path="total.fielddata.memory_size_in_bytes",
            metric_type=MetricType.INTEGER,
            description="Field data memory",
            unit="bytes"
        ))
        
        # Query cache metrics
        self.register(MetricDefinition(
            name="query_cache.memory_size_in_bytes",
            es_path="total.query_cache.memory_size_in_bytes",
            metric_type=MetricType.INTEGER,
            description="Query cache memory",
            unit="bytes"
        ))


# Global registry instance
_global_registry = MetricRegistry()


def get_metric_registry() -> MetricRegistry:
    """Get the global metric registry."""
    return _global_registry

