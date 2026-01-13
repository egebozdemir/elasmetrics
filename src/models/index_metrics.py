"""
Data models for Elasticsearch index metrics.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class IndexMetrics:
    """
    Data class representing Elasticsearch index metrics.
    Implements Data Transfer Object (DTO) pattern.
    """
    index_name: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Document counts
    docs_count: Optional[int] = None
    docs_deleted: Optional[int] = None
    
    # Store sizes
    store_size_bytes: Optional[int] = None
    pri_store_size_bytes: Optional[int] = None
    store_size_human: Optional[str] = None
    pri_store_size_human: Optional[str] = None
    
    # Index metadata
    status: Optional[str] = None
    health: Optional[str] = None
    pri_shards: Optional[int] = None
    replicas: Optional[int] = None
    creation_date: Optional[str] = None
    
    # Additional metadata
    uuid: Optional[str] = None
    
    # Calculated fields
    growth_2m: Optional[float] = None
    growth_2m_sku: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metrics to dictionary.
        
        Returns:
            Dictionary representation of metrics
        """
        return asdict(self)
    
    def to_db_dict(self) -> Dict[str, Any]:
        """
        Convert metrics to dictionary suitable for database insertion.
        Converts datetime to string and handles None values.
        
        Returns:
            Dictionary with database-compatible values
        """
        data = self.to_dict()
        
        # Convert datetime to ISO format string
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        
        # Remove None values for optional fields
        return {k: v for k, v in data.items() if v is not None}
    
    @classmethod
    def from_es_response(cls, index_name: str, stats: Dict[str, Any]) -> 'IndexMetrics':
        """
        Create IndexMetrics instance from Elasticsearch stats response.
        Factory method for creating instances from ES data.
        
        Args:
            index_name: Name of the index
            stats: Statistics dictionary from Elasticsearch
            
        Returns:
            IndexMetrics instance
        """
        # Extract primaries stats (per-shard stats)
        primaries = stats.get('primaries', {})
        total = stats.get('total', {})
        
        # Extract document stats
        docs = primaries.get('docs', {})
        
        # Extract store stats
        store = primaries.get('store', {})
        total_store = total.get('store', {})
        
        return cls(
            index_name=index_name,
            docs_count=docs.get('count'),
            docs_deleted=docs.get('deleted'),
            store_size_bytes=total_store.get('size_in_bytes'),
            pri_store_size_bytes=store.get('size_in_bytes'),
            store_size_human=cls._format_bytes(total_store.get('size_in_bytes')),
            pri_store_size_human=cls._format_bytes(store.get('size_in_bytes')),
        )
    
    @classmethod
    def from_cat_indices(cls, cat_data: Dict[str, Any]) -> 'IndexMetrics':
        """
        Create IndexMetrics instance from _cat/indices response.
        Alternative factory method for cat API data.
        
        Args:
            cat_data: Dictionary from _cat/indices API
            
        Returns:
            IndexMetrics instance
        """
        return cls(
            index_name=cat_data.get('index', ''),
            status=cat_data.get('status'),
            health=cat_data.get('health'),
            pri_shards=cls._safe_int(cat_data.get('pri')),
            replicas=cls._safe_int(cat_data.get('rep')),
            docs_count=cls._safe_int(cat_data.get('docs.count')),
            docs_deleted=cls._safe_int(cat_data.get('docs.deleted')),
            store_size_bytes=cls._parse_size_to_bytes(cat_data.get('store.size')),
            pri_store_size_bytes=cls._parse_size_to_bytes(cat_data.get('pri.store.size')),
            store_size_human=cat_data.get('store.size'),
            pri_store_size_human=cat_data.get('pri.store.size'),
            uuid=cat_data.get('uuid'),
        )
    
    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        """Safely convert value to integer."""
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _format_bytes(bytes_value: Optional[int]) -> Optional[str]:
        """
        Format bytes to human-readable string.
        
        Args:
            bytes_value: Size in bytes
            
        Returns:
            Human-readable size string (e.g., '1.5 GB')
        """
        if bytes_value is None:
            return None
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        
        return f"{bytes_value:.2f} EB"
    
    @staticmethod
    def _parse_size_to_bytes(size_str: Optional[str]) -> Optional[int]:
        """
        Parse human-readable size string to bytes.
        
        Args:
            size_str: Size string (e.g., '1.5gb', '100mb')
            
        Returns:
            Size in bytes
        """
        if not size_str:
            return None
        
        size_str = size_str.strip().lower()
        
        # Extract number and unit
        import re
        match = re.match(r'([\d.]+)\s*([a-z]+)', size_str)
        if not match:
            return None
        
        value = float(match.group(1))
        unit = match.group(2)
        
        # Convert to bytes
        multipliers = {
            'b': 1,
            'kb': 1024,
            'mb': 1024 ** 2,
            'gb': 1024 ** 3,
            'tb': 1024 ** 4,
            'pb': 1024 ** 5,
        }
        
        multiplier = multipliers.get(unit, 1)
        return int(value * multiplier)
    
    def __repr__(self) -> str:
        """String representation of IndexMetrics."""
        return (f"IndexMetrics(index_name='{self.index_name}', "
                f"docs={self.docs_count}, "
                f"size={self.store_size_human})")

