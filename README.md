# ElasMetrics - Elasticsearch Metrics Collector

**Flexible, type-safe metrics collection from Elasticsearch to MySQL with Grafana visualization.**

## 🎯 Overview

ElasMetrics collects index metrics from Elasticsearch clusters and stores them in MySQL for analysis, trending, and alerting. Designed for multi-environment production use with Airflow integration.

**Key Features:**
- ✅ **Universal Metrics** - Collect ANY Elasticsearch metric without code changes
- ✅ **Type-Safe** - Built-in validation (integer, float, string, boolean, JSON)
- ✅ **Multi-Environment** - Staging, production configs with AWS Parameter Store
- ✅ **Airflow Ready** - Native DAG integration
- ✅ **Time-Series + Current State** - Historical trends AND fast current state queries
- ✅ **17+ Pre-Registered Metrics** - Common metrics ready to use

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

# Collect metrics
python main.py collect

# Cleanup old data (keep 90 days)
python main.py cleanup --days 90
```

**See [docs/QUICKSTART.md](docs/QUICKSTART.md) for detailed setup.**

---

## 📊 Universal Metrics System

**Add ANY metric without code changes:**

```yaml
# config/config.yaml
metrics:
  collect:
    # Document & storage
    - docs.count
    - store.size_in_bytes
    
    # Performance
    - indexing.index_total
    - search.query_total
    
    # Cache & segments
    - query_cache.memory_size_in_bytes
    - segments.count
    
    # Custom plugin metrics
    - my.custom.plugin.metric
  
  # Define custom metrics
  custom_definitions:
    - name: my.custom.plugin.metric
      es_path: primaries.my_plugin.value
      type: integer
      description: Custom metric from ES plugin
```

**17+ pre-registered metrics available. See [docs/METRICS_GUIDE.md](docs/METRICS_GUIDE.md)**

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

### Current State (Fast)

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

### Historical Analysis (Trends)

```sql
-- Track index growth over last 7 days
SELECT 
    DATE(timestamp) as day,
    index_name,
    AVG(docs_count) as avg_docs,
    AVG(store_size_bytes/1024/1024/1024) as avg_size_gb
FROM index_metrics
WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY DATE(timestamp), index_name
ORDER BY day, index_name;
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

### Time-Series Table (Historical Data)

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

### Current State View (Fast Queries)

```sql
-- Automatically created, always shows latest metrics
CREATE VIEW index_metrics_latest AS
SELECT t1.*
FROM index_metrics t1
JOIN (
    SELECT index_name, MAX(timestamp) AS max_timestamp
    FROM index_metrics
    GROUP BY index_name
) t2 ON t1.index_name = t2.index_name 
    AND t1.timestamp = t2.max_timestamp;
```

**Benefits:**
- ✅ Full historical data for trends
- ✅ Fast current-state queries via VIEW
- ✅ Both use cases supported

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[QUICKSTART.md](docs/QUICKSTART.md)** | 5-minute setup guide |
| **[METRICS_GUIDE.md](docs/METRICS_GUIDE.md)** | Complete metrics system guide |
| **[QUERY_GUIDE.md](docs/QUERY_GUIDE.md)** | 50+ SQL query examples |
| **[ENVIRONMENT_SETUP.md](docs/ENVIRONMENT_SETUP.md)** | Multi-environment configuration |
| **[PARAMETER_STORE_GUIDE.md](docs/PARAMETER_STORE_GUIDE.md)** | AWS Parameter Store setup |
| **[AIRFLOW_INTEGRATION.md](docs/AIRFLOW_INTEGRATION.md)** | Airflow DAG integration |
| **[DOCKER_SETUP.md](docs/DOCKER_SETUP.md)** | Local testing with Docker |
| **[QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** | Command cheat sheet |
| **[ES_QUERY_GUIDE.md](docs/ES_QUERY_GUIDE.md)** | Elasticsearch query examples |

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
