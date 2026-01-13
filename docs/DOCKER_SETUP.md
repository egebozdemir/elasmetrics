# Docker Test Environment Setup

## 🔍 Port Conflict Issue

If you have MySQL already running on port 3306 (Homebrew, native install, etc.), you have two options:

## ✅ Option 1: Use Local MySQL (Recommended)

**Best if you already have MySQL running via Homebrew**

### Step 1: Start only Elasticsearch
```bash
docker-compose -f docker-compose-es-only.yml up -d
```

### Step 2: Setup your local MySQL
```bash
./setup-mysql-local.sh
```

### Step 3: Configure elasmetrics
Your `.env` file should use:
```bash
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=elasticsearch_metrics
MYSQL_USER=metrics_user
MYSQL_PASSWORD=metrics_password

ES_HOSTS=http://localhost:9200
```

### Step 4: Test
```bash
python main.py health-check
python main.py collect
```

---

## ✅ Option 2: Use Docker MySQL on Different Port

**Best for complete isolation**

### Step 1: Start both services
```bash
docker-compose up -d
```

**Note:** Docker MySQL runs on port **3307** to avoid conflicts

### Step 2: Configure elasmetrics
Your `.env` file should use:
```bash
MYSQL_HOST=localhost
MYSQL_PORT=3307  # ← Note the different port!
MYSQL_DATABASE=elasticsearch_metrics
MYSQL_USER=metrics_user
MYSQL_PASSWORD=metrics_password

ES_HOSTS=http://localhost:9200
```

### Step 3: Test
```bash
python main.py health-check
python main.py collect
```

---

## ✅ Option 3: Stop Local MySQL Temporarily

**If you want to use the default setup**

### Step 1: Stop Homebrew MySQL
```bash
brew services stop mysql
```

### Step 2: Start Docker services on port 3306
Edit `docker-compose.yml` and change MySQL port back to:
```yaml
ports:
  - "3306:3306"
```

### Step 3: Start services
```bash
docker-compose up -d
```

### Step 4: When done, restart Homebrew MySQL
```bash
docker-compose down
brew services start mysql
```

---

## 🚀 Quick Commands

### Check what's running on port 3306
```bash
lsof -i :3306
```

### Check what's running on port 3307
```bash
lsof -i :3307
```

### Check if Elasticsearch is running
```bash
curl http://localhost:9200
```

### View Docker logs
```bash
# All services
docker-compose logs -f

# Just Elasticsearch
docker-compose logs -f elasticsearch

# Just MySQL (if using Docker MySQL)
docker-compose logs -f mysql
```

### Stop everything
```bash
# Elasticsearch only
docker-compose -f docker-compose-es-only.yml down

# Both services
docker-compose down
```

### Remove all data
```bash
docker-compose down -v
```

---

## 📊 Populate Sample Data

After Elasticsearch is running:

```bash
./docker-populate-sample-data.sh
```

This creates several test indices with sample data:
- `logs-app-2024.01.*` - Application logs
- `metrics-system-2024.01` - System metrics
- `events-user-actions` - User events
- `products-catalog` - Product data
- `orders-2024-q1` - Order data

---

## 🔧 Troubleshooting

### "Address already in use" error

**Problem:** Port 3306 is already taken

**Solution:** Use Option 1 (local MySQL) or Option 2 (port 3307)

### "Cannot connect to MySQL"

**Check if it's running:**
```bash
# For local MySQL
brew services list | grep mysql

# For Docker MySQL
docker ps | grep mysql
```

**Test connection:**
```bash
# Local MySQL (port 3306)
mysql -h localhost -P 3306 -u metrics_user -pmetrics_password -e "SELECT 1"

# Docker MySQL (port 3307)
mysql -h localhost -P 3307 -u metrics_user -pmetrics_password -e "SELECT 1"
```

### "Cannot connect to Elasticsearch"

**Check if it's running:**
```bash
docker ps | grep elasticsearch
```

**Check logs:**
```bash
docker-compose logs elasticsearch
```

**Test connection:**
```bash
curl http://localhost:9200
```

---

## 💡 Recommended Setup

For development/testing with existing Homebrew MySQL:

1. Use **Option 1** (local MySQL + Docker Elasticsearch)
2. Keep your Homebrew MySQL running
3. Only run Elasticsearch in Docker
4. Less resource usage
5. Can use MySQL Workbench or other tools you already have

```bash
# Quick start
docker-compose -f docker-compose-es-only.yml up -d
./setup-mysql-local.sh
./docker-populate-sample-data.sh
python main.py health-check
python main.py collect
```

Done! 🎉

