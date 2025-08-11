# News Feed

## Project Overview

News Feed is a Python-based application designed to simplify the process of aggregating, summarizing, and sharing news articles. The project aims to address the challenges of consuming large amounts of information by automating the extraction of key insights from various RSS feeds, translating them into multiple languages, and delivering updates to Telegram channels. It also provides dynamically generated RSS feeds for external consumption.

### Why News Feed?

- **Information Overload**: With the ever-growing volume of news, manually filtering and summarizing articles is time-consuming. News Feed automates this process using advanced LLM technology.
- **Language Accessibility**: By translating summaries into Farsi, the project ensures non-English speakers can access important news updates.
- **Centralized Updates**: News Feed consolidates updates into Telegram channels, making it easier for users to stay informed without visiting multiple sources.

## Features

- Aggregates news from predefined RSS feeds.
- Summarizes articles using Gemini LLM.
- Translates summaries to Farsi.
- Sends updates to Telegram channels in English and Farsi.
- Exposes RSS feeds in both English and Farsi.
- Includes health check and Prometheus metrics endpoints for monitoring.
- **Reliable Job Scheduling**: Powered by an abstract cron job system that schedules tasks, retries hanging jobs, and tracks execution metrics for monitoring.
- **Error Handling and Retry Mechanism**: Ensures resilience by gracefully retrying failed tasks and logging errors.
- **Database Integration**: Tracks job statuses and execution history for better monitoring and debugging.

## Prerequisites

- Docker installed for containerized deployment.
- Python 3.11 and `pip` for manual installation.
- PostgreSQL database setup.
- Telegram bot credentials.

## Installation

### Docker Deployment

1. Clone the repository:
   ```bash
   git clone git@github.com:MahbodGhadiri/news-feed.git
   cd news-feed
   ```
2. Build the Docker image:
   ```bash
   docker build -t news-feed .
   ```
3. Run the container:
   ```bash
   docker run -d --env-file .env -p 8000:8000 news-feed
   ```

### Manual Deployment

1. Clone the repository:
   ```bash
   git clone git@github.com:MahbodGhadiri/news-feed.git
   cd news-feed
   ```
2. Create a Python virtual environment and install dependencies:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory with the following variables:
   ```plaintext
   GEMINI_API_KEY=
   TELEGRAM_TOKEN=
   DATABASE_URL=
   SERVER_URL=
   ENGLISH_CHANNEL_ID=
   FARSI_CHANNEL_ID=
   ```
4. Run the FastAPI application:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## Environment Variables

The application requires the following environment variables:

```plaintext
GEMINI_API_KEY=         # API key for Gemini LLM
TELEGRAM_TOKEN=         # Telegram bot token
DATABASE_URL=           # PostgreSQL database connection string
SERVER_URL=             # Base URL for the server
ENGLISH_CHANNEL_ID=     # Telegram channel ID for English updates
FARSI_CHANNEL_ID=       # Telegram channel ID for Farsi updates
```

**Note**: The `.env` file is **not included** in the repository. You must create it manually.

## Endpoints

### Health Check

- **GET /health**: Returns the service status and uptime.
- Response example:
  ```json
  {
    "status": 200,
    "uptime": "5 minutes",
    "date": "2025-08-11T13:06:00Z",
    "message": "🟢 News Feed is running."
  }
  ```

### Cron Health

- **GET /cron-health**: Returns the status of cron jobs and active jobs count.
- Response example:
  ```json
  {
    "status": "healthy",
    "active_jobs": 3,
    "timestamp": "2025-08-11T13:06:00Z"
  }
  ```

### Prometheus Metrics

- **GET /metrics**: Exposes Prometheus metrics for monitoring.

### RSS Feeds

- **GET /rss**: English RSS feed endpoint.

  - Query parameters:
    - `source`: Filter by source URL.
    - `search`: Search in title or summary.
    - `start_date`: Start date (YYYY-MM-DD).
    - `end_date`: End date (YYYY-MM-DD).
    - `limit`: Limit number of articles (default: 20).
  - Response: RSS feed in XML format.

- **GET /rss/farsi**: Farsi RSS feed endpoint.
  - Query parameters: Same as `/rss`.
  - Response: RSS feed in XML format.

## Database Configuration

The application uses PostgreSQL for storing articles. The `BaseDatabaseService` ensures the database exists and handles connections. Make sure your `DATABASE_URL` is correctly set in the `.env` file.

## RSS Feed Management

RSS feed files are located under `/api/rss-feed/{topic}.txt`. To add new topics:

1. Create a new `.txt` file in the directory.
2. Add the RSS feed URLs for the topic.

## Telegram Integration

The application sends updates to Telegram channels using the Telegram Bot API. To set this up:

1. Create a Telegram bot and obtain the `TELEGRAM_TOKEN`.
2. Configure the channel IDs for English and Farsi in the `.env` file.

## Conceptual Workflow

- **News Aggregation**:
  - RSS feeds are fetched and filtered based on recency, duplicates, and keywords.
- **Summarization**:
  - Articles are summarized using Gemini LLM.
- **Translation**:
  - Summaries are translated into Farsi.
- **Telegram Updates**:
  - Articles are formatted and sent to Telegram channels.
- **RSS Feeds**:
  - Articles are dynamically exposed via RSS endpoints.
- **Scheduled Tasks**:
  - Reliable scheduling and execution of tasks using the abstract cron job system.

## Deployment

- **Docker**:
  - Build and run the Docker container using the provided `Dockerfile`.
- **Kubernetes**:
  - The `.drone.yml` and `k8s/` directories are included for CI/CD pipelines and Kubernetes configurations.

## Future Plans

- Adding unit and integration tests.
- Integration with local LLMs.
- Expanding RSS feed topics.
- Improving translation accuracy.

## Contributing

Contributions to News Feed are welcome! Here's how you can get involved:

### How to Contribute

1. **Fork the Repository**:

   - Fork the project from [GitHub](https://github.com/MahbodGhadiri/news-feed) and clone it to your local machine.

   ```bash
   git clone https://github.com/your-username/news-feed.git
   cd news-feed
   ```

2. **Set Up Your Environment**:

   - Follow the instructions in the "Installation" section to set up your environment.

3. **Create a Feature Branch**:

   - Use a descriptive name for your branch:

   ```bash
   git checkout -b feature/add-new-rss-topic
   ```

4. **Make Your Changes**:

   - Add new features, fix bugs, or improve documentation.
   - Ensure your code follows the project's style guidelines.

5. **Write Tests**:

   - Add unit and integration tests for your changes. This ensures reliability and prevents regressions.

6. **Commit Your Changes**:

   - Write clear and concise commit messages:

   ```bash
   git commit -m "Add new RSS topic management feature"
   ```

7. **Push Your Changes**:

   ```bash
   git push origin feature/add-new-rss-topic
   ```

8. **Submit a Pull Request**:
   - Open a pull request on GitHub and describe your changes in detail.

### Contribution Guidelines

- **Code Quality**: Follow Python best practices and ensure your code is clean and readable.
- **Testing**: Include tests for all new features.
- **Documentation**: Update the README or add relevant documentation for your changes.
- **Respect Existing Features**: Ensure your changes don’t break existing functionality.

### Areas to Contribute

- **New Features**: Suggest and implement new features, such as additional RSS topics or enhanced summarization capabilities.
- **Bug Fixes**: Identify and fix bugs in the application.
- **Performance Improvements**: Optimize code for better performance and scalability.
- **Documentation**: Improve or expand the project's documentation.
- **Testing**: Add unit and integration tests to improve reliability.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
