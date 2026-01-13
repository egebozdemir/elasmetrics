# Elasticsearch Metrics Collection System

A Python application that regularly collects index-based metrics from Elasticsearch, stores them in MySQL, and enables visualization through Grafana.

## 🆕 New: Universal Generic Metrics System

**Collect ANY Elasticsearch metric without code changes!**

```yaml
# Just add to config - no code changes needed!
metrics:
  collect:
    - docs.count
    - indexing.index_total
    - search.query_total
    - my.custom.plugin.metric  # Even custom metrics!
```

✅ **17+ pre-registered metrics**  
✅ **Type-safe with validation**  
✅ **Works with any ES version**  
✅ **Custom metrics for plugins**  
✅ **Different metrics per environment**  

See [METRICS_GUIDE.md](docs/METRICS_GUIDE.md) for details.

## 🎯 Features

- **Universal Metrics Collection**: Generic metrics system - collect ANY Elasticsearch metric without code changes
- **Type-Safe**: Built-in type validation for metrics (integer, float, string, boolean, timestamp, JSON)
- **Flexible Configuration**: YAML, JSON, and environment-based configuration with multi-environment support
- **Airflow Integration**: Native support for Apache Airflow DAGs with JSON configuration
- **Environment Management**: Separate configurations for staging, production, and local development
- **17+ Pre-registered Metrics**: Common ES metrics ready to use (docs, storage, indexing, search, cache, etc.)
- **Custom Metrics**: Add cluster-specific or plugin metrics via configuration
- **Modular Architecture**: Built using OOP principles and design patterns
- **Scalable**: High performance with batch processing and connection pooling
- **Reliable**: Comprehensive error handling and logging
- **Easy Integration**: Can connect to any Elasticsearch cluster

## 🏗️ Architecture and Design Patterns

### Design Patterns Used

1. **Strategy Pattern** (`collectors/`): For different metric collection strategies
2. **Repository Pattern** (`repositories/`): Abstraction layer for data access
3. **Facade Pattern** (`services/`): Simplified interface for complex operations
4. **Singleton Pattern** (`ConfigLoader`): Single instance configuration management
5. **Factory Method** (`MetricsService._create_collector`): For creating collector instances
6. **Data Transfer Object** (`IndexMetrics`): Data transfer object

### Project Structure

```
elasmetrics/
├── config/
│   ├── config.yaml                    # Main configuration file
│   └── config.generic.example.yaml    # Generic metrics example
├── src/
│   ├── collectors/                    # Metric collection modules
│   │   ├── base_collector.py          # Abstract base class (Strategy Pattern)
│   │   ├── index_stats_collector.py   # Legacy collector (backward compatible)
│   │   └── generic_collector.py       # Generic metrics collector (NEW)
│   ├── repositories/                  # Data access layer
│   │   └── mysql_repository.py        # MySQL operations (Repository Pattern)
│   ├── models/                        # Data models
│   │   ├── index_metrics.py           # IndexMetrics DTO (legacy)
│   │   └── generic_metrics.py         # Generic metrics system (NEW)
│   ├── services/                      # Business logic
│   │   └── metrics_service.py         # Orchestration (Facade Pattern)
│   ├── enums/                         # Enumerations (NEW)
│   │   └── environment.py             # Environment enum
│   └── utils/                         # Utility tools
│       ├── config_loader.py           # Configuration management (Enhanced)
│       └── env_loader.py              # Environment loader (NEW)
├── examples/                          # Example configurations (NEW)
│   ├── config_minimal.yaml
│   ├── config_performance.yaml
│   └── airflow_dag_example.py
├── main.py                            # Main application entry point
├── airflow_runner.py                  # Airflow integration (NEW)
└── README.md                          # This file
```

## 📋 Requirements

- Python 3.8+
- Elasticsearch 7.x or 8.x
- MySQL 5.7+ or MariaDB 10.3+

## 🚀 Installation

### 1. Clone the Project

```bash
cd /path/to/elasmetrics
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Settings

#### Option A: Environment Files (Recommended)

Create environment-specific configuration files:

```bash
# Run the setup script
./setup_env.sh

# Or manually create from template
cp .env.template .env          # For local development
cp .env.template .env.staging  # For staging
cp .env.template .env.production  # For production

# Edit with your credentials
vi .env
```

#### Option B: YAML Configuration

Edit the `config/config.yaml` file:

```yaml
elasticsearch:
  hosts:
    - "http://your-elasticsearch-host:9200"
  username: "elastic"
  password: "your-password"

mysql:
  host: "your-mysql-host"
  port: 3306
  database: "elasticsearch_metrics"
  user: "your-user"
  password: "your-password"
