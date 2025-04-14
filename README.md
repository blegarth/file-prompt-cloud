# File Prompt Service

A cloud-native service that processes files using Google Cloud services and Gemini AI.

## Features

- File processing with OCR capabilities
- Integration with Google Cloud Storage
- Pub/Sub for asynchronous processing
- Cloud Run for serverless deployment
- Gemini AI for content analysis
- Virtual environment for dependency isolation

## Architecture

The service uses the following Google Cloud components:
- Cloud Run for hosting
- Cloud Storage for file storage
- Pub/Sub for message queuing
- Cloud Build for container building
- Cloud Logging and Monitoring

## Prerequisites

- Google Cloud account with billing enabled
- Google Cloud SDK installed
- Python 3.11 or later
- Docker installed (for local development)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd file-prompt
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up Google Cloud:
```bash
gcloud auth login
gcloud config set project file-prompt
```

4. Deploy the service:
```bash
chmod +x deployment/deploy.sh
./deployment/deploy.sh
```

## Development

The project structure:
```
.
├── src/
│   ├── core/
│   │   ├── server.py
│   │   ├── processor.py
│   │   ├── main.py
│   │   ├── preprocessor.py
│   │   └── monitoring.py
│   └── gcp/
│       ├── gemini_client.py
│       ├── uploader.py
│       └── handlers.py
├── deployment/
│   ├── deploy.sh
│   └── update.sh
├── Dockerfile
├── requirements.txt
├── .gitignore
└── README.md
```

### Local Development

1. Set up environment variables:
```bash
export GCP_PROJECT_ID=file-prompt
export GCS_BUCKET_NAME=file-prompt-bucket
export PUBSUB_TOPIC=file-processing-topic
export PUBSUB_SUBSCRIPTION=file-processing-subscription
export PUBSUB_RESULTS_TOPIC=file-processing-results
export PUBSUB_RESULTS_SUBSCRIPTION=file-processing-results-subscription
export GOOGLE_API_KEY=your-api-key
```

2. Run the service locally:
```bash
python src/core/server.py
```

### Testing

Run the test suite:
```bash
python -m pytest tests/
```

## Deployment

The service is deployed using Cloud Build and Cloud Run. The deployment script (`deploy.sh`) handles:
- Creating service accounts and permissions
- Setting up Pub/Sub topics and subscriptions
- Building and pushing the Docker image
- Deploying to Cloud Run
- Setting environment variables including:
  - GCP_PROJECT_ID
  - GCS_BUCKET_NAME
  - PUBSUB_TOPIC
  - PUBSUB_SUBSCRIPTION
  - PUBSUB_RESULTS_TOPIC
  - PUBSUB_RESULTS_SUBSCRIPTION
  - GOOGLE_API_KEY

## Monitoring

The service includes:
- Cloud Logging integration
- Cloud Monitoring metrics
- Error tracking and reporting
- Detailed logging of Pub/Sub message publishing

## Security

- Service account with least privilege access
- Secure communication channels
- Input validation and sanitization
- Environment-based configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Job Format

When publishing a message to the processing topic (`file-processing-topic`), the message should be in the following JSON format:

```json
{
    "file_path": "path/to/file/in/bucket",
    "prompt": "optional prompt for analysis",
    "job_id": "unique identifier for tracking"
}
```

### Required Fields:
- `file_path`: The path to the file in the GCS bucket (e.g., "uploads/document.pdf")
- `job_id`: A unique identifier for tracking the job through the system

### Optional Fields:
- `prompt`: A custom prompt for the analysis (defaults to "Analyze this content and provide insights.")

### Example:
```bash
# Publish a job to process a PDF file
gcloud pubsub topics publish file-processing-topic \
  --message='{"file_path": "uploads/document.pdf", "job_id": "job-123", "prompt": "Summarize the key points"}'
```

The service will process the file and publish results to the results topic (`file-processing-results`) in the following format:

```json
{
    "job_id": "job-123",
    "file_path": "uploads/document.pdf",
    "response": "Analysis results...",
    "timestamp": "2024-04-14T14:01:17.067177Z",
    "model": "gemini-pro",
    "usage_metadata": {
        "prompt_token_count": 100,
        "candidates_token_count": 200,
        "total_token_count": 300
    }
}
```

In case of an error, the result will be:
```json
{
    "status": "error",
    "error": "Error message",
    "file_path": "uploads/document.pdf",
    "job_id": "job-123",
    "timestamp": "2024-04-14T14:01:17.067177Z"
}
```