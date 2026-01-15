# 📜 Scripts Directory

This directory contains utility scripts, setup tools, and helper programs for the ElasMetrics project.

---

## 🚀 **Setup Scripts**

### **`setup-mysql-local.sh`**
**Purpose:** Set up MySQL database and user on local Homebrew MySQL  
**Usage:**
```bash
./scripts/setup-mysql-local.sh
```
**What it does:**
- Creates `elasticsearch_metrics` database
- Creates `metrics_user` with appropriate permissions
- Configures for local development

---

### **`setup_env.sh`**
**Purpose:** Create environment files from template  
**Usage:**
```bash
./scripts/setup_env.sh
```
**What it does:**
- Copies `.env.template` to `.env`, `.env.staging`, `.env.production`
- Helps set up environment-specific configurations

---

## 🐳 **Docker Scripts**

### **`docker-start.sh`**
**Purpose:** Start Docker Compose services  
**Usage:**
```bash
./scripts/docker-start.sh
```
**What it does:**
- Starts Elasticsearch and MySQL in Docker
- Waits for services to be ready
- Shows status

---

### **`docker-populate-sample-data.sh`**
**Purpose:** Populate Elasticsearch with synthetic test data  
**Usage:**
```bash
./scripts/docker-populate-sample-data.sh
```
**What it does:**
- Creates 7 sample indices
- Populates with test documents
- Total: ~23,000 documents across logs, events, orders, products, metrics

**Indices created:**
- `logs-app-2024.01.01` - 1,000 docs
- `logs-app-2024.01.02` - 1,500 docs
- `logs-app-2024.01.03` - 2,000 docs
- `metrics-system-2024.01` - 5,000 docs
- `events-user-actions` - 10,000 docs
- `products-catalog` - 500 docs
- `orders-2024-q1` - 3,000 docs

---

## 🔐 **AWS Parameter Store Scripts**

### **`manage_parameters.py`**
**Purpose:** Manage AWS Parameter Store parameters  
**Usage:**
```bash
# Create parameter
python scripts/manage_parameters.py create \
    "/ELASMETRICS/STAGING/MYSQL/PASSWORD" \
    "your-password" \
    --type SecureString

# Get parameter
python scripts/manage_parameters.py get \
    "/ELASMETRICS/STAGING/MYSQL/PASSWORD" \
    --show-value

# List parameters by path
python scripts/manage_parameters.py list \
    "/ELASMETRICS/STAGING/" \
    --recursive

# Delete parameter
python scripts/manage_parameters.py delete \
    "/ELASMETRICS/STAGING/OLD_PARAM" \
    --force

# Interactive setup for environment
python scripts/manage_parameters.py setup STAGING
```

**Features:**
- Create/read/update/delete parameters
- Interactive environment setup
- Supports both String and SecureString types
- Masked value display for security

**See:** `docs/PARAMETER_STORE_GUIDE.md` for details

---

## ⚙️ **Airflow Integration**

### **`airflow_runner.py`**
**Purpose:** Run metrics collection in Airflow DAGs  
**Usage:**
```bash
# With JSON config
python scripts/airflow_runner.py --config-json '{
    "elasticsearch": {"hosts": ["http://localhost:9200"]},
    "mysql": {"host": "localhost", "database": "elasticsearch_metrics", ...}
}'

# With environment and config file
python scripts/airflow_runner.py --env STAGING --config config/config.yaml
```

**Features:**
- JSON configuration support (for Airflow)
- Environment-based configuration
- Proper logging
- Exit codes for DAG status

**See:** `examples/airflow_dag_example.py` for DAG integration

---

## 🔍 **Testing & Demo Scripts**

### **`test_queries.py`**
**Purpose:** Test time-series and current-state queries  
**Usage:**
```bash
python scripts/test_queries.py
```
**What it tests:**
- Current state VIEW queries
- Historical time-series data
- Summary statistics
- Verifies both query patterns work

