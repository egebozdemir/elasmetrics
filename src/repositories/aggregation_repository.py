"""
Repository for aggregation metrics persistence.
Handles storage and retrieval of custom aggregation query results.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager

from ..models.aggregation_metric import AggregationMetric


class AggregationRepository:
    """
    Repository for storing and querying aggregation metrics.
    Uses a dedicated table optimized for time-series data with dimensions.
    """

    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS aggregation_metrics (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        -- Identification
        metric_name VARCHAR(255) NOT NULL,
        data_source VARCHAR(100) NOT NULL,
        index_pattern VARCHAR(255),

        -- Timestamp
        timestamp DATETIME NOT NULL,
        time_range_start DATETIME,
        time_range_end DATETIME,

        -- Values (flexible storage)
        value_numeric DOUBLE,
        value_string VARCHAR(1000),

        -- Dimensions (for grouping/filtering - supports up to 3)
        dimension_1_name VARCHAR(100),
        dimension_1_value VARCHAR(255),
        dimension_2_name VARCHAR(100),
        dimension_2_value VARCHAR(255),
        dimension_3_name VARCHAR(100),
        dimension_3_value VARCHAR(255),

        -- Complex results
        result_json JSON,

        -- Metadata
        query_duration_ms INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        -- Indexes for efficient querying (especially for Grafana)
        INDEX idx_metric_name (metric_name),
        INDEX idx_data_source (data_source),
        INDEX idx_timestamp (timestamp),
        INDEX idx_metric_source_time (metric_name, data_source, timestamp),
        INDEX idx_metric_time (metric_name, timestamp),
        INDEX idx_dimension_1 (dimension_1_name, dimension_1_value),
        INDEX idx_dimension_2 (dimension_2_name, dimension_2_value),
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """

    CREATE_LATEST_VIEW_SQL = """
    CREATE OR REPLACE VIEW aggregation_metrics_latest AS
    SELECT am.*
    FROM aggregation_metrics am
    INNER JOIN (
        SELECT
            metric_name,
            data_source,
            COALESCE(dimension_1_name, '') as d1n,
            COALESCE(dimension_1_value, '') as d1v,
            COALESCE(dimension_2_name, '') as d2n,
            COALESCE(dimension_2_value, '') as d2v,
            MAX(timestamp) as max_timestamp
        FROM aggregation_metrics
        GROUP BY
            metric_name,
            data_source,
            COALESCE(dimension_1_name, ''),
            COALESCE(dimension_1_value, ''),
            COALESCE(dimension_2_name, ''),
            COALESCE(dimension_2_value, '')
    ) latest ON am.metric_name = latest.metric_name
              AND am.data_source = latest.data_source
              AND am.timestamp = latest.max_timestamp
              AND COALESCE(am.dimension_1_name, '') = latest.d1n
              AND COALESCE(am.dimension_1_value, '') = latest.d1v
              AND COALESCE(am.dimension_2_name, '') = latest.d2n
              AND COALESCE(am.dimension_2_value, '') = latest.d2v
    """

    INSERT_SQL = """
    INSERT INTO aggregation_metrics (
        metric_name, data_source, index_pattern, timestamp,
        time_range_start, time_range_end,
        value_numeric, value_string,
        dimension_1_name, dimension_1_value,
        dimension_2_name, dimension_2_value,
        dimension_3_name, dimension_3_value,
        result_json, query_duration_ms
    ) VALUES (
        %(metric_name)s, %(data_source)s, %(index_pattern)s, %(timestamp)s,
        %(time_range_start)s, %(time_range_end)s,
        %(value_numeric)s, %(value_string)s,
        %(dimension_1_name)s, %(dimension_1_value)s,
        %(dimension_2_name)s, %(dimension_2_value)s,
        %(dimension_3_name)s, %(dimension_3_value)s,
        %(result_json)s, %(query_duration_ms)s
    )
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize repository with MySQL config.

        Args:
            config: MySQL configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._connection_params = self._build_connection_params()
        self._ensure_database_exists()
        self._ensure_table_exists()

    def _build_connection_params(self) -> Dict[str, Any]:
        """Build connection parameters from config."""
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
        finally:
            if connection:
                connection.close()

    def _ensure_database_exists(self):
        """Ensure the database exists, create if it doesn't."""
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
        """Ensure the aggregation_metrics table and view exist."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(self.CREATE_TABLE_SQL)
                    self.logger.info("Table 'aggregation_metrics' is ready")

                    cursor.execute(self.CREATE_LATEST_VIEW_SQL)
                    self.logger.info("View 'aggregation_metrics_latest' is ready")

                    conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to ensure table exists: {e}")
            raise

    def save_metric(self, metric: AggregationMetric) -> int:
        """
        Save a single metric to database.

        Args:
            metric: AggregationMetric object to save

        Returns:
            ID of inserted record
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    data = metric.to_db_dict()
                    cursor.execute(self.INSERT_SQL, data)
                    conn.commit()
                    record_id = cursor.lastrowid
                    self.logger.debug(f"Saved metric '{metric.metric_name}' with ID {record_id}")
                    return record_id
        except Exception as e:
            self.logger.error(f"Failed to save metric '{metric.metric_name}': {e}")
            raise

    def save_metrics_batch(self, metrics: List[AggregationMetric]) -> int:
        """
        Save multiple metrics in a batch for better performance.

        Args:
            metrics: List of AggregationMetric objects

        Returns:
            Number of records inserted
        """
        if not metrics:
            self.logger.warning("No metrics to save")
            return 0

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    batch_data = [m.to_db_dict() for m in metrics]
                    cursor.executemany(self.INSERT_SQL, batch_data)
                    conn.commit()

                    self.logger.info(f"Saved {len(metrics)} aggregation metrics to database")
                    return len(metrics)
        except Exception as e:
            self.logger.error(f"Failed to save metrics batch: {e}")
            raise

    def get_latest_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get latest metrics from database.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of metric dictionaries
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    SELECT * FROM aggregation_metrics
                    ORDER BY timestamp DESC, created_at DESC
                    LIMIT %s
                    """
                    cursor.execute(sql, (limit,))
                    return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Failed to get latest metrics: {e}")
            raise

    def get_current_state(self) -> List[Dict[str, Any]]:
        """
        Get current state (latest value per metric/dimension combination).
        Uses the aggregation_metrics_latest VIEW.

        Returns:
            List of latest metrics
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    SELECT * FROM aggregation_metrics_latest
                    ORDER BY metric_name, data_source
                    """
                    cursor.execute(sql)
                    return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Failed to get current state: {e}")
            raise

    def get_metrics_by_name(
        self,
        metric_name: str,
        data_source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Query metrics by name with optional filters.

        Args:
            metric_name: Name of the metric
            data_source: Optional data source filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum records to return

        Returns:
            List of metric dictionaries
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = "SELECT * FROM aggregation_metrics WHERE metric_name = %s"
                    params = [metric_name]

                    if data_source:
                        sql += " AND data_source = %s"
                        params.append(data_source)

                    if start_date:
                        sql += " AND timestamp >= %s"
                        params.append(start_date)

                    if end_date:
                        sql += " AND timestamp <= %s"
                        params.append(end_date)

                    sql += " ORDER BY timestamp DESC LIMIT %s"
                    params.append(limit)

                    cursor.execute(sql, params)
                    return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Failed to get metrics by name: {e}")
            raise

    def get_metrics_by_dimension(
        self,
        dimension_name: str,
        dimension_value: Optional[str] = None,
        metric_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Query metrics by dimension value.

        Args:
            dimension_name: Name of the dimension to filter by
            dimension_value: Optional specific value to filter
            metric_name: Optional metric name filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum records to return

        Returns:
            List of metric dictionaries
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Search across all dimension columns
                    sql = """
                    SELECT * FROM aggregation_metrics
                    WHERE (
                        dimension_1_name = %s OR
                        dimension_2_name = %s OR
                        dimension_3_name = %s
                    )
                    """
                    params = [dimension_name, dimension_name, dimension_name]

                    if dimension_value:
                        sql += """ AND (
                            (dimension_1_name = %s AND dimension_1_value = %s) OR
                            (dimension_2_name = %s AND dimension_2_value = %s) OR
                            (dimension_3_name = %s AND dimension_3_value = %s)
                        )"""
                        params.extend([
                            dimension_name, dimension_value,
                            dimension_name, dimension_value,
                            dimension_name, dimension_value
                        ])

                    if metric_name:
                        sql += " AND metric_name = %s"
                        params.append(metric_name)

                    if start_date:
                        sql += " AND timestamp >= %s"
                        params.append(start_date)

                    if end_date:
                        sql += " AND timestamp <= %s"
                        params.append(end_date)

                    sql += " ORDER BY timestamp DESC LIMIT %s"
                    params.append(limit)

                    cursor.execute(sql, params)
                    return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Failed to get metrics by dimension: {e}")
            raise

    def get_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary of all metrics (count, latest timestamp per metric).

        Returns:
            List of summary dictionaries
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    SELECT
                        metric_name,
                        data_source,
                        COUNT(*) as total_records,
                        MIN(timestamp) as first_recorded,
                        MAX(timestamp) as last_recorded,
                        AVG(value_numeric) as avg_value,
                        MIN(value_numeric) as min_value,
                        MAX(value_numeric) as max_value
                    FROM aggregation_metrics
                    GROUP BY metric_name, data_source
                    ORDER BY metric_name, data_source
                    """
                    cursor.execute(sql)
                    return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Failed to get summary: {e}")
            raise

    def delete_old_metrics(self, days: int = 90) -> int:
        """
        Delete metrics older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of deleted records
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    DELETE FROM aggregation_metrics
                    WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)
                    """
                    cursor.execute(sql, (days,))
                    conn.commit()
                    deleted = cursor.rowcount
                    self.logger.info(f"Deleted {deleted} old aggregation metrics (older than {days} days)")
                    return deleted
        except Exception as e:
            self.logger.error(f"Failed to delete old metrics: {e}")
            raise

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection successful
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    if result:
                        self.logger.info("Aggregation repository connection test successful")
                        return True
            return False
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
