# AI Orchestration Service

A web service that provides a unified interface to multiple AI models like Claude, DeepSeek, Gemini, and Ollama, with subscription management and pay-per-use billing.

## Features

- **Unified API**: Access multiple AI models through a single API
- **Model Selection**: Choose from Claude 3.7 Sonnet, DeepSeek R1, Gemini 2.0 Pro, and local Ollama models
- **Tiered Access**: Different subscription levels with varied access to models and usage limits
- **Payment Integration**: Subscription and pay-per-use billing with Stripe
- **User Management**: Authentication, authorization, and user profiles
- **Usage Tracking**: Monitor token usage and costs
- **Modern Frontend**: React-based web interface with conversation tracking
- **Rate Limiting**: Prevent abuse while allowing premium users higher usage

## Architecture

The project consists of two main components:

1. **Backend API (FastAPI)**: Handles authentication, model orchestration, and billing
2. **Frontend (React)**: Provides user interface for interacting with AI models and managing subscriptions

## Setup

### Prerequisites

- Python 3.8+
- Node.js 14+
- API keys for AI services (Claude, DeepSeek, Gemini)
- Stripe account for payment processing
- (Optional) Ollama setup for local models

### Environment Variables

Create a `.env` file in the root directory with the following:

```
# API Keys
ANTHROPIC_API_KEY=your_claude_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
GEMINI_API_KEY=your_gemini_api_key

# JWT Auth
JWT_SECRET_KEY=your_secret_key_for_jwt

# Stripe Integration
STRIPE_API_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
STRIPE_STANDARD_PRICE_ID=price_standard_id
STRIPE_PREMIUM_PRICE_ID=price_premium_id
STRIPE_ENTERPRISE_PRICE_ID=price_enterprise_id

# Database URL (default is SQLite, change for production)
DATABASE_URL=sqlite:///./ai_service.db

# Optional: Ollama Host (default is localhost:11434)
OLLAMA_HOST=http://localhost:11434
```

### Backend Setup

1. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Initialize the database:
   ```
   python -c "from database import init_db; init_db()"
   ```

3. Start the FastAPI server:
   ```
   uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install Node dependencies:
   ```
   npm install
   ```

3. Create a `.env` file in the frontend directory:
   ```
   REACT_APP_STRIPE_PUBLIC_KEY=your_stripe_public_key
   ```

4. Start the React development server:
   ```
   npm start
   ```

## Deployment Options

### Docker Deployment

1. Build the Docker containers:
   ```
   docker-compose build
   ```

2. Start the services:
   ```
   docker-compose up -d
   ```

### Cloud Deployment

The service can be deployed on various cloud platforms:

#### AWS
- Deploy backend on AWS Lambda or ECS
- Frontend on S3 with CloudFront
- Use RDS for database
- Set up API Gateway for routing

#### Google Cloud
- Backend on Cloud Run or GKE
- Frontend on Firebase Hosting
- Cloud SQL for database
- Cloud Load Balancing for routing

#### Azure
- Backend on Azure Functions or AKS
- Frontend on Azure Static Web Apps
- Azure SQL for database
- Azure API Management for routing

## Production Considerations

For production deployment, consider the following:

1. Use a production-ready database like PostgreSQL
2. Set up proper SSL/TLS certificates
3. Implement robust logging and monitoring
4. Configure auto-scaling for the backend
5. Set up database backups
6. Use a CDN for the frontend assets
7. Implement rate limiting and DDoS protection
8. Set up CI/CD pipelines for automated deployment

## Scaling the Service

To handle increased load:

1. Use a load balancer in front of multiple API instances
2. Implement a caching layer with Redis
3. Use database connection pooling
4. Optimize database queries with proper indexing
5. Consider using a message queue for async processing
6. Implement horizontal scaling for API servers

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
