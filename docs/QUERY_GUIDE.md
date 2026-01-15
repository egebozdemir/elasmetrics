# 📊 Query Guide - Time-Series Metrics & Current State

## 🎯 Overview

Your setup now supports **BOTH** use cases:
- ✅ **Historical tracking** - Time-series data for trends, growth analysis, and alerting
- ✅ **Current state** - Fast queries for latest metrics via optimized VIEW

---

## 🏗️ Database Structure

### **Table: `index_metrics`**
**Purpose:** Full historical time-series data  
**Storage:** All metric snapshots from every collection run  
**Best for:** Trend analysis, growth tracking, historical queries

### **View: `index_metrics_latest`**
**Purpose:** Current state (latest metrics per index)  
**Performance:** Optimized with indexed joins  
**Best for:** Dashboards showing "right now", current cluster status, real-time monitoring

---

## 📈 Use Case 1: Current State Queries (Fast)

### **Get Current Status of All Indices**

```sql
-- Using the optimized VIEW (fastest!)
SELECT 
    index_name,
    docs_count,
    store_size_human,
    health,
    status,
    timestamp as last_collected
FROM index_metrics_latest
ORDER BY docs_count DESC;
```

**Example Output:**
```
index_name                  | docs_count | store_size_human | health | status | last_collected     
----------------------------+------------+------------------+--------+--------+--------------------
events-user-actions         | 10000      | 833.16 KB        | green  | open   | 2026-01-14 21:20:28
orders-2024-q1              | 3000       | 271.85 KB        | green  | open   | 2026-01-14 21:20:28
logs-app-2024.01.03         | 2000       | 332.28 KB        | yellow | open   | 2026-01-14 21:20:28
```

### **Current Status of Specific Index**

```sql
SELECT *
FROM index_metrics_latest
WHERE index_name = 'events-user-actions';
```

### **Current Health Summary**

```sql
SELECT 
    health,
    COUNT(*) as index_count,
    SUM(docs_count) as total_docs,
    SUM(store_size_bytes) as total_bytes
FROM index_metrics_latest
GROUP BY health;
```

### **Indices Using Most Storage (Right Now)**

```sql
SELECT 
    index_name,
    store_size_human,
    store_size_bytes,
    docs_count,
    ROUND(store_size_bytes / docs_count, 2) as bytes_per_doc
FROM index_metrics_latest
ORDER BY store_size_bytes DESC
LIMIT 10;
```

### **Python - Get Current State**

```python
from src.repositories import MySQLRepository

repository = MySQLRepository(config['mysql'])

# Get current state (latest for all indices)
current_state = repository.get_current_state()

for metric in current_state:
    print(f"{metric['index_name']}: {metric['docs_count']} docs, {metric['store_size_human']}")
```

---

## 📊 Use Case 2: Time-Series Analysis (Trends)

### **Track Index Growth Over Last 7 Days**

```sql
SELECT 
    DATE(timestamp) as date,
    index_name,
    MIN(docs_count) as min_docs,
    MAX(docs_count) as max_docs,
    MAX(docs_count) - MIN(docs_count) as docs_added,
    MIN(store_size_human) as min_size,
    MAX(store_size_human) as max_size
FROM index_metrics
WHERE index_name = 'events-user-actions'
  AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY DATE(timestamp), index_name
ORDER BY date;
```

### **Hourly Metrics for Today**

```sql
SELECT 
    HOUR(timestamp) as hour,
    index_name,
    AVG(docs_count) as avg_docs,
    MIN(docs_count) as min_docs,
    MAX(docs_count) as max_docs
FROM index_metrics
WHERE DATE(timestamp) = CURDATE()
  AND index_name = 'events-user-actions'
GROUP BY HOUR(timestamp), index_name
ORDER BY hour;
```

### **Growth Rate Calculation**

```sql
SELECT 
    index_name,
    MIN(timestamp) as first_seen,
    MAX(timestamp) as last_seen,
    MIN(docs_count) as initial_docs,
    MAX(docs_count) as current_docs,
    MAX(docs_count) - MIN(docs_count) as total_growth,
    ROUND((MAX(docs_count) - MIN(docs_count)) / NULLIF(MIN(docs_count), 0) * 100, 2) as growth_percent,
    MIN(store_size_bytes) as initial_bytes,
    MAX(store_size_bytes) as current_bytes,
    ROUND((MAX(store_size_bytes) - MIN(store_size_bytes)) / 1024 / 1024, 2) as growth_mb
FROM index_metrics
WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY index_name
ORDER BY total_growth DESC;
```

### **Compare Last 2 Collection Runs**

