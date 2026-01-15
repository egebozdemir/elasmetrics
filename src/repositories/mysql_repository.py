"""
MySQL repository for persisting index metrics.
Implements Repository pattern for data access abstraction.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager

from ..models import IndexMetrics


class MySQLRepository:
    """
    Repository class for MySQL database operations.
    Implements Repository pattern - abstracts data persistence logic.
    Uses connection pooling for efficient database access.
    """
    
    # SQL queries as class constants
    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS index_metrics (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        index_name VARCHAR(255) NOT NULL,
        timestamp DATETIME NOT NULL,
        docs_count BIGINT,
        docs_deleted BIGINT,
        store_size_bytes BIGINT,
        pri_store_size_bytes BIGINT,
        store_size_human VARCHAR(50),
        pri_store_size_human VARCHAR(50),
        status VARCHAR(20),
        health VARCHAR(20),
        pri_shards INT,
        replicas INT,
        creation_date VARCHAR(50),
        uuid VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_index_name (index_name),
        INDEX idx_timestamp (timestamp),
        INDEX idx_created_at (created_at),
        INDEX idx_index_timestamp (index_name, timestamp)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
    
    # Create VIEW for latest metrics (fast current state queries)
    CREATE_LATEST_VIEW_SQL = """
    CREATE OR REPLACE VIEW index_metrics_latest AS
    SELECT im.*
    FROM index_metrics im
    INNER JOIN (
        SELECT index_name, MAX(timestamp) as max_timestamp
        FROM index_metrics
        GROUP BY index_name
    ) latest ON im.index_name = latest.index_name 
              AND im.timestamp = latest.max_timestamp
    """
    
    INSERT_METRIC_SQL = """
    INSERT INTO index_metrics (
        index_name, timestamp, docs_count, docs_deleted,
        store_size_bytes, pri_store_size_bytes,
        store_size_human, pri_store_size_human,
        status, health, pri_shards, replicas,
        creation_date, uuid
    ) VALUES (
        %(index_name)s, %(timestamp)s, %(docs_count)s, %(docs_deleted)s,
        %(store_size_bytes)s, %(pri_store_size_bytes)s,
        %(store_size_human)s, %(pri_store_size_human)s,
        %(status)s, %(health)s, %(pri_shards)s, %(replicas)s,
        %(creation_date)s, %(uuid)s
    )
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MySQL repository.
        
        Args:
            config: MySQL configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._connection_params = self._build_connection_params()
        self._ensure_database_exists()
        self._ensure_table_exists()
    
    def _build_connection_params(self) -> Dict[str, Any]:
        """
        Build connection parameters from config.
        
        Returns:
            Dictionary with connection parameters
        """
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
    def _get_connection(self, use_database: bool = True):
        """
        Context manager for database connections.
        Ensures proper connection handling and cleanup.
        
        Args:
            use_database: Whether to select database in connection
            
        Yields:
            pymysql.Connection object
        """
        params = self._connection_params.copy()
        if not use_database:
            params.pop('database', None)
        
        connection = None
        try:
            connection = pymysql.connect(**params)
            yield connection
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def _ensure_database_exists(self):
        """
        Ensure the database exists, create if it doesn't.
        """
        database_name = self.config.get('database')
        
        try:
            with self._get_connection(use_database=False) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"CREATE DATABASE IF NOT EXISTS {database_name} "
                        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                    conn.commit()
                    self.logger.info(f"Database '{database_name}' is ready")
        except Exception as e:
            self.logger.error(f"Failed to ensure database exists: {e}")
            raise
    
    def _ensure_table_exists(self):
        """
        Ensure the metrics table exists, create if it doesn't.
        Also creates the 'latest' view for fast current-state queries.
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Create main table
                    cursor.execute(self.CREATE_TABLE_SQL)
                    self.logger.info("Table 'index_metrics' is ready")
                    
                    # Create view for latest metrics (fast current-state queries)
                    cursor.execute(self.CREATE_LATEST_VIEW_SQL)
                    self.logger.info("View 'index_metrics_latest' is ready")
                    
                    conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to ensure table exists: {e}")
            raise
    
    def save_metric(self, metric: IndexMetrics) -> int:
        """
        Save a single metric to database.
        
        Args:
            metric: IndexMetrics object to save
            
        Returns:
            ID of inserted record
            
        Raises:
            Exception: If save operation fails
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    data = metric.to_db_dict()
                    cursor.execute(self.INSERT_METRIC_SQL, data)
                    conn.commit()
                    record_id = cursor.lastrowid
                    self.logger.debug(f"Saved metric for index '{metric.index_name}' with ID {record_id}")
                    return record_id
        except Exception as e:
            self.logger.error(f"Failed to save metric for index '{metric.index_name}': {e}")
            raise
    
    def save_metrics_batch(self, metrics: List[IndexMetrics]) -> int:
        """
        Save multiple metrics in a batch for better performance.
        Uses transaction to ensure atomicity.
        
        Args:
            metrics: List of IndexMetrics objects to save
            
        Returns:
            Number of records inserted
            
        Raises:
            Exception: If batch save operation fails
        """
        if not metrics:
            self.logger.warning("No metrics to save")
            return 0
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Prepare batch data
                    batch_data = [metric.to_db_dict() for metric in metrics]
                    
                    # Execute batch insert
                    rows_affected = cursor.executemany(self.INSERT_METRIC_SQL, batch_data)
                    conn.commit()
                    
                    self.logger.info(f"Successfully saved {len(metrics)} metrics to database")
                    return rows_affected
                    
        except Exception as e:
            self.logger.error(f"Failed to save metrics batch: {e}", exc_info=True)
            raise
    
    def get_latest_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get latest metrics from database (most recent collection runs).
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of metric dictionaries ordered by timestamp
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    SELECT * FROM index_metrics
                    ORDER BY timestamp DESC, created_at DESC
                    LIMIT %s
                    """
                    cursor.execute(sql, (limit,))
                    results = cursor.fetchall()
                    return results
        except Exception as e:
            self.logger.error(f"Failed to get latest metrics: {e}")
            raise
    
    def get_current_state(self) -> List[Dict[str, Any]]:
        """
        Get current state of all indices (latest metrics per index).
        Uses the index_metrics_latest VIEW for optimal performance.
        
        This is perfect for:
        - Current cluster overview dashboards
        - Real-time monitoring
        - Alerting on current values
        - Quick status checks
        
        Returns:
            List of latest metrics (one per index)
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    SELECT * FROM index_metrics_latest
                    ORDER BY index_name
                    """
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    return results
        except Exception as e:
            self.logger.error(f"Failed to get current state: {e}")
            raise
    
    def get_metrics_by_index(
        self,
        index_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get metrics for a specific index within a date range.
        
        Args:
            index_name: Name of the index
            start_date: Start date for filtering (inclusive)
            end_date: End date for filtering (inclusive)
            
        Returns:
            List of metric dictionaries
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = "SELECT * FROM index_metrics WHERE index_name = %s"
                    params = [index_name]
                    
                    if start_date:
                        sql += " AND timestamp >= %s"
                        params.append(start_date)
                    
                    if end_date:
                        sql += " AND timestamp <= %s"
                        params.append(end_date)
                    
                    sql += " ORDER BY timestamp DESC"
                    
                    cursor.execute(sql, params)
                    results = cursor.fetchall()
                    return results
        except Exception as e:
            self.logger.error(f"Failed to get metrics for index '{index_name}': {e}")
            raise
    
    def get_indices_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary statistics for all indices.
        
        Returns:
            List of summary dictionaries with latest metrics per index
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    SELECT 
                        index_name,
                        MAX(timestamp) as latest_timestamp,
                        COUNT(*) as total_records,
                        AVG(docs_count) as avg_docs,
                        AVG(store_size_bytes) as avg_size
                    FROM index_metrics
                    GROUP BY index_name
                    ORDER BY latest_timestamp DESC
                    """
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    return results
        except Exception as e:
            self.logger.error(f"Failed to get indices summary: {e}")
            raise
    
    def delete_old_metrics(self, days: int = 90) -> int:
        """
        Delete metrics older than specified days.
        Useful for data retention management.
        
        Args:
            days: Number of days to keep (delete older records)
            
        Returns:
            Number of deleted records
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    DELETE FROM index_metrics
                    WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)
                    """
                    cursor.execute(sql, (days,))
                    conn.commit()
                    deleted_count = cursor.rowcount
                    self.logger.info(f"Deleted {deleted_count} old metrics (older than {days} days)")
                    return deleted_count
        except Exception as e:
            self.logger.error(f"Failed to delete old metrics: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    if result:
                        self.logger.info("MySQL connection test successful")
                        return True
            return False
        except Exception as e:
            self.logger.error(f"MySQL connection test failed: {e}")
            return False

