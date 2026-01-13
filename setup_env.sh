#!/bin/bash
# Environment Setup Script for Elasticsearch Metrics Collection System

set -e

echo "=========================================="
echo "Environment Setup Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if .env.template exists
if [ ! -f ".env.template" ]; then
    print_error ".env.template not found!"
    exit 1
fi

echo "Choose environment to set up:"
echo "1) Local Development (.env)"
echo "2) Staging (.env.staging)"
echo "3) Production (.env.production)"
echo "4) All environments"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        ENV_FILES=(".env")
        ;;
    2)
        ENV_FILES=(".env.staging")
        ;;
    3)
        ENV_FILES=(".env.production")
        ;;
    4)
        ENV_FILES=(".env" ".env.staging" ".env.production")
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

echo ""

for env_file in "${ENV_FILES[@]}"; do
    if [ -f "$env_file" ]; then
        read -p "$env_file already exists. Overwrite? [y/N]: " overwrite
        if [[ ! $overwrite =~ ^[Yy]$ ]]; then
            print_warning "Skipping $env_file"
            continue
        fi
    fi
    
    cp .env.template "$env_file"
    print_success "Created $env_file"
    
    # Set appropriate ENV value
    case $env_file in
        ".env")
            sed -i '' 's/ENV=STAGING/ENV=STAGING/' "$env_file"
            sed -i '' 's/LOCAL_DEV_MODE=false/LOCAL_DEV_MODE=true/' "$env_file"
            print_success "Configured for local development"
            ;;
        ".env.staging")
            sed -i '' 's/ENV=STAGING/ENV=STAGING/' "$env_file"
            print_success "Configured for staging"
            ;;
        ".env.production")
            sed -i '' 's/ENV=STAGING/ENV=PRODUCTION/' "$env_file"
            print_success "Configured for production"
            ;;
    esac
    
    # Set appropriate permissions
    chmod 600 "$env_file"
    print_success "Set permissions to 600"
    
    echo ""
done

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit the environment file(s) with your actual credentials"
echo "2. Never commit .env files to git (already in .gitignore)"
echo "3. Test configuration: python main.py health-check --env STAGING"
echo ""
echo "Files created:"
for env_file in "${ENV_FILES[@]}"; do
    if [ -f "$env_file" ]; then
        echo "  - $env_file"
    fi
done
echo ""
echo "For more information, see ENVIRONMENT_SETUP.md"
echo ""

