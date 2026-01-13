"""
Metrics service for orchestrating metric collection and storage.
Implements Facade pattern to provide simplified interface.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from elasticsearch import Elasticsearch

from ..collectors import BaseCollector, IndexStatsCollector
from ..repositories import MySQLRepository
from ..models import IndexMetrics
from ..utils import ConfigLoader


class MetricsService:
    """
    Service class orchestrating metric collection and persistence.
    Implements Facade pattern - provides simplified interface to complex subsystem.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize metrics service.
        
        Args:
            config: Configuration dictionary (loads from file if not provided)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Load configuration
        if config is None:
            config_loader = ConfigLoader()
            config = config_loader.load_config()
        
        self.config = config
        
        # Initialize components
        self.es_client = self._create_es_client()
        self.repository = MySQLRepository(config['mysql'])
        self.collector = self._create_collector()
        
        self.logger.info("MetricsService initialized successfully")
    
    def _create_es_client(self) -> Elasticsearch:
        """
        Create and configure Elasticsearch client.
        
        Returns:
            Configured Elasticsearch client
        """
        es_config = self.config['elasticsearch']
        
        # Build connection parameters
        connection_params = {
            'hosts': es_config.get('hosts', ['http://localhost:9200']),
            'timeout': es_config.get('timeout', 30),
            'verify_certs': es_config.get('verify_certs', False),
        }
        
        # Add authentication if provided
        if 'username' in es_config and 'password' in es_config:
            connection_params['basic_auth'] = (
                es_config['username'],
                es_config['password']
            )
        elif 'api_key' in es_config:
            connection_params['api_key'] = es_config['api_key']
        
        try:
            client = Elasticsearch(**connection_params)
            self.logger.info("Elasticsearch client created successfully")
            return client
        except Exception as e:
            self.logger.error(f"Failed to create Elasticsearch client: {e}")
            raise
    
    def _create_collector(self) -> BaseCollector:
        """
        Create appropriate collector based on configuration.
        Factory method for collector creation.
        
        Returns:
            Collector instance
        """
        # Currently only IndexStatsCollector, but can be extended
        # to support different collector types based on config
        return IndexStatsCollector(self.es_client, self.config)
    
    def collect_and_store_metrics(self) -> Dict[str, Any]:
        """
        Main orchestration method: collect metrics and store in database.
        
        Returns:
            Dictionary with execution results and statistics
        """
        start_time = datetime.utcnow()
        self.logger.info("=" * 60)
        self.logger.info("Starting metrics collection and storage process")
        self.logger.info("=" * 60)
        
        result = {
            'success': False,
            'start_time': start_time.isoformat(),
            'end_time': None,
            'duration_seconds': 0,
            'metrics_collected': 0,
            'metrics_stored': 0,
            'errors': []
        }
        
        try:
            # Step 1: Test connections
            self.logger.info("Step 1: Testing connections...")
            if not self._test_connections():
                raise ConnectionError("Connection tests failed")
            
            # Step 2: Collect metrics from Elasticsearch
            self.logger.info("Step 2: Collecting metrics from Elasticsearch...")
            metrics = self.collector.collect()
            result['metrics_collected'] = len(metrics)
            
            if not metrics:
                self.logger.warning("No metrics collected")
                result['success'] = True
                return result
            
            # Step 3: Store metrics in MySQL
            self.logger.info(f"Step 3: Storing {len(metrics)} metrics in MySQL...")
            stored_count = self.repository.save_metrics_batch(metrics)
            result['metrics_stored'] = stored_count
            
            # Step 4: Success
            result['success'] = True
            self.logger.info("✓ Metrics collection and storage completed successfully")
            
        except Exception as e:
            self.logger.error(f"✗ Failed to collect and store metrics: {e}", exc_info=True)
            result['errors'].append(str(e))
        
        finally:
            end_time = datetime.utcnow()
            result['end_time'] = end_time.isoformat()
            result['duration_seconds'] = (end_time - start_time).total_seconds()
            
            # Log summary
            self.logger.info("=" * 60)
            self.logger.info("Execution Summary:")
            self.logger.info(f"  Status: {'SUCCESS' if result['success'] else 'FAILED'}")
            self.logger.info(f"  Duration: {result['duration_seconds']:.2f} seconds")
            self.logger.info(f"  Metrics collected: {result['metrics_collected']}")
            self.logger.info(f"  Metrics stored: {result['metrics_stored']}")
            if result['errors']:
                self.logger.info(f"  Errors: {len(result['errors'])}")
            self.logger.info("=" * 60)
        
        return result
    
    def _test_connections(self) -> bool:
        """
        Test connections to Elasticsearch and MySQL.
        
        Returns:
            True if both connections successful, False otherwise
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
        """
        Get latest metrics from database.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of metric dictionaries
        """
        try:
            return self.repository.get_latest_metrics(limit)
        except Exception as e:
            self.logger.error(f"Failed to get latest metrics: {e}")
            raise
    
    def get_metrics_for_index(
        self,
        index_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get metrics for a specific index.
        
        Args:
            index_name: Name of the index
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            List of metric dictionaries
        """
        try:
            return self.repository.get_metrics_by_index(
                index_name, start_date, end_date
            )
        except Exception as e:
            self.logger.error(f"Failed to get metrics for index '{index_name}': {e}")
            raise
    
    def get_indices_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary statistics for all indices.
        
        Returns:
            List of summary dictionaries
        """
        try:
            return self.repository.get_indices_summary()
        except Exception as e:
            self.logger.error(f"Failed to get indices summary: {e}")
            raise
    
    def collect_detailed_stats_for_index(self, index_name: str) -> IndexMetrics:
        """
        Collect detailed statistics for a specific index.
        
        Args:
            index_name: Name of the index
            
        Returns:
            IndexMetrics object with detailed stats
        """
        try:
            return self.collector.collect_detailed_stats(index_name)
        except Exception as e:
            self.logger.error(f"Failed to collect detailed stats for '{index_name}': {e}")
            raise
    
    def cleanup_old_data(self, days: int = 90) -> int:
        """
        Clean up old metrics data.
        
        Args:
            days: Number of days to keep (delete older records)
            
        Returns:
            Number of deleted records
        """
        try:
            self.logger.info(f"Cleaning up metrics older than {days} days...")
            deleted_count = self.repository.delete_old_metrics(days)
            self.logger.info(f"Cleaned up {deleted_count} old records")
            return deleted_count
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
            'elasticsearch': {'status': 'unknown', 'details': {}},
            'mysql': {'status': 'unknown', 'details': {}},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Check Elasticsearch
        try:
            if self.collector.validate_connection():
                info = self.es_client.info()
                health['elasticsearch'] = {
                    'status': 'healthy',
                    'details': {
                        'cluster_name': info.get('cluster_name'),
                        'version': info.get('version', {}).get('number')
                    }
                }
        except Exception as e:
            health['elasticsearch'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health['overall'] = 'unhealthy'
        
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
        except Exception as e:
            health['mysql'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health['overall'] = 'unhealthy'
        
        return health

