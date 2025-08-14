# Virtual Environment Setup for PostSync

## Quick Start

The virtual environment has been set up with core dependencies. Here's how to use it:

### Activation (Recommended)
```bash
# Use the provided activation script
./activate.sh
```

### Manual Activation
```bash
# Activate virtual environment
source venv/bin/activate

# Verify installation
python --version
pip list
```

### Deactivation
```bash
deactivate
```

## Current Installation Status

✅ **Core Dependencies Installed:**
- FastAPI 0.116.1
- Pydantic 2.11.7  
- Uvicorn (with standard features)
- Pytest 8.4.1
- HTTPx, Requests
- Python-JOSE (JWT)
- Black, isort (code formatting)
- Python-dotenv (environment variables)

⚠️ **Note on Dependencies:**
Due to Python 3.13 compatibility issues, some packages from the full `requirements.txt` are not yet installed:
- Google Cloud packages (Firestore, Secret Manager, etc.)
- Pandas (data processing)
- Some social media API packages
- bcrypt (for password hashing)

## Adding More Dependencies

To install additional packages that are compatible with Python 3.13:

```bash
source venv/bin/activate
pip install package-name
```

## Development Server

Start the FastAPI development server:

```bash
source venv/bin/activate
PYTHONPATH=/Users/nio/postsync uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the provided script:
```bash
./start_server.sh
```

## Testing

Run the test suite:

```bash
source venv/bin/activate
pytest tests/ -v
```

## Code Formatting

Format code with Black and isort:

```bash
source venv/bin/activate
black src/ tests/
isort src/ tests/
```

## Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your actual configuration values.

## Next Steps

1. **Install remaining dependencies** as they become compatible with Python 3.13
2. **Set up Google Cloud credentials** for Firestore and other services
3. **Configure API keys** in `.env` file
4. **Run the development server** to test the API

## Troubleshooting

### Python Version Issues
This project requires Python 3.12+ but works best with Python 3.13. Check your version:
```bash
python --version
```

### Package Compatibility
If you encounter installation issues, try using the minimal requirements:
```bash
pip install -r requirements-minimal.txt
```

### Virtual Environment Issues
If the virtual environment gets corrupted, recreate it:
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-minimal.txt
```