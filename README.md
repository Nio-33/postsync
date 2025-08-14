# PostSync 🚀

*Synchronize your success in the AI world*

PostSync is an intelligent social media automation platform specifically designed for AI professionals, engineers, and startup founders. It automatically discovers trending AI business news, generates engaging content using advanced AI, and publishes optimized posts across LinkedIn and Twitter.

## 🎯 Features

- **Intelligent Content Discovery**: Automatically finds relevant AI business news from Reddit r/AIBusiness and other sources
- **AI-Powered Content Generation**: Uses Google Gemini AI to create professional, engaging posts
- **Multi-Platform Publishing**: Optimized posting for LinkedIn and Twitter with platform-specific content
- **Smart Scheduling**: AI-optimized posting times based on audience engagement patterns
- **Performance Analytics**: Track engagement, reach, and content performance across platforms
- **Zero-Effort Automation**: Set it and forget it - runs completely automatically

## 🏗️ Architecture

PostSync is built on Google Cloud Platform with a microservices architecture:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Content       │    │   AI Generation  │    │   Publishing    │
│   Discovery     │────│   Service        │────│   Engine        │
│   (Cloud Run)   │    │   (Gemini AI)    │    │   (Social APIs) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Firestore     │
                    │   (Database)    │
                    └─────────────────┘
```

## 🛠️ Tech Stack

- **Backend**: Python 3.12+ with FastAPI
- **Frontend**: Vanilla HTML/CSS/JavaScript with modern design
- **Cloud**: Google Cloud Platform (Cloud Run, Firestore, Secret Manager, Scheduler)
- **AI**: Google Gemini API for content generation
- **APIs**: Reddit (PRAW), LinkedIn API, Twitter API v2
- **Database**: Firestore (Firebase)
- **Web Server**: Nginx for static file serving and reverse proxy
- **Deployment**: Docker with GitHub Actions CI/CD

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Google Cloud Account with billing enabled
- Reddit, LinkedIn, and Twitter API credentials

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/postsync/postsync.git
   cd postsync
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API credentials
   ```

5. **Set up Google Cloud authentication**
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

6. **Run the development server**
   ```bash
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Serve the frontend (in another terminal)**
   ```bash
   cd frontend
   python -m http.server 8080
   ```

8. **Access the application**
   - Frontend: http://localhost:8080 (Landing page and dashboard)
   - API documentation: http://localhost:8000/docs (Swagger UI)
   - API documentation: http://localhost:8000/redoc (ReDoc)

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_content_discovery.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## 📁 Project Structure

```
postsync/
├── src/                     # Backend API source code
│   ├── api/                 # FastAPI endpoints
│   │   ├── __init__.py
│   │   ├── auth.py         # Authentication endpoints
│   │   ├── content.py      # Content management endpoints
│   │   ├── analytics.py    # Analytics endpoints
│   │   └── users.py        # User management endpoints
│   ├── services/            # Business logic services
│   │   ├── __init__.py
│   │   ├── content_discovery.py
│   │   ├── content_generation.py
│   │   ├── publishing.py
│   │   ├── analytics.py
│   │   └── scheduling.py
│   ├── models/              # Data models and schemas
│   │   ├── __init__.py
│   │   ├── content.py
│   │   ├── user.py
│   │   ├── analytics.py
│   │   └── schemas/
│   ├── integrations/        # External API integrations
│   │   ├── __init__.py
│   │   ├── reddit.py
│   │   ├── linkedin.py
│   │   ├── twitter.py
│   │   └── firestore.py
│   ├── ai/                  # AI content generation
│   │   ├── __init__.py
│   │   ├── gemini.py
│   │   ├── content_optimizer.py
│   │   └── prompt_templates.py
│   ├── utils/               # Utility functions
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── validators.py
│   │   └── helpers.py
│   ├── config/              # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── database.py
│   └── main.py              # Application entry point
├── frontend/                # Frontend web application
│   ├── index.html          # Landing page with authentication
│   ├── dashboard.html      # Main dashboard interface
│   ├── css/                # Stylesheets
│   │   ├── styles.css      # Main landing page styles
│   │   └── dashboard.css   # Dashboard-specific styles
│   └── js/                 # JavaScript modules
│       ├── app.js          # Main application logic
│       └── dashboard.js    # Dashboard functionality
├── tests/                   # Test suites
│   ├── __init__.py
│   ├── test_api/
│   ├── test_services/
│   ├── test_integrations/
│   ├── test_ai/
│   └── conftest.py
├── docs/                    # Documentation
│   ├── api.md
│   ├── deployment.md
│   └── development.md
├── infrastructure/          # Cloud infrastructure configs
│   ├── terraform/
│   └── kubernetes/
├── scripts/                 # Deployment and utility scripts
│   ├── deploy.sh
│   ├── setup.sh
│   └── migrate.py
├── templates/               # Content generation templates
│   ├── linkedin/
│   └── twitter/
├── .github/                 # GitHub Actions workflows
│   └── workflows/
├── nginx.conf              # Nginx configuration for frontend
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

## 🔧 Configuration

### Environment Variables

Key environment variables to configure:

- `GOOGLE_CLOUD_PROJECT`: Your GCP project ID
- `GEMINI_API_KEY`: Google Gemini API key
- `REDDIT_CLIENT_ID/SECRET`: Reddit API credentials
- `LINKEDIN_CLIENT_ID/SECRET`: LinkedIn API credentials
- `TWITTER_API_KEY/SECRET`: Twitter API credentials

See `.env.example` for a complete list.

### Google Cloud Setup

1. **Enable required APIs**:
   - Cloud Run API
   - Cloud Firestore API
   - Cloud Scheduler API
   - Secret Manager API

2. **Create service account**:
   ```bash
   gcloud iam service-accounts create postsync-service \
     --display-name="PostSync Service Account"
   ```

3. **Grant permissions**:
   ```bash
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:postsync-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/datastore.user"
   ```

## 🚀 Deployment

### Deploy to Google Cloud Run

```bash
# Build and deploy
./scripts/deploy.sh production

# Or manually:
gcloud run deploy postsync \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Docker Deployment

```bash
# Build image
docker build -t postsync:latest .

# Run with Docker Compose (includes frontend and nginx)
docker-compose --profile with-nginx up -d

# Or run backend only
docker run -p 8000:8000 --env-file .env postsync:latest
```

## 📊 Monitoring

PostSync includes comprehensive monitoring and logging:

- **Health Checks**: `/health` endpoint for service monitoring
- **Metrics**: Built-in Prometheus metrics for Cloud Monitoring
- **Logging**: Structured logging with Google Cloud Logging
- **Error Tracking**: Sentry integration for error monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write tests for new functionality
- Update documentation for API changes
- Use type hints for all functions
- Run tests and linting before committing

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs.postsync.com](https://docs.postsync.com)
- **Issues**: [GitHub Issues](https://github.com/postsync/postsync/issues)
- **Email**: support@postsync.com
- **Discord**: [PostSync Community](https://discord.gg/postsync)

## 🎯 Roadmap

- [ ] Multi-language content generation
- [ ] Instagram and YouTube integration
- [ ] Advanced analytics dashboard
- [ ] Team collaboration features
- [ ] Mobile app (iOS/Android)

---

**PostSync** - *Synchronize your success in the AI world* 🚀

Made with ❤️ for the AI community