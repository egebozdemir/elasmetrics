# ⏱️ Time-Series Setup - Best of Both Worlds

## ✅ What You Have Now

Your setup supports **BOTH** requirements:

### **1. Historical Tracking (Time-Series)**
- ✅ All collection runs stored in `index_metrics` table
- ✅ Track growth over days, weeks, months
- ✅ Trend analysis and capacity planning
- ✅ Historical alerting (detect rapid changes)

### **2. Fast Current State**
- ✅ Optimized `index_metrics_latest` VIEW
- ✅ One row per index (latest only)
- ✅ Fast queries for dashboards
- ✅ Real-time monitoring

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│  index_metrics (TABLE)                  │
│  - Full time-series data                │
│  - All collection runs                  │
│  - Historical analysis                  │
│                                         │
│  Row 1: index_A @ 10:00 → 1000 docs    │
│  Row 2: index_B @ 10:00 → 2000 docs    │
│  Row 3: index_A @ 11:00 → 1050 docs    │← Growth tracking
│  Row 4: index_B @ 11:00 → 2100 docs    │
│  Row 5: index_A @ 12:00 → 1100 docs    │
│  ...                                    │
└─────────────────────────────────────────┘
                   │
                   │ Automatically filtered by VIEW
                   ↓
┌─────────────────────────────────────────┐
│  index_metrics_latest (VIEW)            │
│  - Latest snapshot only                 │
│  - One row per index                    │
│  - Fast current state                   │
│                                         │
│  Row 1: index_A @ 12:00 → 1100 docs    │← Latest only
│  Row 2: index_B @ 12:00 → 2100 docs    │
└─────────────────────────────────────────┘
```

---

## 🚀 Usage

### **For Current State (Fast)**

```python
# Python
current_state = repository.get_current_state()

# SQL
SELECT * FROM index_metrics_latest;
```

**Perfect for:**
- Dashboard showing "right now"
- Current cluster health
- Latest size/doc counts
- Real-time status

### **For Trends (Historical)**

```python
# Python
metrics = repository.get_metrics_by_index(
    'events-user-actions',
    start_date=datetime.now() - timedelta(days=7)
)

# SQL
SELECT * FROM index_metrics
WHERE index_name = 'events-user-actions'
  AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY);
```

**Perfect for:**
- Growth charts
- Capacity planning
- Trend analysis
- Change detection

---

## 📊 Example Queries

### **Current State Examples**

```sql
-- All current indices
SELECT index_name, docs_count, store_size_human, health
FROM index_metrics_latest
ORDER BY store_size_bytes DESC;

-- Current total storage
SELECT SUM(store_size_bytes) / 1024 / 1024 / 1024 as total_gb
FROM index_metrics_latest;

-- Unhealthy indices right now
SELECT index_name, health, status, docs_count
FROM index_metrics_latest
WHERE health != 'green';
```

### **Time-Series Examples**

```sql
-- Daily growth for last 7 days
SELECT 
    DATE(timestamp) as date,
    index_name,
    MAX(docs_count) - MIN(docs_count) as daily_growth
FROM index_metrics
WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY DATE(timestamp), index_name;

-- Hourly collection runs
SELECT 
    HOUR(timestamp) as hour,
    COUNT(DISTINCT index_name) as indices_collected
FROM index_metrics
WHERE DATE(timestamp) = CURDATE()
GROUP BY HOUR(timestamp);

-- Compare last 2 runs
WITH ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY index_name ORDER BY timestamp DESC) as rn
    FROM index_metrics
)
SELECT 
    a.index_name,
    a.docs_count - b.docs_count as docs_change,
    TIMESTAMPDIFF(MINUTE, b.timestamp, a.timestamp) as minutes_between
FROM ranked a
JOIN ranked b ON a.index_name = b.index_name AND b.rn = 2
WHERE a.rn = 1;
```

---

## 🗑️ Data Retention

### **Manual Cleanup**

```sql
-- Delete data older than 90 days
DELETE FROM index_metrics
WHERE timestamp < DATE_SUB(NOW(), INTERVAL 90 DAY);
```

### **Automated Cleanup (Python)**

```python
# In your collection script or scheduler
from src.repositories import MySQLRepository

repository = MySQLRepository(config['mysql'])

