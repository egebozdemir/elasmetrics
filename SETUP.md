# Hızlı Başlangıç Kılavuzu

Bu döküman, projeyi hızlıca ayağa kaldırmak için adım adım talimatlar içerir.

## Ön Gereksinimler

1. **Python 3.8+** yüklü olmalı
2. **MySQL/MariaDB** yüklü ve çalışır durumda olmalı
3. **Elasticsearch** cluster'ına erişim

## Kurulum Adımları

### 1. Python Virtual Environment

```bash
cd /Users/ege.bozdemir/Desktop/EGE/projects/elastic-metrics

# Virtual environment oluştur
python3 -m venv venv

# Aktif et
source venv/bin/activate
```

### 2. Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
```

### 3. MySQL Veritabanı Hazırlığı

```bash
# MySQL'e bağlan
mysql -u root -p

# Veritabanı oluştur
CREATE DATABASE elasticsearch_metrics CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Kullanıcı oluştur (opsiyonel)
CREATE USER 'metrics_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON elasticsearch_metrics.* TO 'metrics_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 4. Konfigürasyonu Düzenle

`config/config.yaml` dosyasını düzenleyin:

```yaml
elasticsearch:
  hosts:
    - "http://your-elasticsearch:9200"
  # Eğer authentication gerekiyorsa:
  # username: "elastic"
  # password: "your-password"

mysql:
  host: "localhost"
  port: 3306
  database: "elasticsearch_metrics"
  user: "metrics_user"  # veya root
  password: "secure_password"
```

### 5. Bağlantıları Test Et

```bash
python main.py health-check
```

Başarılı output:

```
============================================================
HEALTH CHECK RESULTS
============================================================
Overall Status: HEALTHY
Timestamp: 2026-01-13T...

Elasticsearch:
  Status: healthy
  cluster_name: your-cluster
  version: 8.x.x

MySQL:
  Status: healthy
  host: localhost
  database: elasticsearch_metrics
============================================================
```

### 6. İlk Metrik Toplama

```bash
python main.py collect
```

## İleri Seviye Konfigürasyon

### Environment Variables Kullanımı

Hassas bilgileri environment variable'larda tutmak için:

```bash
# .env dosyası oluştur
cat > .env << EOF
ES_HOSTS=http://your-elasticsearch:9200
ES_USERNAME=elastic
ES_PASSWORD=your-password

MYSQL_HOST=localhost
MYSQL_DATABASE=elasticsearch_metrics
MYSQL_USER=metrics_user
MYSQL_PASSWORD=secure_password
EOF

# Çalıştırırken environment variable'ları yükle
export $(cat .env | xargs)
python main.py collect
```

### Index Pattern Filtreleme

`config/config.yaml` içinde:

```yaml
metrics:
  # Sadece belirli pattern'leri topla
  include_patterns:
    - "logs-*"
    - "metrics-*"
    - "your-app-*"
  
  # System index'leri hariç tut
  exclude_patterns:
    - ".*"          # Tüm hidden index'ler
    - ".security*"
    - ".kibana*"
```

## Otomatik Çalıştırma (Cron)

Her gün saat 02:00'da otomatik çalışması için:

```bash
# Crontab'ı düzenle
crontab -e

# Aşağıdaki satırı ekle (path'leri kendinize göre düzenleyin)
0 2 * * * cd /Users/ege.bozdemir/Desktop/EGE/projects/elastic-metrics && /Users/ege.bozdemir/Desktop/EGE/projects/elastic-metrics/venv/bin/python main.py collect >> logs/cron.log 2>&1
```

## Grafana Kurulumu

### 1. MySQL Data Source Ekle

Grafana UI:
1. Configuration → Data Sources
2. Add data source → MySQL
3. Bilgileri gir ve "Save & Test"

### 2. Dashboard İçe Aktar

Örnek dashboard oluşturma:

1. Create → Dashboard
2. Add new panel
3. Query:
   ```sql
   SELECT
     timestamp as time,
     index_name,
     store_size_bytes / 1024 / 1024 / 1024 as size_gb
   FROM index_metrics
   WHERE $__timeFilter(timestamp)
   ORDER BY timestamp
   ```

### 3. Alert Kuralları

Büyük index'ler için alert:

```sql
SELECT
  index_name,
  store_size_bytes / 1024 / 1024 / 1024 as size_gb,
  pri_shards
FROM index_metrics
WHERE 
  timestamp = (SELECT MAX(timestamp) FROM index_metrics)
  AND store_size_bytes > 50 * 1024 * 1024 * 1024  -- 50 GB
  AND pri_shards < 3  -- Yetersiz shard
```

## Sorun Giderme

### Problem: Elasticsearch'e bağlanamıyor

```bash
# Elasticsearch erişimini test et
curl http://your-elasticsearch:9200

# Authentication ile
curl -u username:password http://your-elasticsearch:9200
```

### Problem: MySQL bağlantı hatası

```bash
# MySQL servisini kontrol et
systemctl status mysql

# Port kontrolü
netstat -an | grep 3306

# Bağlantı testi
mysql -h localhost -u metrics_user -p elasticsearch_metrics
```

### Problem: Log dosyası oluşmuyor

```bash
# logs klasörü oluştur
mkdir -p logs

# İzinleri kontrol et
chmod 755 logs

# Manuel test
python main.py collect
tail -f logs/elastic_metrics.log
```

## Sonraki Adımlar

1. ✅ Projeyi çalışır duruma getir
2. ✅ İlk metrik toplanmasını yap
3. ✅ Grafana dashboard'ları oluştur
4. ⏭️ Slack alert entegrasyonu (gelecek adımlar için)
5. ⏭️ Shard size bazlı aksiyon alarmları

## Yardım

Daha fazla bilgi için:
- `README.md` - Detaylı dokümantasyon
- `python main.py --help` - CLI yardımı
- `logs/elastic_metrics.log` - Uygulama logları

