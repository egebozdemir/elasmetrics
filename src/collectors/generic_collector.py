"""
Generic collector for Elasticsearch metrics.
Supports collecting any metric configured in the system without code changes.
"""
from typing import List, Dict, Any
from elasticsearch import Elasticsearch

from .base_collector import BaseCollector
from ..models.generic_metrics import (
    GenericMetrics,
    MetricDefinition,
    MetricRegistry,
    MetricType,
    get_metric_registry
)


class GenericMetricsCollector(BaseCollector):
    """
    Generic metrics collector that can collect any ES metrics.
    Configuration-driven, no code changes needed for new metrics.
    """
    
    def __init__(self, es_client: Elasticsearch, config: Dict[str, Any]):
        """
        Initialize generic metrics collector.
        
        Args:
            es_client: Elasticsearch client instance
            config: Configuration dictionary
        """
        super().__init__(es_client, config)
        self.registry = get_metric_registry()
        self._load_custom_metrics()
    
    def _load_custom_metrics(self):
        """Load custom metric definitions from configuration."""
        custom_metrics = self.config.get('metrics', {}).get('custom_definitions', [])
        
        for metric_def in custom_metrics:
            try:
                definition = MetricDefinition(
                    name=metric_def['name'],
                    es_path=metric_def['es_path'],
                    metric_type=MetricType(metric_def.get('type', 'string')),
                    description=metric_def.get('description'),
                    unit=metric_def.get('unit'),
                    aggregatable=metric_def.get('aggregatable', True)
                )
                self.registry.register(definition)
                self.logger.info(f"Registered custom metric: {definition.name}")
            except Exception as e:
                self.logger.warning(f"Failed to register custom metric {metric_def.get('name')}: {e}")
    
    def collect(self) -> List[GenericMetrics]:
        """
        Collect metrics from Elasticsearch.
        
        Returns:
            List of GenericMetrics objects
            
        Raises:
            Exception: If collection fails
        """
        self.logger.info("Starting generic metrics collection")
        
        if not self.validate_connection():
            raise ConnectionError("Cannot connect to Elasticsearch")
        
        try:
            # Get configured metrics to collect
            metric_names = self.config.get('metrics', {}).get('collect', [])
            
            if not metric_names:
                # If no specific metrics configured, use all registered
                self.logger.warning("No metrics configured, collecting all registered metrics")
                metric_definitions = self.registry.get_all()
            else:
                # Get definitions for configured metrics
                metric_definitions = self.registry.get_by_names(metric_names)
                
                # Warn about missing definitions
                found_names = [d.name for d in metric_definitions]
                missing = set(metric_names) - set(found_names)
                if missing:
                    self.logger.warning(f"Metric definitions not found for: {missing}")
            
            if not metric_definitions:
                self.logger.warning("No valid metric definitions found")
                return []
            
            self.logger.info(f"Collecting {len(metric_definitions)} metrics")
            
            # Get all indices
            all_indices = self._get_all_indices()
            filtered_indices = self._filter_indices(all_indices)
            
            if not filtered_indices:
                self.logger.warning("No indices match the configured patterns")
                return []
            
            # Collect metrics
            metrics_list = []
            batches = self._batch_process(filtered_indices)
            
            for batch_num, batch in enumerate(batches, 1):
                self.logger.info(f"Processing batch {batch_num}/{len(batches)} ({len(batch)} indices)")
                batch_metrics = self._collect_batch_metrics(batch, metric_definitions)
                metrics_list.extend(batch_metrics)
            
            self.logger.info(f"Successfully collected metrics for {len(metrics_list)} indices")
            return metrics_list
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {e}", exc_info=True)
            raise
    
    def _collect_batch_metrics(
        self,
        indices: List[str],
        metric_definitions: List[MetricDefinition]
    ) -> List[GenericMetrics]:
        """
        Collect metrics for a batch of indices.
        
        Args:
            indices: List of index names
            metric_definitions: List of metrics to collect
            
        Returns:
            List of GenericMetrics objects
        """
        metrics_list = []
        
        # Determine collection method based on metrics
        use_stats_api = any(
            '.' in d.es_path and not d.es_path.startswith('settings.')
            for d in metric_definitions
        )
        
        if use_stats_api:
            # Use _stats API for detailed metrics
            metrics_list = self._collect_from_stats_api(indices, metric_definitions)
        else:
            # Use _cat/indices for simpler metrics
            metrics_list = self._collect_from_cat_api(indices, metric_definitions)
        
        return metrics_list
    
    def _collect_from_stats_api(
        self,
        indices: List[str],
        metric_definitions: List[MetricDefinition]
    ) -> List[GenericMetrics]:
        """
        Collect metrics using _stats API (more detailed).
        
        Args:
            indices: List of index names
            metric_definitions: List of metrics to collect
            
        Returns:
            List of GenericMetrics objects
        """
        metrics_list = []
        
        try:
            # Get stats for all indices at once
            response = self.es_client.indices.stats(index=','.join(indices))
            
            # Process each index
            for index_name in indices:
                if index_name not in response['indices']:
                    continue
                
                index_stats = response['indices'][index_name]
                
                # Create metrics object
                metrics = GenericMetrics.from_es_response(
                    index_name=index_name,
                    stats=index_stats,
                    metric_definitions=metric_definitions
                )
                
                # Add metadata
                metrics.add_metadata('uuid', index_stats.get('uuid'))
                metrics.add_metadata('health', index_stats.get('health'))
                metrics.add_metadata('status', index_stats.get('status'))
                
                metrics_list.append(metrics)
                
        except Exception as e:
            self.logger.error(f"Failed to collect from stats API: {e}")
            # Fallback to individual collection
            for index_name in indices:
                try:
                    metrics = self._collect_single_index_stats(index_name, metric_definitions)
                    if metrics:
                        metrics_list.append(metrics)
                except Exception as index_error:
                    self.logger.warning(f"Failed to collect metrics for {index_name}: {index_error}")
        
        return metrics_list
    
    def _collect_from_cat_api(
        self,
        indices: List[str],
        metric_definitions: List[MetricDefinition]
    ) -> List[GenericMetrics]:
        """
        Collect metrics using _cat/indices API (faster, less detailed).
        
        Args:
            indices: List of index names
            metric_definitions: List of metrics to collect
            
        Returns:
            List of GenericMetrics objects
        """
        metrics_list = []
        
        try:
            # Determine which headers we need
            headers = self._get_cat_headers_for_metrics(metric_definitions)
            
            # Get metrics
            response = self.es_client.cat.indices(
                index=','.join(indices),
                format='json',
                h=','.join(headers),
                bytes='b'
            )
            
            # Process each index
            for item in response:
                index_name = item.get('index', item.get('i'))
                if not index_name:
                    continue
                
                metrics = GenericMetrics(index_name=index_name)
                
                # Map cat API fields to metrics
                for definition in metric_definitions:
                    # Try to find value in cat response
                    cat_field = self._map_metric_to_cat_field(definition.name)
                    value = item.get(cat_field)
                    
                    if value is not None:
                        try:
                            metrics.add_metric(definition.name, value, definition)
                        except (ValueError, TypeError) as e:
                            self.logger.debug(f"Failed to add metric {definition.name}: {e}")
                
                # Add metadata
                metrics.add_metadata('health', item.get('health', item.get('h')))
                metrics.add_metadata('status', item.get('status', item.get('s')))
                metrics.add_metadata('uuid', item.get('uuid', item.get('id')))
                
                metrics_list.append(metrics)
                
        except Exception as e:
            self.logger.error(f"Failed to collect from cat API: {e}")
        
        return metrics_list
    
    def _collect_single_index_stats(
        self,
        index_name: str,
        metric_definitions: List[MetricDefinition]
    ) -> GenericMetrics:
        """
        Collect metrics for a single index using _stats API.
        
        Args:
            index_name: Index name
            metric_definitions: List of metrics to collect
            
        Returns:
            GenericMetrics object
        """
        try:
            response = self.es_client.indices.stats(index=index_name)
            index_stats = response['indices'].get(index_name)
            
            if not index_stats:
                raise ValueError(f"No stats found for index {index_name}")
            
            metrics = GenericMetrics.from_es_response(
                index_name=index_name,
                stats=index_stats,
                metric_definitions=metric_definitions
            )
            
            # Get additional metadata from settings
            settings_response = self.es_client.indices.get(index=index_name)
            if index_name in settings_response:
                settings = settings_response[index_name].get('settings', {}).get('index', {})
                metrics.add_metadata('number_of_shards', settings.get('number_of_shards'))
                metrics.add_metadata('number_of_replicas', settings.get('number_of_replicas'))
                metrics.add_metadata('creation_date', settings.get('creation_date'))
                metrics.add_metadata('uuid', settings.get('uuid'))
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect stats for {index_name}: {e}")
            raise
    
    def _get_cat_headers_for_metrics(self, metric_definitions: List[MetricDefinition]) -> List[str]:
        """
        Get cat API headers needed for the given metrics.
        
        Args:
            metric_definitions: List of metrics
            
        Returns:
            List of cat API header names
        """
        # Always include these
        headers = ['index', 'health', 'status', 'uuid']
        
        # Map metrics to cat headers
        for definition in metric_definitions:
            cat_field = self._map_metric_to_cat_field(definition.name)
            if cat_field and cat_field not in headers:
                headers.append(cat_field)
        
        return headers
    
    def _map_metric_to_cat_field(self, metric_name: str) -> str:
        """
        Map metric name to cat API field name.
        
        Args:
            metric_name: Metric name
            
        Returns:
            Cat API field name
        """
        # Direct mappings
        mapping = {
            'docs.count': 'docs.count',
            'docs.deleted': 'docs.deleted',
            'store.size_in_bytes': 'store.size',
            'pri.store.size_in_bytes': 'pri.store.size',
        }
        
        return mapping.get(metric_name, metric_name.replace('_', '.'))

