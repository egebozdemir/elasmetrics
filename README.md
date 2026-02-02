# ElasMetrics - Elasticsearch Metrics Collector

**Flexible, type-safe metrics collection from Elasticsearch to MySQL with Grafana visualization.**

## 🎯 Overview

ElasMetrics collects index metrics from Elasticsearch clusters and stores them in MySQL for analysis, trending, and alerting. Designed for multi-environment production use with Airflow integration.

**Key Features:**
- ✅ **Universal Metrics** - Collect ANY Elasticsearch metric without code changes
- ✅ **Multi-Cluster Support** - Connect to multiple ES/OpenSearch clusters (VPC + proxy endpoints)
- ✅ **Custom Aggregation Queries** - Run `_count` and `_search` aggregations, store results in MySQL
- ✅ **Multi-Environment** - Staging, production configs with AWS Parameter Store
- ✅ **Airflow Ready** - Native DAG integration
- ✅ **Time-Series + Current State** - Historical trends AND fast current state queries
- ✅ **AWS OpenSearch Compatible** - Works with AWS Elasticsearch and OpenSearch Service

---

## 🚀 Quick Start

### 1. Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
# Create .env file from template
./scripts/setup_env.sh

# Edit with your credentials
vi .env
```

**Minimum config (.env):**
```bash
ES_HOSTS=http://localhost:9200
ES_USERNAME=elastic
ES_PASSWORD=changeme

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=elasticsearch_metrics
MYSQL_USER=root
MYSQL_PASSWORD=changeme
```

### 3. Test & Run

```bash
# Health check
python main.py health-check

# Collect index metrics
python main.py collect

# Collect aggregation metrics (custom queries)
python main.py collect-aggregations

# List configured data sources
python main.py list-sources

# List configured aggregation queries
python main.py list-queries

# Cleanup old data (keep 90 days)
python main.py cleanup --days 90
```

**See [docs/QUICKSTART.md](docs/QUICKSTART.md) for detailed setup.**

---

## 📊 Multi-Cluster & Aggregation Queries

**Connect to multiple ES/OpenSearch clusters:**

```yaml
# config/config.yaml
data_sources:
  main_cluster:
    hosts:
      - "https://vpc-your-domain.us-east-1.es.amazonaws.com:443"
    username: "${ES_MAIN_USERNAME}"
    password: "${ES_MAIN_PASSWORD}"

  enterprise_datahub:
    hosts:
      - "https://datahub-api.yourcompany.com"
    username: "${DATAHUB_USERNAME}"
    password: "${DATAHUB_PASSWORD}"
```

**Run custom aggregation queries:**

```yaml
aggregation_queries:
  - name: stock_item_count
    data_source: main_cluster
    index_pattern: "products-*"
    query_type: count
    query:
      match:
        in_stock: true
    result_mapping:
      type: single_value
      value_path: "count"

  - name: items_per_locale
    data_source: main_cluster
    index_pattern: "catalog-*"
    query_type: search
    query:
      size: 0
      aggs:
        by_locale:
          terms:
            field: locale
            size: 50
    result_mapping:
      type: terms_buckets
      aggregation_path: "by_locale"
      dimension_field: "locale"
      value_field: "doc_count"
```

**See [config/config.multi-cluster.example.yaml](config/config.multi-cluster.example.yaml) for complete examples.**

---

## ⚙️ Configuration

### Multi-Environment Support

```bash
# Local development
python main.py collect

# Staging environment
python main.py collect --env STAGING

# Production environment
python main.py collect --env PRODUCTION
```

### Configuration Hierarchy (priority order)

1. **Command-line JSON** (`--config-json`) - Highest
2. **Environment Variables** (from `.env` files)
3. **YAML Configuration** (`config/config.yaml`)
4. **AWS Parameter Store** (when enabled) - Lowest

**See [docs/ENVIRONMENT_SETUP.md](docs/ENVIRONMENT_SETUP.md) for details.**

---

## 🔐 AWS Parameter Store (Production)

```bash
# Interactive setup
python scripts/manage_parameters.py setup PRODUCTION