```

**Note**: Environment files take precedence over YAML configuration.

## 💻 Usage

### Collecting Metrics

```bash
# With default configuration (uses .env)
python main.py collect

# With specific environment
python main.py collect --env PRODUCTION
python main.py collect --env STAGING

# With custom configuration file
python main.py collect --config /path/to/config.yaml

# With JSON configuration (Airflow mode)
python main.py collect --config-json '{"elasticsearch":{...},"mysql":{...}}'
```

### Health Check

```bash
# Check with default environment
python main.py health-check

# Check specific environment
python main.py health-check --env PRODUCTION
```

### Cleaning Old Data

```bash
# Keep last 90 days, delete older
python main.py cleanup --days 90

# Cleanup in specific environment
python main.py cleanup --days 90 --env PRODUCTION
```

### Airflow Integration

```bash
# Run with Airflow runner
python airflow_runner.py \
    --config-file examples/config_example.json \
    --env PRODUCTION
```

For detailed Airflow integration, see [AIRFLOW_INTEGRATION.md](docs/AIRFLOW_INTEGRATION.md)

## 🔧 Configuration Details

### Configuration Hierarchy

The system supports multiple configuration methods (in order of precedence):

1. **Command-line JSON** (`--config-json`) - Highest priority
2. **Environment Variables** (from `.env` files)
3. **YAML Configuration** (`config/config.yaml`) - Lowest priority

### Environment-Based Configuration

Create environment-specific `.env` files:

```bash
# .env.production
ENV=PRODUCTION
ES_HOSTS=http://es-prod:9200
ES_USERNAME=elastic
ES_PASSWORD=prod_password
MYSQL_HOST=mysql-prod
MYSQL_DATABASE=elasticsearch_metrics
MYSQL_USER=metrics_user
MYSQL_PASSWORD=prod_mysql_password
```

### Elasticsearch Settings

**YAML:**
```yaml
elasticsearch:
  hosts:
    - "http://localhost:9200"
  username: "elastic"        # Optional
  password: "changeme"       # Optional
  api_key: "your_api_key"    # Alternative auth
  timeout: 30
  verify_certs: false
```

**Environment Variables:**
```bash
ES_HOSTS=http://localhost:9200
ES_USERNAME=elastic
ES_PASSWORD=changeme
ES_TIMEOUT=30
ES_VERIFY_CERTS=false
```

### MySQL Settings

**YAML:**
```yaml
mysql:
  host: "localhost"
  port: 3306
  database: "elasticsearch_metrics"
  user: "root"
  password: "changeme"
  charset: "utf8mb4"
  pool_size: 5
```

**Environment Variables:**
```bash
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=elasticsearch_metrics
MYSQL_USER=root
MYSQL_PASSWORD=changeme
MYSQL_POOL_SIZE=5
```

### Metrics Settings

#### Legacy Format (Still Supported)

```yaml
metrics:
  # Metrics to collect
  index_stats:
    - docs.count
    - docs.deleted
    - store.size_in_bytes
    - pri.store.size_in_bytes
  
  # Index patterns to include
  include_patterns:
    - "*"
  
  # Index patterns to exclude
  exclude_patterns:
    - ".security*"
    - ".kibana*"
  
  # Batch size
  batch_size: 100
```

#### Generic Metrics Format (Recommended - NEW!)

**Universal, type-safe, and configuration-driven:**

```yaml
metrics:
  # Specify which metrics to collect (no code changes needed!)
  collect:
    # Document metrics
    - docs.count
    - docs.deleted
    
    # Storage metrics
    - store.size_in_bytes
    - pri.store.size_in_bytes
    
    # Performance metrics (indexing)
    - indexing.index_total
    - indexing.index_time_in_millis
    
    # Performance metrics (search)
    - search.query_total
    - search.query_time_in_millis
    
    # Segment metrics
    - segments.count
    - segments.memory_in_bytes
    
    # Cache metrics
    - query_cache.memory_size_in_bytes
    - fielddata.memory_size_in_bytes
    
    # And many more...
  
  # Define custom metrics (optional)
  custom_definitions:
    - name: my.custom.metric
      es_path: primaries.my_plugin.custom_value
      type: integer  # string, float, boolean, timestamp, json
      description: Custom metric from ES plugin
      unit: count
  
  # Index patterns
  include_patterns:
    - "*"
  exclude_patterns:
    - ".security*"
    - ".kibana*"
  
  batch_size: 100
  collector_type: generic  # Use generic collector
