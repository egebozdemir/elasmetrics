#!/bin/bash
# Setup MySQL database on your local Homebrew MySQL

echo "🗄️  Setting up database on local MySQL..."
echo ""

# Check if MySQL is running
if ! pgrep -x "mysqld" > /dev/null; then
    echo "⚠️  MySQL is not running. Starting..."
    brew services start mysql
    sleep 5
fi

# Create database and user
mysql -u root -p << 'EOF'
-- Create database if not exists
CREATE DATABASE IF NOT EXISTS elasticsearch_metrics CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user if not exists (MySQL 8.0+)
CREATE USER IF NOT EXISTS 'metrics_user'@'localhost' IDENTIFIED BY 'metrics_password';

-- Grant permissions
GRANT SELECT, INSERT, DELETE, CREATE, ALTER, INDEX ON elasticsearch_metrics.* TO 'metrics_user'@'localhost';

-- Show confirmation
SELECT 'Database and user created successfully!' AS Status;
SHOW DATABASES LIKE 'elasticsearch_metrics';

FLUSH PRIVILEGES;
EOF

echo ""
echo "✅ MySQL setup complete!"
echo ""
echo "Connection details:"
echo "  Host: localhost"
echo "  Port: 3306"
echo "  Database: elasticsearch_metrics"
echo "  User: metrics_user"
echo "  Password: metrics_password"
echo ""
echo "Update your .env file with these credentials."

