"""
Base collector abstract class implementing Strategy pattern.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import UnsupportedProductError
import logging

from ..models import IndexMetrics


class BaseCollector(ABC):
    """
    Abstract base class for metric collectors.
    Implements Strategy pattern - defines interface for collecting metrics.
    """

    def __init__(self, es_client: Elasticsearch, config: Dict[str, Any]):
        """
        Initialize collector.

        Args:
            es_client: Elasticsearch client instance
            config: Configuration dictionary
        """
        self.es_client = es_client
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def collect(self) -> List[IndexMetrics]:
        """
        Collect metrics from Elasticsearch.
        Abstract method to be implemented by concrete collectors.

        Returns:
            List of IndexMetrics objects

        Raises:
            Exception: If collection fails
        """
        pass

    def _filter_indices(self, indices: List[str]) -> List[str]:
        """
        Filter indices based on include/exclude patterns from config.

        Args:
            indices: List of index names

        Returns:
            Filtered list of index names
        """
        import fnmatch

        metrics_config = self.config.get('metrics', {})
        include_patterns = metrics_config.get('include_patterns', ['*'])
        exclude_patterns = metrics_config.get('exclude_patterns', [])

        filtered = []

        for index in indices:
            # Check exclude patterns first
            excluded = any(fnmatch.fnmatch(index, pattern) for pattern in exclude_patterns)
            if excluded:
                continue

            # Check include patterns
            included = any(fnmatch.fnmatch(index, pattern) for pattern in include_patterns)
            if included:
                filtered.append(index)

        self.logger.info(f"Filtered {len(indices)} indices to {len(filtered)} indices")
        return filtered

    def _get_all_indices(self) -> List[str]:
        """
        Get list of all indices from Elasticsearch.
        Compatible with AWS OpenSearch by using raw transport when needed.

        Returns:
            List of index names

        Raises:
            Exception: If Elasticsearch query fails
        """
        try:
            # Try normal API call first
            response = self.es_client.cat.indices(format='json', h='index')
            indices = [item['index'] for item in response]
            self.logger.debug(f"Retrieved {len(indices)} indices from Elasticsearch")
            return indices
        except UnsupportedProductError as e:
            # AWS OpenSearch detected - use raw transport to bypass product check
            self.logger.warning(f"AWS OpenSearch detected, using raw transport: {e}")
            try:
                response = self.es_client.transport.perform_request(
                    'GET',
                    '/_cat/indices?format=json&h=index'
                )
                
                if isinstance(response, dict) and 'body' in response:
                    body = response['body']
                elif hasattr(response, 'body'):
                    body = response.body
                else:
                    body = response
                
                indices = [item['index'] for item in body]
                self.logger.info(f"Retrieved {len(indices)} indices from AWS OpenSearch (via raw transport)")
                return indices
            except Exception as transport_error:
                self.logger.error(f"Failed to get indices via raw transport: {transport_error}")
                raise ConnectionError(f"Failed to get indices from AWS OpenSearch: {transport_error}") from transport_error
        except Exception as e:
            self.logger.error(f"Failed to get indices: {e}")
            raise

    def _batch_process(self, items: List[Any], batch_size: int = None) -> List[List[Any]]:
        """
        Split items into batches for processing.

        Args:
            items: List of items to batch
            batch_size: Size of each batch (from config if not specified)

        Returns:
            List of batches
        """
        if batch_size is None:
            batch_size = self.config.get('metrics', {}).get('batch_size', 100)

        batches = []
        for i in range(0, len(items), batch_size):
            batches.append(items[i:i + batch_size])

        return batches

    def validate_connection(self) -> bool:
        """
        Validate Elasticsearch connection.
        Compatible with both Elasticsearch and AWS OpenSearch.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Use cluster health instead of info() to avoid product check issues
            # This works with both Elasticsearch and AWS OpenSearch
            health = self.es_client.cluster.health()
            cluster_name = health.get('cluster_name', 'unknown')
            self.logger.info(f"Connected to Elasticsearch cluster: {cluster_name}")
            return True
        except Exception as e:
            # Check if this is AWS OpenSearch product check error
            error_msg = str(e)
            if 'not Elasticsearch' in error_msg or 'unknown product' in error_msg:
                # This is AWS OpenSearch - the API calls work but product check fails
                # We can safely ignore this and continue
                self.logger.warning(f"AWS OpenSearch detected (product check failed, but connection works): {e}")
                self.logger.info("Connected to AWS OpenSearch cluster (bypassing product check)")
                return True

            # For other errors, try a lightweight fallback check
            try:
                self.es_client.cat.indices(h='index', format='json', s='index')
                self.logger.info("Connected to Elasticsearch/OpenSearch cluster (product check bypassed)")
                return True
            except Exception as e2:
                self.logger.error(f"Failed to connect to Elasticsearch: {e}")
                return False