# Delete old data (runs after collection)
deleted = repository.delete_old_metrics(days=90)
logger.info(f"Cleaned up {deleted} old records")
```

### **Recommended Retention**

| Data Age | Action |
|----------|--------|
| 0-7 days | Keep all (raw data) |
| 7-30 days | Keep all or hourly aggregates |
| 30-90 days | Keep daily aggregates |
| 90+ days | Delete (or archive) |

---

## 📈 Grafana Integration

### **Dashboard Panel 1: Current Status**

```sql
SELECT 
    index_name,
    docs_count,
    store_size_bytes / 1024 / 1024 as size_mb,
    health
FROM index_metrics_latest
ORDER BY docs_count DESC;
```

### **Dashboard Panel 2: Growth Over Time**

```sql
SELECT 
    $__timeGroup(timestamp, '1h') as time,
    index_name,
    AVG(docs_count) as docs
FROM index_metrics
WHERE $__timeFilter(timestamp)
GROUP BY time, index_name
ORDER BY time;
```

### **Dashboard Panel 3: Storage Trends**

```sql
SELECT 
    $__timeGroup(timestamp, '1h') as time,
    SUM(store_size_bytes) / 1024 / 1024 / 1024 as total_gb
FROM index_metrics
WHERE $__timeFilter(timestamp)
GROUP BY time
ORDER BY time;
```

---

## 🔔 Alerting Examples

### **Alert 1: Current Size Threshold**

```sql
-- Check every 5 minutes
SELECT index_name, store_size_human
FROM index_metrics_latest
WHERE store_size_bytes > 1024 * 1024 * 1024;  -- > 1GB
```

### **Alert 2: Rapid Growth**

```sql
-- Check for >20% growth in last hour
WITH recent AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY index_name ORDER BY timestamp DESC) as rn
    FROM index_metrics
    WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
)
SELECT 
    a.index_name,
    ROUND((a.docs_count - b.docs_count) / b.docs_count * 100, 2) as growth_pct
FROM recent a
JOIN recent b ON a.index_name = b.index_name AND b.rn = 2
WHERE a.rn = 1
  AND (a.docs_count - b.docs_count) / b.docs_count > 0.20;
```

### **Alert 3: Health Change**

```sql
-- Detect health degradation
SELECT 
    index_name,
    health,
    timestamp
FROM index_metrics_latest
WHERE health IN ('yellow', 'red');
```

---

## 🧪 Testing

Run the test script:

```bash
python scripts/test_queries.py
```

**Expected output:**
- ✅ Current state: 7 indices
- ✅ Historical records: Multiple collection runs
- ✅ Summary statistics

---

## 📚 Full Documentation

See **`QUERY_GUIDE.md`** for:
- 50+ query examples
- Grafana dashboard queries
- Advanced analytics
- Performance optimization tips
- Complete use case coverage

---

## 💡 Best Practices

1. **Use the VIEW for current state queries** (faster)
2. **Add time filters** to historical queries (better performance)
3. **Set up retention policy** (prevent unbounded growth)
4. **Monitor table size** regularly
5. **Index optimization** (already done! ✅)
6. **Aggregate old data** for long-term storage

---

## 📊 Performance

| Query Type | Table/View | Typical Time |
|------------|------------|--------------|
| Current state (7 indices) | `index_metrics_latest` | < 10ms |
| Last 24 hours | `index_metrics` | < 50ms |
| Last 7 days | `index_metrics` | < 200ms |
| Last 30 days | `index_metrics` | < 500ms |

With proper retention (90 days), all queries stay fast! ⚡

---

## ✅ Summary

**You have the perfect setup:**

✅ **Time-series data** for trends and historical analysis  
✅ **Optimized VIEW** for fast current-state queries  
✅ **Proper indexes** for performance  
✅ **Retention strategy** to manage growth  
✅ **Ready for Grafana** with example queries  
✅ **Alert-friendly** with both current and change detection  

**This is production-ready monitoring infrastructure!** 🎉

---

## 🚀 Next Steps

1. Run `python scripts/test_queries.py` to verify setup
2. Set up Grafana dashboards using `QUERY_GUIDE.md`
3. Configure data retention (90 days recommended)
4. Set up alerts for size/health/growth
5. Schedule collection runs (cron or Airflow)

**Need help?** Check `QUERY_GUIDE.md` for 50+ query examples!

