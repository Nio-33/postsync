#!/bin/bash
# PostSync Deployment Script
# Deploys PostSync to Google Cloud Run

set -euo pipefail

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-postsync-prod}"
SERVICE_NAME="postsync-api"
REGION="${DEPLOY_REGION:-us-central1}"
ENVIRONMENT="${1:-staging}"

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

# Check if required tools are installed
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install Google Cloud SDK."
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Authenticate with Google Cloud
authenticate() {
    log_info "Authenticating with Google Cloud..."
    
    # Check if already authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        log_warning "Not authenticated with Google Cloud. Please run 'gcloud auth login'"
        exit 1
    fi
    
    # Set project
    gcloud config set project "$PROJECT_ID"
    
    # Configure Docker for GCR
    gcloud auth configure-docker --quiet
    
    log_success "Authentication completed"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    
    local image_tag="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${ENVIRONMENT}-$(date +%Y%m%d%H%M%S)"
    local latest_tag="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${ENVIRONMENT}-latest"
    
    docker build -t "$image_tag" -t "$latest_tag" .
    
    log_success "Docker image built: $image_tag"
    echo "$image_tag" > .last_image_tag
}

# Push Docker image
push_image() {
    log_info "Pushing Docker image to Google Container Registry..."
    
    local image_tag=$(cat .last_image_tag)
    local latest_tag="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${ENVIRONMENT}-latest"
    
    docker push "$image_tag"
    docker push "$latest_tag"
    
    log_success "Docker image pushed to GCR"
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
    log_info "Deploying to Cloud Run..."
    
    local image_tag=$(cat .last_image_tag)
    local service_name="${SERVICE_NAME}"
    
    if [ "$ENVIRONMENT" != "production" ]; then
        service_name="${SERVICE_NAME}-${ENVIRONMENT}"
    fi
    
    # Set environment-specific configuration
    local memory="1Gi"
    local cpu="1"
    local min_instances="0"
    local max_instances="10"
    local concurrency="100"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        memory="2Gi"
        cpu="2"
        min_instances="1"
        max_instances="100"
    fi
    
    # Deploy to Cloud Run
    gcloud run deploy "$service_name" \
        --image "$image_tag" \
        --region "$REGION" \
        --platform managed \
        --allow-unauthenticated \
        --set-env-vars "ENVIRONMENT=${ENVIRONMENT}" \
        --set-env-vars "DEBUG=false" \
        --memory "$memory" \
        --cpu "$cpu" \
        --min-instances "$min_instances" \
        --max-instances "$max_instances" \
        --concurrency "$concurrency" \
        --timeout 300 \
        --execution-environment gen2 \
        --quiet
    
    log_success "Deployment to Cloud Run completed"
}

# Get service URL
get_service_url() {
    local service_name="${SERVICE_NAME}"
    
    if [ "$ENVIRONMENT" != "production" ]; then
        service_name="${SERVICE_NAME}-${ENVIRONMENT}"
    fi
    
    local url=$(gcloud run services describe "$service_name" \
        --region "$REGION" \
        --format 'value(status.url)')
    
    echo "$url"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    local url=$(get_service_url)
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url/health" > /dev/null; then
            log_success "Health check passed"
            return 0
        fi
        
        log_info "Health check attempt $attempt/$max_attempts failed, retrying in 10 seconds..."
        sleep 10
        ((attempt++))
    done
    
    log_error "Health check failed after $max_attempts attempts"
    return 1
}

# Run database migrations (if needed)
run_migrations() {
    if [ "$ENVIRONMENT" = "production" ]; then
        log_info "Running database migrations..."
        
        # Set up environment for migration
        export ENVIRONMENT="production"
        export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
        
        # Run migration script
        if [ -f "scripts/migrate.py" ]; then
            python scripts/migrate.py
            log_success "Database migrations completed"
        else
            log_warning "No migration script found, skipping migrations"
        fi
    fi
}

# Update traffic allocation
update_traffic() {
    if [ "$ENVIRONMENT" = "production" ]; then
        log_info "Updating traffic allocation to latest revision..."
        
        gcloud run services update-traffic "$SERVICE_NAME" \
            --region "$REGION" \
            --to-latest \
            --quiet
        
        log_success "Traffic updated to latest revision"
    fi
}

# Cleanup old revisions
cleanup_revisions() {
    log_info "Cleaning up old revisions..."
    
    local service_name="${SERVICE_NAME}"
    if [ "$ENVIRONMENT" != "production" ]; then
        service_name="${SERVICE_NAME}-${ENVIRONMENT}"
    fi
    
    # Keep only the last 5 revisions
    local revisions=$(gcloud run revisions list \
        --service "$service_name" \
        --region "$REGION" \
        --format "value(metadata.name)" \
        --sort-by "~metadata.creationTimestamp" \
        | tail -n +6)
    
    if [ -n "$revisions" ]; then
        echo "$revisions" | while read -r revision; do
            gcloud run revisions delete "$revision" --region "$REGION" --quiet
            log_info "Deleted old revision: $revision"
        done
    fi
    
    log_success "Cleanup completed"
}

# Main deployment function
main() {
    log_info "Starting PostSync deployment to $ENVIRONMENT environment"
    
    check_prerequisites
    authenticate
    build_image
    push_image
    deploy_to_cloud_run
    
    if health_check; then
        run_migrations
        update_traffic
        cleanup_revisions
        
        local url=$(get_service_url)
        log_success "Deployment completed successfully!"
        log_info "Service URL: $url"
        log_info "API Documentation: $url/docs"
    else
        log_error "Deployment failed health check"
        exit 1
    fi
    
    # Cleanup
    rm -f .last_image_tag
}

# Help function
show_help() {
    cat << EOF
PostSync Deployment Script

Usage: $0 [ENVIRONMENT]

ENVIRONMENT:
    staging     Deploy to staging environment (default)
    production  Deploy to production environment

Environment Variables:
    GOOGLE_CLOUD_PROJECT    Google Cloud project ID (default: postsync-prod)
    DEPLOY_REGION          Deployment region (default: us-central1)

Examples:
    $0                      # Deploy to staging
    $0 staging             # Deploy to staging
    $0 production          # Deploy to production

Requirements:
    - Google Cloud SDK (gcloud)
    - Docker
    - Authenticated with Google Cloud
EOF
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    staging|production|"")
        main
        ;;
    *)
        log_error "Invalid environment: $1"
        echo
        show_help
        exit 1
        ;;
esac