---

### **`showcase_es_queries.py`**
**Purpose:** Python-based Elasticsearch query demonstrations  
**Usage:**
```bash
python scripts/showcase_es_queries.py
```
**What it shows:**
- 13 different ES query patterns
- Cluster info and health
- Search examples
- Aggregations (terms, stats, date histogram)
- Multi-index queries
- Mappings and settings

---

### **`showcase-es-queries.sh`**
**Purpose:** Bash-based Elasticsearch query demonstrations  
**Usage:**
```bash
./scripts/showcase-es-queries.sh
```
**What it shows:**
- Same queries as Python version
- Uses curl and jq
- Good for presentations and testing
- 13 different query examples

---

### **`inspect-data.sh`**
**Purpose:** Quick inspection of synthetic data  
**Usage:**
```bash
./scripts/inspect-data.sh
```
**What it shows:**
- Cluster summary
- Document counts
- Sample documents from each index
- Field mappings

---

## 📋 **Example Scripts**

### **`run_example.sh`**
**Purpose:** Run example collection with different configurations  
**Usage:**
```bash
./scripts/run_example.sh
```
**What it does:**
- Demonstrates various configuration methods
- Shows environment-based configs
- Example metrics collections

---

## 🎯 **Quick Reference**

### **Initial Setup:**
```bash
# 1. Set up environment files
./scripts/setup_env.sh

# 2. Start Docker services
./scripts/docker-start.sh

# 3. Set up local MySQL (if using Homebrew)
./scripts/setup-mysql-local.sh

# 4. Populate test data
./scripts/docker-populate-sample-data.sh

# 5. Test the system
python scripts/test_queries.py
```

### **AWS Parameter Store Setup:**
```bash
# Interactive setup
python scripts/manage_parameters.py setup STAGING

# Or manual creation
python scripts/manage_parameters.py create \
    "/ELASMETRICS/STAGING/MYSQL/PASSWORD" \
    "your-password" \
    --type SecureString
```

### **Data Inspection:**
```bash
# Quick data overview
./scripts/inspect-data.sh

# ES query showcase (Python)
python scripts/showcase_es_queries.py

# ES query showcase (Bash)
./scripts/showcase-es-queries.sh

# Test database queries
python scripts/test_queries.py
```

---

## 📝 **Script Permissions**

All scripts should be executable:

```bash
chmod +x scripts/*.sh
chmod +x scripts/*.py
```

---

## 🔗 **Related Documentation**

| Script | Related Documentation |
|--------|----------------------|
| `manage_parameters.py` | `docs/PARAMETER_STORE_GUIDE.md` |
| `airflow_runner.py` | `docs/AIRFLOW_INTEGRATION.md` |
| `test_queries.py` | `docs/QUERY_GUIDE.md`, `docs/TIME_SERIES_SETUP.md` |
| `showcase_es_queries.py` | `docs/ES_QUERY_GUIDE.md` |
| `docker-*.sh` | `docs/DOCKER_SETUP.md` |
| `setup-mysql-local.sh` | `docs/SETUP.md` |

---

## 🐛 **Troubleshooting**

### **Permission Denied**
```bash
chmod +x scripts/<script-name>
```

### **Python Scripts Not Found**
```bash
# Make sure you're in the project root
cd /path/to/elasmetrics
python scripts/script_name.py
```

### **Module Not Found**
```bash
# Activate virtual environment
source venv/bin/activate
pip install -r requirements.txt
```

### **Docker Not Running**
```bash
# Start Docker Desktop first
docker ps

# Then run docker scripts
./scripts/docker-start.sh
```

---

## 📚 **More Information**

- **Project Documentation:** `docs/` directory
- **Main README:** `README.md`
- **Quick Start:** `docs/QUICKSTART.md`
- **Setup Guide:** `docs/SETUP.md`

---

**Note:** All scripts are designed to be run from the project root directory.