```sql
WITH ranked_metrics AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY index_name ORDER BY timestamp DESC) as rn
    FROM index_metrics
)
SELECT 
    a.index_name,
    a.docs_count as latest_docs,
    b.docs_count as previous_docs,
    a.docs_count - b.docs_count as docs_change,
    a.store_size_bytes as latest_bytes,
    b.store_size_bytes as previous_bytes,
    ROUND((a.store_size_bytes - b.store_size_bytes) / 1024, 2) as size_change_kb,
    a.timestamp as latest_time,
    b.timestamp as previous_time
FROM ranked_metrics a
LEFT JOIN ranked_metrics b ON a.index_name = b.index_name AND b.rn = 2
WHERE a.rn = 1;
```

### **Detect Indices with Rapid Growth**

```sql
SELECT 
    index_name,
    COUNT(*) as collection_count,
    MIN(docs_count) as min_docs,
    MAX(docs_count) as max_docs,
    MAX(docs_count) - MIN(docs_count) as docs_added,
    ROUND((MAX(docs_count) - MIN(docs_count)) / 
          TIMESTAMPDIFF(HOUR, MIN(timestamp), MAX(timestamp)), 2) as docs_per_hour
FROM index_metrics
WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY index_name
HAVING docs_added > 100  -- Alert threshold
ORDER BY docs_per_hour DESC;
```

---

## ⚡ Use Case 3: Grafana Dashboard Queries

### **Panel 1: Current Total Documents**

```sql
SELECT SUM(docs_count) as total_documents
FROM index_metrics_latest;
```

### **Panel 2: Current Total Storage**

```sql
SELECT ROUND(SUM(store_size_bytes) / 1024 / 1024 / 1024, 2) as total_gb
FROM index_metrics_latest;
```

### **Panel 3: Index Growth Over Time (Line Chart)**

```sql
SELECT 
    $__timeGroup(timestamp, '1h') as time,
    index_name,
    AVG(docs_count) as docs_count
FROM index_metrics
WHERE $__timeFilter(timestamp)
  AND index_name IN ($index_name)
GROUP BY time, index_name
ORDER BY time;
```

### **Panel 4: Storage Growth Over Time (Stacked Area Chart)**

```sql
SELECT 
    $__timeGroup(timestamp, '1h') as time,
    index_name,
    AVG(store_size_bytes) / 1024 / 1024 as size_mb
FROM index_metrics
WHERE $__timeFilter(timestamp)
GROUP BY time, index_name
ORDER BY time;
```

### **Panel 5: Health Status Distribution (Pie Chart)**

```sql
SELECT 
    health,
    COUNT(*) as count
FROM index_metrics_latest
GROUP BY health;
```

### **Panel 6: Top Growing Indices (Bar Chart)**

```sql
SELECT 
    index_name,
    MAX(docs_count) - MIN(docs_count) as growth
FROM index_metrics
WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY index_name
ORDER BY growth DESC
LIMIT 10;
```

---

## 🔔 Use Case 4: Alerting Queries

### **Indices Exceeding Size Threshold**

```sql
SELECT 
    index_name,
    store_size_human,
    store_size_bytes,
    docs_count
FROM index_metrics_latest
WHERE store_size_bytes > 500 * 1024 * 1024  -- 500 MB threshold
ORDER BY store_size_bytes DESC;
```

### **Indices with Yellow/Red Health**

```sql
SELECT 
    index_name,
    health,
    status,
    docs_count,
    store_size_human,
    timestamp
FROM index_metrics_latest
WHERE health IN ('yellow', 'red');
```

### **Rapid Growth Alert (>10% in last hour)**

```sql
WITH latest_two AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY index_name ORDER BY timestamp DESC) as rn
    FROM index_metrics
    WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
)
SELECT 
    a.index_name,
    a.docs_count as current_docs,
    b.docs_count as previous_docs,
    ROUND((a.docs_count - b.docs_count) / NULLIF(b.docs_count, 0) * 100, 2) as growth_percent,
    TIMESTAMPDIFF(MINUTE, b.timestamp, a.timestamp) as minutes_between
FROM latest_two a
JOIN latest_two b ON a.index_name = b.index_name AND b.rn = 2
WHERE a.rn = 1
  AND (a.docs_count - b.docs_count) / NULLIF(b.docs_count, 0) > 0.10
ORDER BY growth_percent DESC;
```

### **Indices Not Seen Recently**

```sql
SELECT 
    index_name,
    MAX(timestamp) as last_seen,
    TIMESTAMPDIFF(HOUR, MAX(timestamp), NOW()) as hours_ago
FROM index_metrics
GROUP BY index_name
HAVING hours_ago > 24
ORDER BY hours_ago DESC;
```

---

## 🧹 Use Case 5: Data Retention Management

### **Check Data Volume**

