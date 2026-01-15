# ⚡ Quick Start (5 Minutes)

## Minimum Requirements

- ✅ Python 3.8+
- ✅ Elasticsearch cluster access
- ✅ MySQL/MariaDB

## 🚀 Run in 5 Minutes

### 1️⃣ Virtual Environment and Dependencies (2 min)

```bash
cd /Users/ege.bozdemir/Desktop/EGE/projects/elastic-metrics

# Virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2️⃣ MySQL Preparation (1 min)

```bash
mysql -u root -p << EOF
CREATE DATABASE elasticsearch_metrics CHARACTER SET utf8mb4;
EXIT
EOF
```

### 3️⃣ Configuration (1 min)

Edit the `config/config.yaml` file:

```yaml
elasticsearch:
  hosts:
    - "http://YOUR_ELASTICSEARCH_HOST:9200"

mysql:
  host: "localhost"
  database: "elasticsearch_metrics"
  user: "root"
  password: "YOUR_MYSQL_PASSWORD"
```

### 4️⃣ Test and Run (1 min)

```bash
# Test connections
python main.py health-check

# Collect first metrics
python main.py collect
```

## ✅ Successful Installation Indicators

Health check output:

```
Overall Status: HEALTHY
Elasticsearch: healthy ✓
MySQL: healthy ✓
```

Collect output:

```
✓ Metrics collection and storage completed successfully
  Metrics collected: XX
  Metrics stored: XX
```

## 📊 Next Steps

1. **Grafana Dashboard**: See `README.md` > Grafana queries
2. **Scheduling**: See `AIRFLOW_INTEGRATION.md` for production scheduling
3. **Queries**: See `QUERY_GUIDE.md` for analysis examples

## 🆘 Having Issues?

### Cannot connect to Elasticsearch

```bash
# Test connection
curl http://YOUR_ELASTICSEARCH_HOST:9200

# Add username/password to config
```

### Cannot connect to MySQL

```bash
# Is MySQL service running?
mysql -h localhost -u root -p

# Does database exist?
SHOW DATABASES LIKE 'elasticsearch_metrics';
```

### Python dependency error

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

## 📞 Help

- Main documentation: [README.md](../README.md)
- All docs index: [INDEX.md](INDEX.md)
- Environment setup: [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md)
- Log file: `logs/elastic_metrics.log`