# Or create manually
python scripts/manage_parameters.py create \
    "/ELASMETRICS/PRODUCTION/MYSQL/PASSWORD" \
    "secure-password" \
    --type SecureString
```

**Enable in `.env`:**
```bash
USE_PARAMETER_STORE=true
LOCAL_DEV_MODE=false  # Set to true for local testing
```

**See [docs/PARAMETER_STORE_GUIDE.md](docs/PARAMETER_STORE_GUIDE.md)**

---

## ✈️ Airflow Integration

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
import json

def collect_metrics(**context):
    import sys
    sys.path.insert(0, '/opt/elasmetrics')
    from scripts.airflow_runner import run_collection
    
    config = {
        "elasticsearch": {"hosts": ["http://es-prod:9200"], ...},
        "mysql": {"host": "mysql-prod", ...}
    }
    
    result = run_collection(json.dumps(config), env='PRODUCTION')
    if not result['success']:
        raise Exception(f"Failed: {result.get('error')}")

dag = DAG('elasticsearch_metrics', schedule_interval='0 2 * * *', ...)
task = PythonOperator(task_id='collect', python_callable=collect_metrics, dag=dag)
```

**See [docs/AIRFLOW_INTEGRATION.md](docs/AIRFLOW_INTEGRATION.md)**

---

## 📈 Querying Data

### Index Metrics - Current State

```sql
-- Get latest metrics for all indices (uses optimized VIEW)
SELECT
    index_name,
    docs_count,
    store_size_human,
    health,
    timestamp
FROM index_metrics_latest
ORDER BY docs_count DESC;
```

### Aggregation Metrics - Custom Queries

```sql
-- Get latest aggregation metrics
SELECT
    metric_name,
    data_source,
    value_numeric,
    dimension_1_name,
    dimension_1_value,
    timestamp
FROM aggregation_metrics_latest
ORDER BY metric_name;

-- Trend analysis for custom metrics
SELECT
    DATE(timestamp) as day,
    metric_name,
    AVG(value_numeric) as avg_value
FROM aggregation_metrics
WHERE metric_name = 'stock_item_count'
  AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY DATE(timestamp), metric_name
ORDER BY day;
```

**50+ query examples in [docs/QUERY_GUIDE.md](docs/QUERY_GUIDE.md)**

---

## 🐳 Docker Test Environment

```bash
# Start Elasticsearch + MySQL
docker-compose up -d

# Populate test data (23K docs, 7 indices)
./scripts/docker-populate-sample-data.sh

# Configure .env for Docker setup
# MYSQL_PORT=3307 (Docker MySQL runs on 3307 to avoid conflicts)

# Test
python main.py health-check
python main.py collect
```

**Note:** Docker MySQL runs on port **3307** to avoid conflicts with local MySQL.

**See [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md) for alternative setups.**

---

## 📊 Database Schema

### Index Metrics Table

```sql
CREATE TABLE index_metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    index_name VARCHAR(255) NOT NULL,
    timestamp DATETIME NOT NULL,
    docs_count BIGINT,
    store_size_bytes BIGINT,
    -- ... more metrics ...
    INDEX idx_index_name (index_name),
    INDEX idx_timestamp (timestamp)
);
```

### Aggregation Metrics Table (Custom Queries)

```sql
CREATE TABLE aggregation_metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    data_source VARCHAR(100) NOT NULL,
    index_pattern VARCHAR(255),
    timestamp DATETIME NOT NULL,
    value_numeric DOUBLE,
    dimension_1_name VARCHAR(100),  -- For grouping (e.g., 'locale')
    dimension_1_value VARCHAR(255), -- Dimension value (e.g., 'en_US')
    -- ... up to 3 dimensions ...
    INDEX idx_metric_name (metric_name),
    INDEX idx_timestamp (timestamp)
);
```

