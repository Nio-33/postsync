#!/bin/bash
# PostSync Development Setup Script
# Sets up the development environment for PostSync

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.12+ is installed
check_python() {
    log_info "Checking Python version..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3.12 or later."
        exit 1
    fi
    
    local python_version=$(python3 --version | cut -d' ' -f2)
    local major_version=$(echo "$python_version" | cut -d'.' -f1)
    local minor_version=$(echo "$python_version" | cut -d'.' -f2)
    
    if [ "$major_version" -lt 3 ] || ([ "$major_version" -eq 3 ] && [ "$minor_version" -lt 12 ]); then
        log_error "Python 3.12 or later is required. Current version: $python_version"
        exit 1
    fi
    
    log_success "Python version check passed: $python_version"
}

# Create virtual environment
create_venv() {
    log_info "Creating virtual environment..."
    
    if [ -d "venv" ]; then
        log_warning "Virtual environment already exists. Removing and recreating..."
        rm -rf venv
    fi
    
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    log_success "Virtual environment created and activated"
}

# Install dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Ensure virtual environment is activated
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        source venv/bin/activate
    fi
    
    # Install main dependencies
    pip install -r requirements.txt
    
    # Install development dependencies
    pip install pytest pytest-asyncio pytest-cov black flake8 isort mypy
    
    log_success "Dependencies installed successfully"
}

# Set up environment configuration
setup_environment() {
    log_info "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_info "Created .env file from .env.example"
            log_warning "Please update .env file with your actual API credentials"
        else
            log_warning ".env.example not found. Please create .env file manually"
        fi
    else
        log_info ".env file already exists"
    fi
    
    # Create necessary directories
    mkdir -p logs temp cache
    
    log_success "Environment configuration completed"
}

# Set up pre-commit hooks
setup_pre_commit() {
    log_info "Setting up pre-commit hooks..."
    
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        source venv/bin/activate
    fi
    
    # Install pre-commit
    pip install pre-commit
    
    # Create pre-commit configuration
    cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3
        
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
EOF
    
    # Install pre-commit hooks
    pre-commit install
    
    log_success "Pre-commit hooks installed"
}

# Check Google Cloud setup
check_gcloud() {
    log_info "Checking Google Cloud setup..."
    
    if ! command -v gcloud &> /dev/null; then
        log_warning "Google Cloud SDK not found. Please install it for cloud features."
        log_info "Visit: https://cloud.google.com/sdk/docs/install"
    else
        local gcloud_config=$(gcloud config get-value project 2>/dev/null || echo "")
        if [ -z "$gcloud_config" ]; then
            log_warning "Google Cloud project not configured. Run 'gcloud init' to set up."
        else
            log_success "Google Cloud SDK configured with project: $gcloud_config"
        fi
    fi
}

# Check Docker setup
check_docker() {
    log_info "Checking Docker setup..."
    
    if ! command -v docker &> /dev/null; then
        log_warning "Docker not found. Please install Docker for containerization."
        log_info "Visit: https://docs.docker.com/get-docker/"
    else
        if docker info &> /dev/null; then
            log_success "Docker is installed and running"
        else
            log_warning "Docker is installed but not running. Please start Docker."
        fi
    fi
}

# Run initial tests
run_tests() {
    log_info "Running initial tests..."
    
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        source venv/bin/activate
    fi
    
    # Run basic tests to ensure setup is working
    if [ -d "tests" ]; then
        python -m pytest tests/ -v --tb=short
        log_success "Initial tests passed"
    else
        log_warning "No tests directory found. Skipping test run."
    fi
}

# Create development database (if using PostgreSQL locally)
setup_local_db() {
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        log_info "Setting up local development database..."
        
        # Start PostgreSQL container for local development
        docker run -d \
            --name postsync-postgres \
            -e POSTGRES_DB=postsync_dev \
            -e POSTGRES_USER=postsync \
            -e POSTGRES_PASSWORD=dev_password \
            -p 5432:5432 \
            postgres:15-alpine || log_warning "Database container might already exist"
        
        log_success "Local PostgreSQL database started (optional for Firestore alternative)"
    fi
}

# Display next steps
show_next_steps() {
    cat << EOF

${GREEN}✅ PostSync development environment setup completed!${NC}

${BLUE}Next Steps:${NC}

1. ${YELLOW}Activate virtual environment:${NC}
   source venv/bin/activate

2. ${YELLOW}Update environment configuration:${NC}
   Edit .env file with your API credentials:
   - GEMINI_API_KEY
   - REDDIT_CLIENT_ID/SECRET
   - LINKEDIN_CLIENT_ID/SECRET
   - TWITTER_API_KEY/SECRET/BEARER_TOKEN

3. ${YELLOW}Set up Google Cloud authentication:${NC}
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID

4. ${YELLOW}Start the development server:${NC}
   uvicorn src.main:app --reload

5. ${YELLOW}View API documentation:${NC}
   http://localhost:8000/docs

6. ${YELLOW}Run tests:${NC}
   pytest

7. ${YELLOW}Format code:${NC}
   black src/ tests/
   isort src/ tests/

${BLUE}Development Commands:${NC}
- Start app: uvicorn src.main:app --reload
- Run tests: pytest
- Code format: black src/ tests/
- Type check: mypy src/
- Docker build: docker build -t postsync .
- Docker run: docker-compose up

${BLUE}Useful Resources:${NC}
- API Documentation: http://localhost:8000/docs
- Project README: README.md
- Environment Config: .env
- Docker Compose: docker-compose.yml

${GREEN}Happy coding! 🚀${NC}
EOF
}

# Help function
show_help() {
    cat << EOF
PostSync Development Setup Script

This script sets up the development environment for PostSync including:
- Python virtual environment
- Dependencies installation
- Environment configuration
- Development tools setup
- Optional Docker and Google Cloud checks

Usage: $0 [OPTIONS]

Options:
    --skip-tests        Skip running initial tests
    --skip-docker       Skip Docker setup check
    --skip-gcloud       Skip Google Cloud setup check
    --skip-db           Skip local database setup
    -h, --help          Show this help message

Examples:
    $0                  # Full setup
    $0 --skip-tests     # Setup without running tests
    $0 --skip-docker --skip-gcloud  # Skip optional components
EOF
}

# Main setup function
main() {
    log_info "Starting PostSync development environment setup"
    
    local skip_tests=false
    local skip_docker=false
    local skip_gcloud=false
    local skip_db=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-tests)
                skip_tests=true
                shift
                ;;
            --skip-docker)
                skip_docker=true
                shift
                ;;
            --skip-gcloud)
                skip_gcloud=true
                shift
                ;;
            --skip-db)
                skip_db=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Run setup steps
    check_python
    create_venv
    install_dependencies
    setup_environment
    setup_pre_commit
    
    if [ "$skip_gcloud" = false ]; then
        check_gcloud
    fi
    
    if [ "$skip_docker" = false ]; then
        check_docker
    fi
    
    if [ "$skip_db" = false ]; then
        setup_local_db
    fi
    
    if [ "$skip_tests" = false ]; then
        run_tests
    fi
    
    show_next_steps
}

# Run main function with all arguments
main "$@"