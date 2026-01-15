#!/bin/bash
# Example run script

echo "================================"
echo "Elasticsearch Metrics Collection"
echo "================================"
echo ""

# Virtual environment checks
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "✓ Virtual environment found"
    source venv/bin/activate
fi

echo ""
echo "1. Running health check..."
python main.py health-check

echo ""
echo "2. Starting metrics collection..."
python main.py collect

echo ""
echo "✓ Process completed!"
echo "Log file: logs/elastic_metrics.log"

