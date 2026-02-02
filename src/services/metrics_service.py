"""
Metrics service for orchestrating metric collection and storage.
Implements Facade pattern to provide simplified interface.
Supports multiple data sources and aggregation queries.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from elasticsearch import Elasticsearch

from ..collectors import BaseCollector, IndexStatsCollector
from ..collectors.aggregation_collector import AggregationCollector
from ..repositories import MySQLRepository
from ..repositories.aggregation_repository import AggregationRepository
from ..models import IndexMetrics
from ..models.aggregation_metric import AggregationQueryConfig, load_query_configs
from ..utils import ConfigLoader
from .data_source_manager import DataSourceManager, get_data_source_manager


class MetricsService:
    """
    Service class orchestrating metric collection and persistence.
    Implements Facade pattern - provides simplified interface to complex subsystem.

    Supports:
    - Multiple data sources (ES clusters via direct or proxy connections)
    - Index statistics collection (existing functionality)
    - Aggregation query collection (new functionality)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize metrics service.

        Args:
            config: Configuration dictionary (loads from file if not provided)
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        if config is None:
            config_loader = ConfigLoader()
            config = config_loader.load_config()

        self.config = config

        # Initialize data source manager for multi-cluster support
        self.data_source_manager = get_data_source_manager()
        self._initialize_data_sources()

        # Legacy single client for backward compatibility
        self.es_client = self._get_default_client()

        # Repositories
        self.repository = MySQLRepository(config['mysql'])
        self.aggregation_repository = AggregationRepository(config['mysql'])

        # Legacy collector for backward compatibility
        self.collector = self._create_collector()

        self.logger.info("MetricsService initialized successfully")

    def _initialize_data_sources(self):
        """Initialize data sources from configuration."""
        try:
            self.data_source_manager.initialize(self.config)
        except Exception as e:
            self.logger.error(f"Failed to initialize data sources: {e}")
            raise

    def _get_default_client(self) -> Elasticsearch:
        """
        Get default ES client for backward compatibility.
        Returns the first available client or creates one from legacy config.
        """
        try:
            return self.data_source_manager.get_client()
        except Exception:
            # Fallback to legacy client creation
            return self._create_es_client_legacy()

    def _create_es_client_legacy(self) -> Elasticsearch:
        """
        Create ES client from legacy 'elasticsearch' config section.
        For backward compatibility.
        """
        es_config = self.config.get('elasticsearch', {})

        connection_params = {
            'hosts': es_config.get('hosts', ['http://localhost:9200']),
            'timeout': es_config.get('timeout', 30),
            'verify_certs': es_config.get('verify_certs', False),
        }

        if 'username' in es_config and 'password' in es_config:
            connection_params['basic_auth'] = (
                es_config['username'],
                es_config['password']
            )
        elif 'api_key' in es_config:
            connection_params['api_key'] = es_config['api_key']

        try:
            client = Elasticsearch(**connection_params)
            self.logger.info("Elasticsearch client created (legacy mode)")
            return client
        except Exception as e:
            self.logger.error(f"Failed to create Elasticsearch client: {e}")
            raise

    def _create_collector(self, source_name: str = None) -> BaseCollector:
        """
        Create appropriate collector based on configuration.
        Factory method for collector creation.

        Args:
            source_name: Optional data source name. If None, uses default.

        Returns:
            Collector instance
        """
        if source_name:
            client = self.data_source_manager.get_client(source_name)
        else:
            client = self.es_client

        return IndexStatsCollector(client, self.config)

    # =========================================================================
    # INDEX METRICS COLLECTION (existing functionality, enhanced)
    # =========================================================================

    def collect_and_store_metrics(
        self,
        source_name: str = None
    ) -> Dict[str, Any]:
        """
        Main orchestration method: collect index metrics and store in database.
        Can collect from a specific source or all configured sources.

        Args:
            source_name: Optional specific data source to collect from.
                        If None, collects from all sources in index_metrics.sources
                        or falls back to default/legacy behavior.

        Returns:
            Dictionary with execution results and statistics
        """
        start_time = datetime.utcnow()
        self.logger.info("=" * 60)
        self.logger.info("Starting index metrics collection and storage process")
        self.logger.info("=" * 60)

        result = {
            'success': False,
            'start_time': start_time.isoformat(),
            'end_time': None,
            'duration_seconds': 0,
            'metrics_collected': 0,
            'metrics_stored': 0,
            'sources_processed': [],
            'errors': []
        }

        try:
            # Determine which sources to collect from
            sources = self._get_index_metrics_sources(source_name)
            self.logger.info(f"Collecting index metrics from sources: {sources}")

            total_collected = 0
            total_stored = 0

            for src in sources:
                try:
                    self.logger.info(f"Processing source: {src}")
                    collector = self._create_collector(src)

                    # Validate connection
                    if not collector.validate_connection():
                        self.logger.error(f"Connection failed for source: {src}")
                        result['errors'].append(f"Connection failed for {src}")
                        continue

                    # Collect metrics
                    metrics = collector.collect()
                    total_collected += len(metrics)

                    if metrics:
                        stored = self.repository.save_metrics_batch(metrics)
                        total_stored += stored

                    result['sources_processed'].append({
                        'source': src,
                        'collected': len(metrics),
                        'stored': len(metrics) if metrics else 0
                    })

                except Exception as e:
                    self.logger.error(f"Error processing source '{src}': {e}")
                    result['errors'].append(f"{src}: {str(e)}")

            result['metrics_collected'] = total_collected
            result['metrics_stored'] = total_stored
            result['success'] = len(result['errors']) == 0

            if result['success']:
                self.logger.info("✓ Index metrics collection completed successfully")
            else:
                self.logger.warning(f"Index metrics collection completed with {len(result['errors'])} error(s)")

        except Exception as e:
            self.logger.error(f"✗ Failed to collect index metrics: {e}", exc_info=True)
            result['errors'].append(str(e))

        finally:
            end_time = datetime.utcnow()
            result['end_time'] = end_time.isoformat()
            result['duration_seconds'] = (end_time - start_time).total_seconds()
            self._log_summary(result, "Index Metrics")

        return result

    def _get_index_metrics_sources(self, source_name: str = None) -> List[str]:
        """Get list of data sources to collect index metrics from."""
        if source_name:
            return [source_name]

        # Check config for index_metrics.sources
        index_metrics_config = self.config.get('index_metrics', {})
        configured_sources = index_metrics_config.get('sources', [])

        if configured_sources:
            return configured_sources

        # Fallback to all available sources
        available = self.data_source_manager.list_sources()
        if available:
            return available

        # Ultimate fallback - use legacy default
        return ['default']

    # =========================================================================
    # AGGREGATION METRICS COLLECTION (new functionality)
    # =========================================================================

    def collect_and_store_aggregations(
        self,
        source_name: str = None,
        query_name: str = None
    ) -> Dict[str, Any]:
        """
        Collect aggregation metrics and store in database.

        Args:
            source_name: Optional specific data source to collect from.
                        If None, processes queries for all sources.
            query_name: Optional specific query to run.
                       If None, runs all configured queries.

        Returns:
            Dictionary with execution results and statistics
        """
        start_time = datetime.utcnow()
        self.logger.info("=" * 60)
        self.logger.info("Starting aggregation metrics collection")
        self.logger.info("=" * 60)

        result = {
            'success': False,
            'start_time': start_time.isoformat(),
            'end_time': None,
            'duration_seconds': 0,
            'queries_executed': 0,
            'metrics_collected': 0,
            'metrics_stored': 0,
            'query_results': [],
            'errors': []
        }

        try:
            # Load query configurations
            query_configs = load_query_configs(self.config)

            if not query_configs:
                self.logger.warning("No aggregation queries configured")
                result['success'] = True
                return result

            # Filter by query name if specified
            if query_name:
                query_configs = [q for q in query_configs if q.name == query_name]
                if not query_configs:
                    raise ValueError(f"Query '{query_name}' not found in configuration")

            # Filter by source if specified
            if source_name:
                query_configs = [q for q in query_configs if q.data_source == source_name]

            self.logger.info(f"Processing {len(query_configs)} aggregation query(ies)")

            # Group queries by data source
            queries_by_source: Dict[str, List[AggregationQueryConfig]] = {}
            for qc in query_configs:
                if qc.data_source not in queries_by_source:
                    queries_by_source[qc.data_source] = []
                queries_by_source[qc.data_source].append(qc)

            total_metrics = 0

            # Process each data source
            for src, queries in queries_by_source.items():
                try:
                    self.logger.info(f"Processing {len(queries)} queries for source: {src}")

                    client = self.data_source_manager.get_client(src)
                    path_prefix = self.data_source_manager.get_path_prefix(src)
                    collector = AggregationCollector(client, src, path_prefix=path_prefix)

                    # Execute queries
                    metrics = collector.collect(queries)
                    total_metrics += len(metrics)

                    # Store metrics
                    if metrics:
                        self.aggregation_repository.save_metrics_batch(metrics)

                    # Track results per query
                    for query in queries:
                        query_metrics = [m for m in metrics if m.metric_name.startswith(query.name)]
                        result['query_results'].append({
                            'query': query.name,
                            'source': src,
                            'metrics_count': len(query_metrics)
                        })
                        result['queries_executed'] += 1

                except KeyError as e:
                    self.logger.error(f"Data source '{src}' not found: {e}")
                    result['errors'].append(f"Source not found: {src}")
                except Exception as e:
                    self.logger.error(f"Error processing source '{src}': {e}", exc_info=True)
                    result['errors'].append(f"{src}: {str(e)}")

            result['metrics_collected'] = total_metrics
            result['metrics_stored'] = total_metrics
            result['success'] = len(result['errors']) == 0

            if result['success']:
                self.logger.info("✓ Aggregation metrics collection completed successfully")
            else:
                self.logger.warning(f"Aggregation collection completed with {len(result['errors'])} error(s)")

        except Exception as e:
            self.logger.error(f"✗ Failed to collect aggregation metrics: {e}", exc_info=True)
            result['errors'].append(str(e))

        finally:
            end_time = datetime.utcnow()
            result['end_time'] = end_time.isoformat()
            result['duration_seconds'] = (end_time - start_time).total_seconds()
            self._log_summary(result, "Aggregation Metrics")

        return result

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _log_summary(self, result: Dict[str, Any], operation: str):
        """Log execution summary."""
        self.logger.info("=" * 60)
        self.logger.info(f"{operation} - Execution Summary:")
        self.logger.info(f"  Status: {'SUCCESS' if result['success'] else 'FAILED'}")
        self.logger.info(f"  Duration: {result['duration_seconds']:.2f} seconds")
        self.logger.info(f"  Metrics collected: {result.get('metrics_collected', 0)}")
        self.logger.info(f"  Metrics stored: {result.get('metrics_stored', 0)}")
        if result.get('errors'):
            self.logger.info(f"  Errors: {len(result['errors'])}")
        self.logger.info("=" * 60)

    def _test_connections(self) -> bool:
        """
        Test connections to Elasticsearch and MySQL.

        Returns:
            True if all connections successful, False otherwise
        """
        es_ok = self.collector.validate_connection()
        mysql_ok = self.repository.test_connection()

        if es_ok and mysql_ok:
            self.logger.info("✓ All connections tested successfully")
            return True
        else:
            if not es_ok:
                self.logger.error("✗ Elasticsearch connection failed")
            if not mysql_ok:
                self.logger.error("✗ MySQL connection failed")
            return False

    def get_latest_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get latest index metrics from database."""
        try:
            return self.repository.get_latest_metrics(limit)
        except Exception as e:
            self.logger.error(f"Failed to get latest metrics: {e}")
            raise

    def get_latest_aggregation_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get latest aggregation metrics from database."""
        try:
            return self.aggregation_repository.get_latest_metrics(limit)
        except Exception as e:
            self.logger.error(f"Failed to get latest aggregation metrics: {e}")
            raise

    def get_metrics_for_index(
        self,
        index_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get metrics for a specific index."""
        try:
            return self.repository.get_metrics_by_index(
                index_name, start_date, end_date
            )
        except Exception as e:
            self.logger.error(f"Failed to get metrics for index '{index_name}': {e}")
            raise

    def get_indices_summary(self) -> List[Dict[str, Any]]:
        """Get summary statistics for all indices."""
        try:
            return self.repository.get_indices_summary()
        except Exception as e:
            self.logger.error(f"Failed to get indices summary: {e}")
            raise

    def collect_detailed_stats_for_index(self, index_name: str) -> IndexMetrics:
        """Collect detailed statistics for a specific index."""
        try:
            return self.collector.collect_detailed_stats(index_name)
        except Exception as e:
            self.logger.error(f"Failed to collect detailed stats for '{index_name}': {e}")
            raise

    def cleanup_old_data(self, days: int = 90) -> Dict[str, int]:
        """
        Clean up old metrics data from both tables.

        Args:
            days: Number of days to keep (delete older records)

        Returns:
            Dictionary with deleted counts per table
        """
        result = {
            'index_metrics_deleted': 0,
            'aggregation_metrics_deleted': 0
        }

        try:
            self.logger.info(f"Cleaning up metrics older than {days} days...")

            result['index_metrics_deleted'] = self.repository.delete_old_metrics(days)
            result['aggregation_metrics_deleted'] = self.aggregation_repository.delete_old_metrics(days)

            total = result['index_metrics_deleted'] + result['aggregation_metrics_deleted']
            self.logger.info(f"Cleaned up {total} total old records")

            return result
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all components.

        Returns:
            Dictionary with health status of components
        """
        health = {
            'overall': 'healthy',
            'data_sources': {},
            'mysql': {'status': 'unknown', 'details': {}},
            'timestamp': datetime.utcnow().isoformat()
        }

        # Check all data sources
        try:
            source_health = self.data_source_manager.health_check()
            health['data_sources'] = source_health

            # Check if any source is unhealthy
            for name, status in source_health.items():
                if status.get('status') != 'healthy':
                    health['overall'] = 'unhealthy'
        except Exception as e:
            health['data_sources'] = {'error': str(e)}
            health['overall'] = 'unhealthy'

        # Legacy elasticsearch key for backward compatibility
        if health['data_sources']:
            first_source = list(health['data_sources'].values())[0]
            health['elasticsearch'] = first_source

        # Check MySQL
        try:
            if self.repository.test_connection():
                health['mysql'] = {
                    'status': 'healthy',
                    'details': {
                        'host': self.config['mysql']['host'],
                        'database': self.config['mysql']['database']
                    }
                }
            else:
                health['mysql'] = {'status': 'unhealthy', 'error': 'Connection test failed'}
                health['overall'] = 'unhealthy'
        except Exception as e:
            health['mysql'] = {'status': 'unhealthy', 'error': str(e)}
            health['overall'] = 'unhealthy'

        return health

    def list_data_sources(self) -> List[str]:
        """List all available data sources."""
        return self.data_source_manager.list_sources()

    def list_aggregation_queries(self) -> List[Dict[str, Any]]:
        """List all configured aggregation queries."""
        query_configs = load_query_configs(self.config)
        return [q.to_dict() for q in query_configs]