```

**Key Benefits:**
- ✅ **17+ pre-registered metrics** ready to use
- ✅ **Add any metric** without code changes
- ✅ **Type-safe** with automatic validation
- ✅ **Works with any ES version** (7.x, 8.x, future)
- ✅ **Custom metrics** for plugins or special needs
- ✅ **Different metrics per environment**

For detailed guide, see [METRICS_GUIDE.md](docs/METRICS_GUIDE.md)

## 📊 Data Model

### Legacy Schema (Fixed Metrics)

```sql
CREATE TABLE index_metrics (
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
    growth_2m DECIMAL(20, 2),
    growth_2m_sku VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_index_name (index_name),
    INDEX idx_timestamp (timestamp)
);
```

### Generic Metrics Schema (Flexible - Recommended)

**JSON Storage (Maximum Flexibility):**

```sql
CREATE TABLE generic_metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    index_name VARCHAR(255) NOT NULL,
    timestamp DATETIME NOT NULL,
    metrics_json JSON NOT NULL,      -- All metrics stored as JSON
    metadata_json JSON,               -- Metadata (health, status, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_index_name (index_name),
    INDEX idx_timestamp (timestamp)
);
```

**Benefits:**
- ✅ Add new metrics without ALTER TABLE
- ✅ Query using JSON functions: `JSON_EXTRACT(metrics_json, '$.docs.count')`
- ✅ Supports any metric structure
- ✅ No schema changes needed

**Hybrid Storage (Performance + Flexibility):**

```sql
CREATE TABLE hybrid_metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    index_name VARCHAR(255) NOT NULL,
    timestamp DATETIME NOT NULL,
    
    -- Core metrics as columns (fast queries)
    docs_count BIGINT,
    store_size_bytes BIGINT,
    
    -- Additional metrics as JSON (flexible)
    additional_metrics JSON,
    metadata JSON,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_index_name (index_name),
    INDEX idx_timestamp (timestamp),
    INDEX idx_docs_count (docs_count),
    INDEX idx_size (store_size_bytes)
);
```

## 🔄 Cron/Scheduled Jobs

### Traditional Cron

Example crontab for daily automatic execution:

```bash
# Run every day at 02:00 AM in production
0 2 * * * cd /path/to/elastic-metrics && /path/to/venv/bin/python main.py collect --env PRODUCTION >> logs/cron.log 2>&1

# Run every 4 hours in staging
0 */4 * * * cd /path/to/elastic-metrics && /path/to/venv/bin/python main.py collect --env STAGING >> logs/cron_staging.log 2>&1
```

### Apache Airflow (Recommended)

For production environments, we recommend using Apache Airflow for better monitoring, retry logic, and orchestration:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
import json

def collect_metrics(**context):
    import sys
    sys.path.insert(0, '/opt/elasmetrics')
    from airflow_runner import run_collection
    
    config = {"elasticsearch": {...}, "mysql": {...}}
    result = run_collection(json.dumps(config), env='PRODUCTION')
    
    if not result['success']:
        raise Exception(f"Collection failed: {result.get('error')}")
    return result

dag = DAG('elasticsearch_metrics', schedule_interval='0 2 * * *', ...)
task = PythonOperator(task_id='collect', python_callable=collect_metrics, dag=dag)
```

See [AIRFLOW_INTEGRATION.md](docs/AIRFLOW_INTEGRATION.md) for detailed guide.

## 📈 Grafana Integration

### Adding MySQL Data Source

1. In Grafana: Configuration > Data Sources
2. "Add data source" > MySQL
3. Enter connection information:
   - Host: `your-mysql-host:3306`
   - Database: `elasticsearch_metrics`
   - User/Password: MySQL user credentials

### Example Grafana Queries

**Index Size Trend:**
```sql
SELECT
  timestamp as time,
  index_name,
  store_size_bytes / 1024 / 1024 / 1024 as size_gb
FROM index_metrics
WHERE
  $__timeFilter(timestamp)
  AND index_name IN ($index_name)
ORDER BY timestamp
```

**Top 10 Largest Indices:**
```sql
SELECT
  index_name,
  store_size_human,
  docs_count,
  pri_shards,
  replicas
FROM index_metrics
WHERE timestamp = (SELECT MAX(timestamp) FROM index_metrics)
ORDER BY store_size_bytes DESC
LIMIT 10
```

**Document Count Growth:**
```sql
SELECT
  timestamp as time,
  index_name,
  docs_count
FROM index_metrics
WHERE
  $__timeFilter(timestamp)
  AND index_name = '$index_name'
ORDER BY timestamp
```

## 🧪 Testing

```bash
# System test with Health check
python main.py health-check

# Test collection (like dry-run)
# Use test environment in config.yaml
python main.py collect --config config/config.test.yaml
```

## 🐛 Troubleshooting

### Elasticsearch Connection Error