**Both tables have `_latest` VIEWs for fast current-state queries.**

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[QUICKSTART.md](docs/QUICKSTART.md)** | 5-minute setup guide |
| **[SR_USAGE_INTEGRATION_PLAN.md](docs/SR_USAGE_INTEGRATION_PLAN.md)** | Multi-cluster & aggregation architecture |
| **[METRICS_GUIDE.md](docs/METRICS_GUIDE.md)** | Complete metrics system guide |
| **[QUERY_GUIDE.md](docs/QUERY_GUIDE.md)** | 50+ SQL query examples |
| **[ENVIRONMENT_SETUP.md](docs/ENVIRONMENT_SETUP.md)** | Multi-environment configuration |
| **[PARAMETER_STORE_GUIDE.md](docs/PARAMETER_STORE_GUIDE.md)** | AWS Parameter Store setup |
| **[AIRFLOW_INTEGRATION.md](docs/AIRFLOW_INTEGRATION.md)** | Airflow DAG integration |
| **[DOCKER_SETUP.md](docs/DOCKER_SETUP.md)** | Local testing with Docker |
| **[QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** | Command cheat sheet |

**See [docs/INDEX.md](docs/INDEX.md) for complete navigation.**

---

## 🏗️ Architecture

```
elasmetrics/
├── main.py                      # CLI entry point
├── config/
│   └── config.yaml              # Main configuration
├── src/
│   ├── collectors/              # Metric collectors (Strategy pattern)
│   ├── repositories/            # Data access (Repository pattern)
│   ├── models/                  # Data models
│   ├── services/                # Business logic (Facade pattern)
│   └── utils/                   # Configuration & utilities
├── scripts/                     # Utility scripts
│   ├── manage_parameters.py     # AWS Parameter Store
│   ├── airflow_runner.py        # Airflow integration
│   ├── test_queries.py          # Query testing
│   └── docker-*.sh              # Docker helpers
├── docs/                        # Documentation
└── examples/                    # Example configurations
```

**Design Patterns:** Strategy, Repository, Facade, Singleton, Factory Method

---

## 🔄 Automation

### Cron

```bash
# Daily collection in production
0 2 * * * cd /path/to/elasmetrics && venv/bin/python main.py collect --env PRODUCTION

# Every 4 hours in staging
0 */4 * * * cd /path/to/elasmetrics && venv/bin/python main.py collect --env STAGING
```

### Airflow (Recommended)

See [docs/AIRFLOW_INTEGRATION.md](docs/AIRFLOW_INTEGRATION.md) for production-ready DAG examples.

---

## 🔒 Security

- ✅ Never commit secrets (`.env*` in `.gitignore`)
- ✅ Use AWS Parameter Store for production
- ✅ Separate credentials per environment
- ✅ Restrict file permissions: `chmod 600 .env.production`
- ✅ Minimum MySQL privileges:
  ```sql
  GRANT SELECT, INSERT, DELETE ON elasticsearch_metrics.* TO 'metrics_user'@'%';
  ```

---

## 🛠️ Development

### Add New Metric (No Code Changes!)

```yaml
# Just add to config/config.yaml
metrics:
  collect:
    - my.new.metric
  
  custom_definitions:
    - name: my.new.metric
      es_path: primaries.custom.value
      type: integer
      description: My new metric
```

### Add New Collector (Code Changes)

1. Create class in `src/collectors/` extending `BaseCollector`
2. Implement `collect()` method
3. Update `MetricsService._create_collector()`

---

## 📦 Requirements

- Python 3.8+
- Elasticsearch 7.x or 8.x (including AWS Elasticsearch/OpenSearch)
- MySQL 5.7+ or MariaDB 10.3+
- (Optional) AWS CLI configured for Parameter Store
- (Optional) Docker for local testing

**✅ AWS Elasticsearch/OpenSearch Compatible** - Works seamlessly with AWS managed Elasticsearch and OpenSearch Service

---

## 🤝 Contributing

1. Open an issue first
2. Create feature branch: `git checkout -b feature/name`
3. Commit: `git commit -am 'Add feature'`
4. Push: `git push origin feature/name`
5. Create Pull Request

---
