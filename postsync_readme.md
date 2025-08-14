# PostSync

> Intelligent social media automation for AI professionals

Automatically discover, curate, and post trending AI business news to LinkedIn and Twitter. Stay relevant, build influence, and grow your professional network—all while you focus on what matters most.

## 🌟 Overview

PostSync transforms how AI professionals manage their social media presence by:

- **🔍 Smart Discovery**: Monitors r/AIBusiness for trending industry news
- **🧠 AI Curation**: Uses Gemini AI to select and rank the most engaging content
- **✍️ Intelligent Writing**: Generates platform-optimized posts that sound authentically professional
- **📅 Automated Publishing**: Posts daily at 11:00 AM Lagos time across LinkedIn and Twitter
- **🛡️ Quality Control**: Prevents duplicates and ensures fact-checked, brand-safe content

**Built for busy professionals who want to maintain thought leadership without the time investment.**

## ✨ Key Features

### 🎯 **Content Intelligence**
- Scores posts using upvotes, comments, recency, and keyword relevance
- Filters for AI business impact and professional relevance
- Prevents duplicate content within 14-day windows
- Maintains comprehensive posting history and analytics

### 🤖 **AI-Powered Generation**
- **LinkedIn**: Professional 2-3 paragraph posts with engagement questions
- **Twitter**: Concise 200-280 character posts optimized for virality
- **Brand Consistency**: Maintains your professional voice across platforms
- **Zero Hallucinations**: Strict fact-checking against source material

### ⚡ **Reliable Automation**
- Cloud-native architecture with 99.9% uptime
- Intelligent error handling and retry mechanisms
- Comprehensive logging and performance monitoring
- Secure API credential management

## 🛠 Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Python 3.12 + FastAPI | Core application logic |
| **Cloud Platform** | Google Cloud Run | Serverless hosting |
| **Scheduler** | Cloud Scheduler + Pub/Sub | Daily automation triggers |
| **Database** | Firestore | Content history & analytics |
| **AI Engine** | Google Gemini API | Content generation |
| **Social APIs** | Reddit, LinkedIn, Twitter v2 | Platform integrations |
| **Secrets** | Google Secret Manager | Secure credential storage |
| **Deployment** | Docker + GitHub Actions | CI/CD pipeline |
| **Monitoring** | Cloud Logging + Error Reporting | System observability |

## 🚀 Quick Start

### Prerequisites

- Google Cloud Platform account with billing enabled
- API credentials for Reddit, LinkedIn, Twitter, and Gemini
- Python 3.12+ for local development

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/postsync.git
cd postsync

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Google Cloud

```bash
# Authenticate and set project
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required services
gcloud services enable \
  run.googleapis.com \
  scheduler.googleapis.com \
  pubsub.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com
```

### 3. Store API Credentials

```bash
# Reddit API
echo "your_reddit_client_id" | gcloud secrets create reddit-client-id --data-file=-
echo "your_reddit_client_secret" | gcloud secrets create reddit-client-secret --data-file=-

# LinkedIn API
echo "your_linkedin_access_token" | gcloud secrets create linkedin-access-token --data-file=-
echo "your_linkedin_client_id" | gcloud secrets create linkedin-client-id --data-file=-

# Twitter API
echo "your_twitter_api_key" | gcloud secrets create twitter-api-key --data-file=-
echo "your_twitter_api_secret" | gcloud secrets create twitter-api-secret --data-file=-
echo "your_twitter_access_token" | gcloud secrets create twitter-access-token --data-file=-
echo "your_twitter_access_token_secret" | gcloud secrets create twitter-access-token-secret --data-file=-

# Gemini AI
echo "your_gemini_api_key" | gcloud secrets create gemini-api-key --data-file=-
```

### 4. Deploy to Production

```bash
# Deploy to Cloud Run
gcloud run deploy postsync \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 300 \
  --max-instances 10

# Create Pub/Sub infrastructure
gcloud pubsub topics create postsync-trigger
gcloud pubsub subscriptions create postsync-subscription --topic=postsync-trigger

# Schedule daily execution
gcloud scheduler jobs create pubsub daily-postsync \
  --schedule="0 11 * * *" \
  --time-zone="Africa/Lagos" \
  --topic=postsync-trigger \
  --message-body='{"trigger": "daily_run"}'
```

## ⚙️ Configuration

### Environment Variables

Create `.env` for local development:

```env
# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
FIRESTORE_COLLECTION=postsync_posts

# Reddit Configuration
REDDIT_USER_AGENT=PostSync/1.0
REDDIT_SUBREDDIT=AIBusiness

# Content Settings
MIN_UPVOTES=10
MAX_POST_AGE_HOURS=24
CONTENT_HISTORY_DAYS=14

# AI Configuration
GEMINI_MODEL=gemini-1.5-flash
GENERATION_TEMPERATURE=0.3

# Logging
LOG_LEVEL=INFO
```

### Content Scoring Weights

Customize content selection in `config/scoring.py`:

```python
SCORING_CONFIG = {
    "weights": {
        "upvotes": 0.4,      # Reddit upvote count
        "comments": 0.3,     # Discussion activity
        "recency": 0.2,      # How recent the post is
        "keywords": 0.1      # Keyword relevance
    },
    "priority_keywords": [
        "funding", "acquisition", "IPO", "investment",
        "breakthrough", "launch", "partnership", 
        "AI startup", "venture capital", "unicorn"
    ],
    "minimum_score": 50  # Posts below this score are filtered out
}
```