```bash
# Connection test
curl -u username:password http://your-es-host:9200

# Health check
python main.py health-check
```

### MySQL Connection Error

```bash
# MySQL connection test
mysql -h your-mysql-host -u your-user -p

# Create database
CREATE DATABASE elasticsearch_metrics CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Log Check

```bash
# Follow log file
tail -f logs/elastic_metrics.log

# Filter errors
grep ERROR logs/elastic_metrics.log
```

## 🔐 Security

- **Never commit secrets**: All `.env.*` files are in `.gitignore`
- **Use environment files**: Store sensitive information in `.env.production`, `.env.staging`
- **Separate credentials**: Use different credentials for each environment
- **Strong passwords**: Generate strong passwords for production databases
- **Use SSL/TLS**: Enable SSL/TLS in production for Elasticsearch and MySQL
- **Minimum permissions**: Grant only required permissions to MySQL user:
  ```sql
  GRANT SELECT, INSERT, DELETE ON elasticsearch_metrics.* TO 'metrics_user'@'%';
  ```
- **File permissions**: Restrict access to environment files:
  ```bash
  chmod 600 .env.production
  chmod 600 .env.staging
  ```
- **Secret management**: Consider using AWS Secrets Manager, HashiCorp Vault, or similar for production

See [ENVIRONMENT_SETUP.md](docs/ENVIRONMENT_SETUP.md) for security best practices.

## 📝 Development

### Adding New Collector

1. Create new collector class under `src/collectors/`
2. Inherit from `BaseCollector`
3. Implement the `collect()` method
4. Update `MetricsService._create_collector()` method

### Adding New Metric

**With Generic Metrics System (Recommended - No Code Changes):**

Just add to your configuration:

```yaml
metrics:
  collect:
    - my.new.metric  # ← Add this
  
  custom_definitions:
    - name: my.new.metric
      es_path: primaries.custom.value
      type: integer
      description: My new metric
```

**With Legacy System (Requires Code Changes):**

1. Update `IndexMetrics` class in `src/models/index_metrics.py`
2. Update `MySQLRepository.CREATE_TABLE_SQL`
3. Add code to collect the metric in the collector

### Custom Metrics for Plugins

If you have custom Elasticsearch plugins:

```yaml
metrics:
  collect:
    - ml.anomaly_score
    - my_plugin.request_count
  
  custom_definitions:
    - name: ml.anomaly_score
      es_path: primaries.ml.anomaly_detection.score
      type: float
      description: Anomaly detection score from ML plugin
      
    - name: my_plugin.request_count
      es_path: primaries.my_plugin.requests.total
      type: integer
      description: Total requests to my plugin
```

## 🤝 Contributing

1. Open an issue for new features first
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push the branch: `git push origin feature/new-feature`
5. Create a Pull Request

## 📄 License

This project is for internal use.

## 👥 Contact

Contact the Data Engineering team for questions.

## 📚 Documentation

- **[README.md](README.md)** - Main documentation (you are here)
- **[SETUP.md](docs/SETUP.md)** - Detailed installation and setup guide
- **[METRICS_GUIDE.md](docs/METRICS_GUIDE.md)** - **NEW!** Generic metrics system guide
- **[ENVIRONMENT_SETUP.md](docs/ENVIRONMENT_SETUP.md)** - Environment configuration guide
- **[AIRFLOW_INTEGRATION.md](docs/AIRFLOW_INTEGRATION.md)** - Apache Airflow integration guide
- **[QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - Quick reference for common tasks
- **[PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md)** - Project overview and architecture
- **[CHANGELOG.md](docs/CHANGELOG.md)** - Version history and changes

## 🔄 Version History

- **v1.2.0** (2026-01-13): Generic Metrics System
  - **Universal metrics collection** - works with any ES version
  - **Type-safe metrics** with validation (integer, float, string, boolean, JSON)
  - **17+ pre-registered metrics** (docs, storage, indexing, search, cache, etc.)
  - **Configuration-driven** - add metrics without code changes
  - **Custom metrics support** for plugins and special needs
  - **Flexible database schemas** (JSON, hybrid, key-value)
  - **Backward compatible** with legacy collectors
  - Comprehensive documentation (METRICS_GUIDE.md)

- **v1.1.0** (2026-01-13): Environment Management & Airflow Integration
  - Environment-based configuration (staging, production)
  - Apache Airflow integration support
  - JSON configuration support
  - Enhanced ConfigLoader with multi-source support
  - Environment file templates (.env.template)
  - Comprehensive documentation

- **v1.0.0** (2026-01-13): First stable release
  - Elasticsearch index metrics collection
  - MySQL storage
  - Health check and cleanup commands
  - Comprehensive logging

