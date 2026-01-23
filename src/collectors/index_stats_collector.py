"""
Collector for Elasticsearch index statistics.
"""
from typing import List, Dict, Any
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import UnsupportedProductError

from .base_collector import BaseCollector
from ..models import IndexMetrics


class IndexStatsCollector(BaseCollector):
    """
    Concrete implementation of BaseCollector for index statistics.
    Uses Elasticsearch _cat/indices API for efficient data collection.
    """
    
    def __init__(self, es_client: Elasticsearch, config: Dict[str, Any]):
        """
        Initialize index stats collector.
        
        Args:
            es_client: Elasticsearch client instance
            config: Configuration dictionary
        """
        super().__init__(es_client, config)
    
    def collect(self) -> List[IndexMetrics]:
        """
        Collect index statistics from Elasticsearch.
        
        Returns:
            List of IndexMetrics objects
            
        Raises:
            Exception: If collection fails
        """
        self.logger.info("Starting index metrics collection")
        
        # Validate connection first
        if not self.validate_connection():
            raise ConnectionError("Cannot connect to Elasticsearch")
        
        try:
            # Get all indices
            all_indices = self._get_all_indices()
            
            # Filter indices based on patterns
            filtered_indices = self._filter_indices(all_indices)
            
            if not filtered_indices:
                self.logger.warning("No indices match the configured patterns")
                return []
            
            # Collect metrics for filtered indices
            metrics_list = []
            
            # Process in batches to avoid overwhelming ES
            batches = self._batch_process(filtered_indices)
            
            for batch_num, batch in enumerate(batches, 1):
                self.logger.info(f"Processing batch {batch_num}/{len(batches)} "
                               f"({len(batch)} indices)")
                
                batch_metrics = self._collect_batch_metrics(batch)
                metrics_list.extend(batch_metrics)
            
            self.logger.info(f"Successfully collected metrics for {len(metrics_list)} indices")
            return metrics_list
            
        except Exception as e:
            self.logger.error(f"Failed to collect index metrics: {e}", exc_info=True)
            raise
    
    def _collect_batch_metrics(self, indices: List[str]) -> List[IndexMetrics]:
        """
        Collect metrics for a batch of indices using _cat/indices API.
        Compatible with AWS OpenSearch.
        
        Args:
            indices: List of index names
            
        Returns:
            List of IndexMetrics objects
        """
        metrics_list = []
        
        # Define which fields we want from _cat/indices
        headers = [
            'index', 'health', 'status', 'uuid',
            'pri', 'rep',
            'docs.count', 'docs.deleted',
            'store.size', 'pri.store.size',
            'creation.date.string'
        ]
        
        # Get metrics for all indices in batch at once
        # Using comma-separated index names is more efficient
        index_pattern = ','.join(indices)
        
        try:
            response = self.es_client.cat.indices(
                index=index_pattern,
                format='json',
                h=','.join(headers),
                bytes='b'  # Get sizes in bytes
            )
            
            # Parse response and create IndexMetrics objects
            for item in response:
                try:
                    metrics = IndexMetrics.from_cat_indices(item)
                    metrics_list.append(metrics)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse metrics for index {item.get('index', 'unknown')}: {e}"
                    )
                    continue
                    
        except UnsupportedProductError as e:
            # AWS OpenSearch detected - use raw transport
            self.logger.warning(f"AWS OpenSearch detected in batch collection, using raw transport: {e}")
            try:
                from urllib.parse import urlencode
                query_params = {'format': 'json', 'h': ','.join(headers), 'bytes': 'b'}
                query_string = urlencode(query_params)
                
                response = self.es_client.transport.perform_request(
                    'GET',
                    f'/_cat/indices/{index_pattern}?{query_string}'
                )
                
                if isinstance(response, dict) and 'body' in response:
                    body = response['body']
                elif hasattr(response, 'body'):
                    body = response.body
                else:
                    body = response
                
                for item in body:
                    try:
                        metrics = IndexMetrics.from_cat_indices(item)
                        metrics_list.append(metrics)
                    except Exception as parse_error:
                        self.logger.warning(
                            f"Failed to parse metrics for index {item.get('index', 'unknown')}: {parse_error}"
                        )
                        continue
                        
            except Exception as transport_error:
                self.logger.error(f"Failed to collect batch metrics via raw transport: {transport_error}")
                metrics_list = self._collect_individual_metrics(indices)
                
        except Exception as e:
            self.logger.error(f"Failed to collect batch metrics: {e}")
            # Try individual collection as fallback
            metrics_list = self._collect_individual_metrics(indices)
        
        return metrics_list
    
    def _collect_individual_metrics(self, indices: List[str]) -> List[IndexMetrics]:
        """
        Fallback method to collect metrics for indices one by one.
        Used when batch collection fails. Compatible with AWS OpenSearch.
        
        Args:
            indices: List of index names
            
        Returns:
            List of IndexMetrics objects
        """
        self.logger.warning("Falling back to individual index collection")
        metrics_list = []
        
        headers = [
            'index', 'health', 'status', 'uuid',
            'pri', 'rep',
            'docs.count', 'docs.deleted',
            'store.size', 'pri.store.size',
            'creation.date.string'
        ]
        
        for index_name in indices:
            try:
                response = self.es_client.cat.indices(
                    index=index_name,
                    format='json',
                    h=','.join(headers),
                    bytes='b'
                )
                
                if response:
                    metrics = IndexMetrics.from_cat_indices(response[0])
                    metrics_list.append(metrics)
                    
            except UnsupportedProductError:
                # AWS OpenSearch - use raw transport
                try:
                    from urllib.parse import urlencode
                    query_params = {'format': 'json', 'h': ','.join(headers), 'bytes': 'b'}
                    query_string = urlencode(query_params)
                    
                    response = self.es_client.transport.perform_request(
                        'GET',
                        f'/_cat/indices/{index_name}?{query_string}'
                    )
                    
                    if isinstance(response, dict) and 'body' in response:
                        body = response['body']
                    elif hasattr(response, 'body'):
                        body = response.body
                    else:
                        body = response
                    
                    if body:
                        metrics = IndexMetrics.from_cat_indices(body[0])
                        metrics_list.append(metrics)
                        
                except Exception as transport_error:
                    self.logger.warning(
                        f"Failed to collect metrics for index {index_name} via raw transport: {transport_error}"
                    )
                    continue
                    
            except Exception as e:
                self.logger.warning(f"Failed to collect metrics for index {index_name}: {e}")
                continue
        
        return metrics_list
    
    def collect_detailed_stats(self, index_name: str) -> IndexMetrics:
        """
        Collect detailed statistics for a specific index using _stats API.
        Provides more detailed information than _cat/indices.
        
        Args:
            index_name: Name of the index
            
        Returns:
            IndexMetrics object with detailed stats
            
        Raises:
            Exception: If collection fails
        """
        try:
            response = self.es_client.indices.stats(index=index_name)
            
            # Get stats for the specific index
            index_stats = response['indices'].get(index_name)
            if not index_stats:
                raise ValueError(f"No stats found for index {index_name}")
            
            # Create metrics from detailed stats
            metrics = IndexMetrics.from_es_response(index_name, index_stats)
            
            # Also get index settings for additional metadata
            settings_response = self.es_client.indices.get(index=index_name)
            index_settings = settings_response[index_name]
            
            # Add settings information
            settings = index_settings.get('settings', {}).get('index', {})
            metrics.pri_shards = int(settings.get('number_of_shards', 0))
            metrics.replicas = int(settings.get('number_of_replicas', 0))
            metrics.creation_date = settings.get('creation_date')
            metrics.uuid = settings.get('uuid')
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect detailed stats for {index_name}: {e}")
            raise