## 📊 Usage

### Local Development

```bash
# Start development server
uvicorn main:app --reload --port 8000

# Test manual trigger
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -d '{"test_mode": true}'

# View system status
curl http://localhost:8000/health
```

### Production Management

```bash
# Manual content generation
gcloud pubsub topics publish postsync-trigger \
  --message='{"manual_trigger": true}'

# View recent logs
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=postsync" --limit 50

# Check system health
curl https://your-postsync-url.run.app/health
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/status` | GET | Detailed system status |
| `/trigger` | POST | Manual content generation |
| `/history` | GET | Recent post history |
| `/metrics` | GET | Performance analytics |

## 📈 Monitoring & Analytics

### Key Metrics Dashboard

PostSync tracks several important metrics:

- **Content Success Rate**: % of generated posts that meet quality standards
- **Engagement Performance**: Average engagement vs. your baseline
- **System Reliability**: Uptime and successful execution rate
- **Content Diversity**: Topic coverage and duplicate prevention
- **API Health**: Response times and error rates

### Setting Up Alerts

```bash
# Create alerting policy for failed executions
gcloud alpha monitoring policies create --policy-from-file=monitoring/alert-policy.yaml

# Set up Slack notifications (optional)
# Configure webhook URL in Google Cloud Functions
```

### Viewing Analytics

```bash
# Export performance data
curl https://your-postsync-url.run.app/metrics?format=csv > postsync-metrics.csv

# View engagement trends
curl https://your-postsync-url.run.app/analytics/engagement
```

## 🔧 Customization

### Brand Voice Configuration

Customize your content style in `config/brand_voice.json`:

```json
{
  "tone": "professional_thought_leader",
  "personality": ["knowledgeable", "optimistic", "engaging"],
  "content_style": {
    "linkedin": {
      "length": "200-300_words",
      "include_question": true,
      "hashtag_count": "3-5",
      "emoji_usage": "minimal"
    },
    "twitter": {
      "length": "220-280_chars",
      "hashtag_count": "1-2", 
      "emoji_usage": "strategic"
    }
  }
}
```

### Content Templates

Create custom post templates in `templates/`:

```python
# templates/linkedin_template.py
LINKEDIN_TEMPLATE = """
🚀 {hook}

{analysis}

{business_implications}

{engagement_question}

#{hashtags}

Source: {source_url}
"""
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v --cov=src/

# Test specific components
pytest tests/unit/test_content_generation.py -v
pytest tests/integration/test_api_flows.py -v

# Load testing
pytest tests/performance/ -v
```

### Test Coverage

```bash
# Generate coverage report
coverage run -m pytest tests/
coverage html
open htmlcov/index.html
```

## 🚨 Troubleshooting

### Common Issues

**🔴 Content Generation Failures**
```bash
# Check Gemini API quota and billing
gcloud logging read "severity>=ERROR AND textPayload:gemini" --limit 10

# Verify API key permissions
curl -H "Authorization: Bearer $GEMINI_API_KEY" https://generativelanguage.googleapis.com/v1/models
```

**🟡 Social Media Posting Errors**
```bash
# Verify LinkedIn token validity
curl -H "Authorization: Bearer $LINKEDIN_TOKEN" https://api.linkedin.com/v2/me

# Check Twitter API rate limits
curl -H "Authorization: Bearer $TWITTER_BEARER_TOKEN" \
  https://api.twitter.com/2/tweets/search/recent?query=test&max_results=10
```

**🟠 Scheduling Issues**
```bash
# Check Cloud Scheduler job status
gcloud scheduler jobs describe daily-postsync

# View Pub/Sub subscription health
gcloud pubsub subscriptions describe postsync-subscription
```

### Debug Mode

Enable detailed logging:

```bash
export LOG_LEVEL=DEBUG
export POSTSYNC_DEBUG=true
```

### Getting Help

1. **📖 Check the [FAQ](docs/FAQ.md)** for common questions
2. **🐛 Open an issue** on GitHub with detailed logs
3. **💬 Join our Discord** for community support
4. **📧 Email support** for enterprise customers

## 🗺️ Roadmap

### Version 1.1 (Next Quarter)
- [ ] Instagram and TikTok integration
- [ ] Advanced analytics dashboard
- [ ] A/B testing for post optimization
- [ ] Custom content review workflow

### Version 1.2 (Q2 2025)
- [ ] Multi-language support
- [ ] AI-generated images for posts
- [ ] Team collaboration features
- [ ] White-label enterprise version

### Version 2.0 (Q3 2025)
- [ ] Multi-source content aggregation (TechCrunch, VentureBeat)
- [ ] Predictive engagement scoring
- [ ] Video content generation
- [ ] Advanced personalization engine

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Run development checks
make lint test security-check
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run the full test suite
5. Submit a pull request with a clear description

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Reddit API** for enabling content discovery
- **Google Gemini** for intelligent content generation
- **Google Cloud Platform** for reliable infrastructure
- **The AI community** for inspiration and feedback

---

**PostSync** - *Synchronize your success in the AI world* 🚀

For support, questions, or feature requests, please visit our [GitHub Issues](https://github.com/yourusername/postsync/issues) or contact us at hello@postsync.com.

---

*Built with ❤️ for the AI community*