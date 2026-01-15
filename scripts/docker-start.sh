#!/bin/bash
# Quick start script for Elasticsearch + MySQL test environment

echo "🚀 Starting Elasticsearch + MySQL test environment..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Start containers
echo "📦 Starting containers..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check Elasticsearch
echo ""
echo "🔍 Checking Elasticsearch..."
if curl -s http://localhost:9200 > /dev/null; then
    echo "✅ Elasticsearch is running at http://localhost:9200"
    echo ""
    echo "Cluster info:"
    curl -s http://localhost:9200 | jq '.' 2>/dev/null || curl -s http://localhost:9200
else
    echo "⚠️  Elasticsearch is starting... (this may take 30-60 seconds)"
    echo "   Run: docker-compose logs -f elasticsearch"
fi

# Check MySQL
echo ""
echo "🔍 Checking MySQL..."
if docker exec elasmetrics-mysql mysqladmin ping -h localhost -u root -pchangeme > /dev/null 2>&1; then
    echo "✅ MySQL is running at localhost:3306"
    echo "   Database: elasticsearch_metrics"
    echo "   User: metrics_user"
    echo "   Password: metrics_password"
else
    echo "⚠️  MySQL is starting..."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Test Elasticsearch:"
echo "   curl http://localhost:9200"
echo ""
echo "2. Populate with sample data:"
echo "   ./docker-populate-sample-data.sh"
echo ""
echo "3. Run health check:"
echo "   python main.py health-check"
echo ""
echo "4. Collect metrics:"
echo "   python main.py collect"
echo ""
echo "5. View logs:"
echo "   docker-compose logs -f"
echo ""
echo "6. Stop containers:"
echo "   docker-compose down"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

