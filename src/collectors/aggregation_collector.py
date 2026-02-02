"""
Collector for custom aggregation queries against ES/OpenSearch.
Supports both _count API and _search API with aggregations.
"""
import json
import logging
import time
from typing import List, Dict, Any
from urllib.parse import quote

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import UnsupportedProductError

from ..models.aggregation_metric import (
    AggregationMetric,
    AggregationQueryConfig,
    QueryType,
)


class AggregationCollector:
    """
    Executes configured aggregation queries and returns metrics.
    Supports:
    - _count API for simple document counts
    - _search API with aggregations (terms, avg, sum, etc.)
    - Multiple result mapping strategies
    - Custom path prefix for proxy endpoints (e.g., DataHub)
    """

    def __init__(self, es_client: Elasticsearch, data_source: str, path_prefix: str = None):
        """
        Initialize collector with ES client.

        Args:
            es_client: Elasticsearch client for this data source
            data_source: Name of the data source
            path_prefix: Optional path prefix for proxy endpoints (e.g., '/v1/proxy' for DataHub)
        """
        self.es_client = es_client
        self.data_source = data_source
        self.path_prefix = path_prefix
        self.logger = logging.getLogger(f"{self.__class__.__name__}[{data_source}]")

        if path_prefix:
            self.logger.info(f"Using path prefix: {path_prefix}")

    def collect(self, query_configs: List[AggregationQueryConfig]) -> List[AggregationMetric]:
        """
        Execute aggregation queries and collect metrics.

        Args:
            query_configs: List of query configurations to execute

        Returns:
            List of AggregationMetric objects
        """
        all_metrics = []

        # Filter queries for this data source
        source_queries = [q for q in query_configs if q.data_source == self.data_source]

        if not source_queries:
            self.logger.info(f"No queries configured for data source '{self.data_source}'")
            return all_metrics

        self.logger.info(f"Executing {len(source_queries)} queries for data source '{self.data_source}'")

        for config in source_queries:
            if not config.enabled:
                self.logger.debug(f"Skipping disabled query: {config.name}")
                continue

            try:
                self.logger.info(f"Executing query: {config.name}")
                metrics = self._execute_query(config)
                all_metrics.extend(metrics)
                self.logger.info(f"Query '{config.name}' produced {len(metrics)} metric(s)")
            except Exception as e:
                self.logger.error(f"Failed to execute query '{config.name}': {e}", exc_info=True)
                continue

        return all_metrics

    def collect_single(self, query_config: AggregationQueryConfig) -> List[AggregationMetric]:
        """
        Execute a single query configuration.

        Args:
            query_config: Query configuration to execute

        Returns:
            List of AggregationMetric objects
        """
        if query_config.data_source != self.data_source:
            self.logger.warning(
                f"Query '{query_config.name}' is for source '{query_config.data_source}', "
                f"not '{self.data_source}'"
            )
            return []

        return self._execute_query(query_config)

    def _execute_query(self, config: AggregationQueryConfig) -> List[AggregationMetric]:
        """Execute a single aggregation query."""
        start_time = time.time()

        try:
            # Use raw transport if path_prefix is configured (e.g., DataHub)
            if self.path_prefix:
                return self._execute_query_with_prefix(config, start_time)

            if config.query_type == QueryType.COUNT:
                response = self._execute_count_query(config)
            else:
                response = self._execute_search_query(config)

            query_duration_ms = int((time.time() - start_time) * 1000)

            # Parse results based on mapping type
            metrics = self._parse_results(config, response, query_duration_ms)

            return metrics

        except UnsupportedProductError as e:
            # AWS OpenSearch - try raw transport
            self.logger.warning(f"AWS OpenSearch detected, using raw transport for '{config.name}'")
            return self._execute_query_raw_transport(config, start_time)

    def _execute_count_query(self, config: AggregationQueryConfig) -> Dict[str, Any]:
        """Execute _count API query."""
        query_body = {"query": config.query} if config.query else {}

        response = self.es_client.count(
            index=config.index_pattern,
            body=query_body
        )

        # _count returns: {"count": N, "_shards": {...}}
        return response

    def _execute_search_query(self, config: AggregationQueryConfig) -> Dict[str, Any]:
        """Execute _search API query with aggregations."""
        response = self.es_client.search(
            index=config.index_pattern,
            body=config.query
        )

        return response

    def _execute_query_with_prefix(
        self,
        config: AggregationQueryConfig,
        start_time: float
    ) -> List[AggregationMetric]:
        """
        Execute query using raw transport with path prefix.
        Used for proxy endpoints like DataHub where URL pattern is:
        {host}/v1/proxy/{index}/_search instead of {host}/{index}/_search
        """
        try:
            index_encoded = quote(config.index_pattern, safe='*')

            # Build path with prefix: /v1/proxy/{index}/_search
            if config.query_type == QueryType.COUNT:
                path = f'{self.path_prefix}/{index_encoded}/_count'
                query_body = {"query": config.query} if config.query else {}
            else:
                path = f'{self.path_prefix}/{index_encoded}/_search'
                query_body = config.query

            self.logger.debug(f"Executing request with path: {path}")

            response = self.es_client.transport.perform_request(
                'POST',
                path,
                body=query_body
            )

            body = self._extract_response_body(response)
            query_duration_ms = int((time.time() - start_time) * 1000)
            return self._parse_results(config, body, query_duration_ms)

        except Exception as e:
            self.logger.error(f"Request with prefix failed for '{config.name}': {e}")
            raise

    def _execute_query_raw_transport(
        self,
        config: AggregationQueryConfig,
        start_time: float
    ) -> List[AggregationMetric]:
        """Fallback execution using raw transport for AWS OpenSearch."""
        try:
            index_encoded = quote(config.index_pattern, safe='*')

            if config.query_type == QueryType.COUNT:
                query_body = {"query": config.query} if config.query else {}
                response = self.es_client.transport.perform_request(
                    'POST',
                    f'/{index_encoded}/_count',
                    body=query_body
                )
            else:
                response = self.es_client.transport.perform_request(
                    'POST',
                    f'/{index_encoded}/_search',
                    body=config.query
                )

            body = self._extract_response_body(response)
            query_duration_ms = int((time.time() - start_time) * 1000)
            return self._parse_results(config, body, query_duration_ms)

        except Exception as e:
            self.logger.error(f"Raw transport query failed for '{config.name}': {e}")
            raise

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

        base_kwargs = {
            'metric_name': config.name,
            'data_source': self.data_source,
            'index_pattern': config.index_pattern,
            'query_duration_ms': query_duration_ms,
        }

        # Handle _count API response
        if config.query_type == QueryType.COUNT:
            return self._parse_count_result(response, base_kwargs)

        # Handle _search API response with aggregations
        if mapping_type == 'single_value':
            return self._parse_single_value(mapping, response, base_kwargs)
        elif mapping_type == 'terms_buckets':
            return self._parse_terms_buckets(mapping, response, base_kwargs)
        elif mapping_type == 'nested_buckets':
            return self._parse_nested_buckets(mapping, response, base_kwargs)
        elif mapping_type == 'mixed':
            return self._parse_mixed(mapping, response, base_kwargs)
        else:
            self.logger.warning(f"Unknown mapping type: {mapping_type}")
            return []

    def _parse_count_result(
        self,
        response: Dict[str, Any],
        base_kwargs: Dict[str, Any]
    ) -> List[AggregationMetric]:
        """Parse _count API response."""
        count = response.get('count', 0)

        metric = AggregationMetric(
            **base_kwargs,
            value_numeric=float(count),
        )

        return [metric]

    def _parse_single_value(
        self,
        mapping: Dict[str, Any],
        response: Dict[str, Any],
        base_kwargs: Dict[str, Any]
    ) -> List[AggregationMetric]:
        """Parse single value aggregations (avg, sum, count, percentiles, etc.)."""
        metrics = []
        aggs = response.get('aggregations', {})

        # Handle multiple metrics from single response
        metric_configs = mapping.get('metrics', [])

        if not metric_configs:
            # Simple case: single value from value_path
            value_path = mapping.get('value_path', 'value')
            value = self._get_nested_value(aggs, value_path)

            if value is not None:
                metric = AggregationMetric(
                    **base_kwargs,
                    value_numeric=float(value) if self._is_numeric(value) else None,
                    value_string=str(value) if not self._is_numeric(value) else None,
                )
                metrics.append(metric)
        else:
            # Multiple metrics extracted from response
            for metric_config in metric_configs:
                value = self._get_nested_value(aggs, metric_config['path'])

                if value is not None:
                    metric_name = metric_config.get('name')
                    # Append sub-metric name if multiple metrics
                    full_name = f"{base_kwargs['metric_name']}_{metric_name}" if metric_name else base_kwargs['metric_name']

                    metric = AggregationMetric(
                        metric_name=full_name,
                        data_source=base_kwargs['data_source'],
                        index_pattern=base_kwargs['index_pattern'],
                        query_duration_ms=base_kwargs['query_duration_ms'],
                        value_numeric=float(value) if self._is_numeric(value) else None,
                        value_string=str(value) if not self._is_numeric(value) else None,
                    )
                    metrics.append(metric)

        return metrics

    def _parse_terms_buckets(
        self,
        mapping: Dict[str, Any],
        response: Dict[str, Any],
        base_kwargs: Dict[str, Any]
    ) -> List[AggregationMetric]:
        """Parse terms aggregation buckets."""
        metrics = []
        aggs = response.get('aggregations', {})

        agg_path = mapping.get('aggregation_path')
        dimension_field = mapping.get('dimension_field', 'key')
        value_field = mapping.get('value_field', 'doc_count')

        # Get buckets
        buckets_path = f"{agg_path}.buckets" if agg_path else "buckets"
        buckets = self._get_nested_value(aggs, buckets_path)

        if not buckets:
            # Try direct path
            agg_data = self._get_nested_value(aggs, agg_path) if agg_path else aggs
            buckets = agg_data.get('buckets', []) if isinstance(agg_data, dict) else []

        for bucket in buckets:
            key = bucket.get('key', bucket.get('key_as_string', ''))
            value = bucket.get(value_field, 0)

            # Check for sub-aggregation value
            if value_field != 'doc_count' and '.' in value_field:
                value = self._get_nested_value(bucket, value_field)

            metric = AggregationMetric(
                **base_kwargs,
                value_numeric=float(value) if self._is_numeric(value) else None,
                dimensions={dimension_field: str(key)},
            )
            metrics.append(metric)

        return metrics

    def _parse_nested_buckets(
        self,
        mapping: Dict[str, Any],
        response: Dict[str, Any],
        base_kwargs: Dict[str, Any]
    ) -> List[AggregationMetric]:
        """Parse nested/multi-level bucket aggregations."""
        metrics = []
        aggs = response.get('aggregations', {})
        levels = mapping.get('levels', [])
        value_field = mapping.get('value_field', 'doc_count')

        def recurse_buckets(current_data, level_idx, dimensions):
            if level_idx >= len(levels):
                # At leaf level, create metric
                value = current_data.get(value_field, 0)

                # Check for sub-aggregation value
                if value_field != 'doc_count' and '.' in value_field:
                    value = self._get_nested_value(current_data, value_field)

                metric = AggregationMetric(
                    **base_kwargs,
                    value_numeric=float(value) if self._is_numeric(value) else None,
                    dimensions=dimensions.copy(),
                )
                metrics.append(metric)
                return

            level = levels[level_idx]
            agg_path = level['aggregation_path']
            dim_field = level['dimension_field']

            agg_data = current_data.get(agg_path, {})
            buckets = agg_data.get('buckets', [])

            for bucket in buckets:
                key = bucket.get('key', bucket.get('key_as_string', ''))
                new_dimensions = dimensions.copy()
                new_dimensions[dim_field] = str(key)
                recurse_buckets(bucket, level_idx + 1, new_dimensions)

        recurse_buckets(aggs, 0, {})
        return metrics

    def _parse_mixed(
        self,
        mapping: Dict[str, Any],
        response: Dict[str, Any],
        base_kwargs: Dict[str, Any]
    ) -> List[AggregationMetric]:
        """Parse mixed result types (combination of single values and buckets)."""
        metrics = []

        for metric_config in mapping.get('metrics', []):
            metric_type = metric_config.get('type', 'single_value')
            metric_name = metric_config.get('name', '')

            # Create modified base_kwargs with updated metric name
            modified_kwargs = base_kwargs.copy()
            if metric_name:
                modified_kwargs['metric_name'] = f"{base_kwargs['metric_name']}_{metric_name}"

            if metric_type == 'single_value':
                sub_mapping = {
                    'metrics': [{
                        'path': metric_config['path'],
                        'name': None,  # Don't double-append name
                    }]
                }
                metrics.extend(self._parse_single_value(sub_mapping, response, modified_kwargs))

            elif metric_type == 'terms_buckets':
                sub_mapping = {
                    'aggregation_path': metric_config['path'],
                    'dimension_field': metric_config.get('dimension_field', 'key'),
                    'value_field': metric_config.get('value_field', 'doc_count'),
                }
                metrics.extend(self._parse_terms_buckets(sub_mapping, response, modified_kwargs))

        return metrics

    @staticmethod
    def _extract_response_body(response) -> Dict[str, Any]:
        """
        Extract body from various response formats.
        Raw transport can return different formats depending on ES client version.
        """
        if isinstance(response, dict):
            # Direct dict response or response with 'body' key
            if 'body' in response:
                return response['body']
            return response
        elif hasattr(response, 'body'):
            # ObjectApiResponse from newer ES client versions
            return response.body
        else:
            # Fallback - assume it's already the body
            return response

    @staticmethod
    def _get_nested_value(data: Dict[str, Any], path: str) -> Any:
        """
        Get value from nested dict using dot notation.
        Handles escaped dots in path (for percentile keys like "50.0").
        """
        if not path:
            return data

        # Handle escaped dots (e.g., "percentiles.values.50\\.0")
        parts = []
        current = ""
        i = 0
        while i < len(path):
            if path[i] == '\\' and i + 1 < len(path) and path[i + 1] == '.':
                current += '.'
                i += 2
            elif path[i] == '.':
                if current:
                    parts.append(current)
                current = ""
                i += 1
            else:
                current += path[i]
                i += 1
        if current:
            parts.append(current)

        current_data = data
        for part in parts:
            if not isinstance(current_data, dict):
                return None
            current_data = current_data.get(part)
            if current_data is None:
                return None

        return current_data

    @staticmethod
    def _is_numeric(value: Any) -> bool:
        """Check if value is numeric."""
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, str):
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False
        return False

    def validate_connection(self) -> bool:
        """Validate ES connection for this collector."""
        try:
            self.es_client.cluster.health()
            return True
        except Exception as e:
            error_msg = str(e)
            if 'not Elasticsearch' in error_msg or 'unknown product' in error_msg:
                return True  # AWS OpenSearch
            self.logger.error(f"Connection validation failed: {e}")
            return False