```sql
-- Total rows
SELECT COUNT(*) as total_rows FROM index_metrics;

-- Rows per day
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as row_count,
    COUNT(DISTINCT index_name) as index_count
FROM index_metrics
GROUP BY DATE(timestamp)
ORDER BY date DESC
LIMIT 30;

-- Table size
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb,
    table_rows
FROM information_schema.TABLES
WHERE table_schema = 'elasticsearch_metrics'
  AND table_name = 'index_metrics';
```

### **Delete Old Data (Keep 90 Days)**

```sql
-- Check what would be deleted
SELECT 
    COUNT(*) as rows_to_delete,
    MIN(timestamp) as oldest,
    MAX(timestamp) as newest
FROM index_metrics
WHERE timestamp < DATE_SUB(NOW(), INTERVAL 90 DAY);

-- Delete (run in production)
DELETE FROM index_metrics
WHERE timestamp < DATE_SUB(NOW(), INTERVAL 90 DAY);
```

### **Python - Automated Cleanup**

```python
from src.repositories import MySQLRepository

repository = MySQLRepository(config['mysql'])

# Delete metrics older than 90 days
deleted_count = repository.delete_old_metrics(days=90)
print(f"Deleted {deleted_count} old records")
```

---

## 🎨 Use Case 6: Advanced Analytics

### **Daily Aggregated Summary Table**

```sql
-- Create aggregated daily summary
CREATE TABLE index_metrics_daily_summary AS
SELECT 
    DATE(timestamp) as date,
    index_name,
    MIN(docs_count) as min_docs,
    MAX(docs_count) as max_docs,
    AVG(docs_count) as avg_docs,
    MAX(docs_count) - MIN(docs_count) as daily_growth,
    MIN(store_size_bytes) as min_bytes,
    MAX(store_size_bytes) as max_bytes,
    AVG(store_size_bytes) as avg_bytes,
    COUNT(*) as collection_count
FROM index_metrics
GROUP BY DATE(timestamp), index_name;

-- Query the summary (much faster than raw data)
SELECT * FROM index_metrics_daily_summary
WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
ORDER BY date DESC, index_name;
```

### **Moving Average (7-day)**

```sql
SELECT 
    timestamp,
    index_name,
    docs_count,
    AVG(docs_count) OVER (
        PARTITION BY index_name 
        ORDER BY timestamp 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as moving_avg_7day
FROM index_metrics
WHERE index_name = 'events-user-actions'
ORDER BY timestamp DESC;
```

### **Percentile Analysis**

```sql
-- 95th percentile of index sizes
WITH percentiles AS (
    SELECT 
        index_name,
        store_size_bytes,
        PERCENT_RANK() OVER (PARTITION BY index_name ORDER BY store_size_bytes) as percentile
    FROM index_metrics
)
SELECT 
    index_name,
    MIN(CASE WHEN percentile >= 0.95 THEN store_size_bytes END) / 1024 / 1024 as p95_size_mb,
    MAX(store_size_bytes) / 1024 / 1024 as max_size_mb
FROM percentiles
GROUP BY index_name;
```

---

## 🚀 Performance Tips

### **1. Use the VIEW for Current State**
```sql
-- ✅ FAST - Uses optimized VIEW
SELECT * FROM index_metrics_latest;

-- ❌ SLOWER - Raw table with subquery
SELECT * FROM index_metrics 
WHERE (index_name, timestamp) IN (
    SELECT index_name, MAX(timestamp) 
    FROM index_metrics 
    GROUP BY index_name
);
```

### **2. Add Indexes for Common Queries**
```sql
-- Already created! ✅
INDEX idx_index_name (index_name)
INDEX idx_timestamp (timestamp)
INDEX idx_index_timestamp (index_name, timestamp)
```

### **3. Use Date Filters**
```sql
-- ✅ GOOD - Uses index
WHERE timestamp >= '2026-01-10'

-- ❌ BAD - Full table scan
WHERE DATE(timestamp) = '2026-01-10'
```

### **4. Limit Result Sets**
```sql
-- Always use LIMIT for large result sets
SELECT * FROM index_metrics
ORDER BY timestamp DESC
LIMIT 1000;
```

---

## 📝 Summary

| Query Type | Table/View to Use | Performance | Use Case |
|------------|-------------------|-------------|----------|
| **Current state** | `index_metrics_latest` | ⚡ Fast | Dashboards, current status |
| **Trends/growth** | `index_metrics` | 📊 Medium | Historical analysis |
| **Specific date range** | `index_metrics` | 📊 Medium | Time-series charts |
| **Alerting (current)** | `index_metrics_latest` | ⚡ Fast | Real-time alerts |
| **Alerting (changes)** | `index_metrics` | 📊 Medium | Growth rate alerts |

---

**You now have the best of both worlds:**
- ✅ Full historical data for trends and analysis
- ✅ Fast current-state queries via optimized VIEW
- ✅ Ready for Grafana dashboards
- ✅ Supports alerting on both current values and changes

🎉 **Perfect setup for production monitoring!**

