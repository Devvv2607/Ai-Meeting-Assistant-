# Requirements Document

## Introduction

This document outlines the requirements for diagnosing and fixing backend issues in the AI Meeting Intelligence Platform and ensuring proper frontend-backend integration. The system consists of a FastAPI backend with PostgreSQL, Redis, Celery workers, and a Next.js frontend.

## Glossary

- **Backend**: The FastAPI Python application that handles API requests, authentication, and meeting processing
- **Frontend**: The Next.js TypeScript application that provides the user interface
- **Database**: PostgreSQL database storing users, meetings, transcripts, and summaries
- **Celery**: Asynchronous task queue for processing audio files
- **Redis**: In-memory data store used for caching and as Celery broker
- **S3**: AWS S3 storage for audio files
- **Whisper**: OpenAI's speech-to-text model
- **JWT**: JSON Web Token for authentication
- **API_Client**: Frontend service that communicates with backend API

## Requirements

### Requirement 1: Backend Service Health

**User Story:** As a system administrator, I want the backend services to start correctly and be accessible, so that the application can function properly.

#### Acceptance Criteria

1. WHEN the backend service starts, THE Backend SHALL initialize the database connection successfully
2. WHEN the backend service starts, THE Backend SHALL create all required database tables if they don't exist
3. WHEN the backend service starts, THE Backend SHALL expose the health check endpoint at /health
4. WHEN a health check request is made, THE Backend SHALL return a 200 status code with {"status": "ok"}
5. THE Backend SHALL log all startup errors clearly for debugging

### Requirement 2: Database Configuration

**User Story:** As a developer, I want the database configuration to be correct and flexible, so that the application can connect to PostgreSQL in different environments.

#### Acceptance Criteria

1. WHEN environment variables are set, THE Backend SHALL use those values for database connection
2. WHEN the DATABASE_URL contains special characters in the password, THE Backend SHALL properly encode them
3. WHEN running in Docker, THE Backend SHALL connect to the postgres service using the correct hostname
4. WHEN running locally, THE Backend SHALL connect to localhost with the configured port
5. THE Backend SHALL provide clear error messages when database connection fails

### Requirement 3: Authentication System

**User Story:** As a user, I want to register and login securely, so that I can access my meetings privately.

#### Acceptance Criteria

1. WHEN a user registers with valid credentials, THE Backend SHALL create a new user account with hashed password
2. WHEN a user registers with an existing email, THE Backend SHALL return a 400 error with "Email already registered"
3. WHEN a user logs in with correct credentials, THE Backend SHALL return a valid JWT access token
4. WHEN a user logs in with incorrect credentials, THE Backend SHALL return a 401 error with "Invalid credentials"
5. WHEN a JWT token is provided in the Authorization header, THE Backend SHALL authenticate the user for protected endpoints

### Requirement 4: Meeting Upload

**User Story:** As a user, I want to upload audio files for transcription, so that I can get meeting insights.

#### Acceptance Criteria

1. WHEN a user uploads a valid audio file, THE Backend SHALL accept files with extensions .wav, .mp3, .m4a, .mp4
2. WHEN a user uploads a file larger than 2GB, THE Backend SHALL reject it with a 400 error
3. WHEN a valid file is uploaded, THE Backend SHALL save it temporarily and upload to S3
4. WHEN a file is uploaded successfully, THE Backend SHALL create a meeting record with status PENDING
5. WHEN a meeting is created, THE Backend SHALL trigger an async Celery task for processing

### Requirement 5: Async Processing Pipeline

**User Story:** As a system, I want to process audio files asynchronously, so that uploads don't block the API.

#### Acceptance Criteria

1. WHEN a meeting is created, THE Backend SHALL enqueue a Celery task with the meeting ID and audio URL
2. WHEN the Celery worker processes a task, THE Worker SHALL update the meeting status to PROCESSING
3. WHEN transcription completes successfully, THE Worker SHALL update the meeting status to COMPLETED
4. WHEN processing fails, THE Worker SHALL update the meeting status to FAILED and log the error
5. THE Worker SHALL store transcript segments with embeddings in the database

### Requirement 6: API Endpoints

**User Story:** As a frontend developer, I want consistent and well-documented API endpoints, so that I can integrate the frontend properly.

#### Acceptance Criteria

1. THE Backend SHALL expose all endpoints under the /api/v1 prefix
2. WHEN the API documentation is accessed at /docs, THE Backend SHALL display interactive Swagger UI
3. WHEN an endpoint returns an error, THE Backend SHALL return a consistent error format with detail field
4. WHEN a protected endpoint is accessed without authentication, THE Backend SHALL return 401 Unauthorized
5. THE Backend SHALL enable CORS for all origins during development

### Requirement 7: Frontend-Backend Integration

**User Story:** As a user, I want the frontend to communicate seamlessly with the backend, so that I can use all features without errors.

#### Acceptance Criteria

1. WHEN the frontend makes an API request, THE API_Client SHALL include the JWT token in the Authorization header
2. WHEN the backend returns a 401 error, THE API_Client SHALL redirect the user to the login page
3. WHEN uploading a file, THE API_Client SHALL use FormData with proper content-type headers
4. WHEN the backend URL is configured, THE Frontend SHALL use the NEXT_PUBLIC_API_URL environment variable
5. THE Frontend SHALL handle all API errors gracefully and display user-friendly messages

### Requirement 8: Environment Configuration

**User Story:** As a developer, I want environment variables to be properly configured, so that the application works in different environments.

#### Acceptance Criteria

1. THE System SHALL provide a .env.example file with all required variables documented
2. WHEN Docker Compose starts, THE System SHALL pass environment variables to all services correctly
3. WHEN a required environment variable is missing, THE Backend SHALL log a clear error message
4. THE Backend SHALL support both local development and Docker deployment configurations
5. THE Frontend SHALL access backend URL through NEXT_PUBLIC_API_URL environment variable

### Requirement 9: Error Handling and Logging

**User Story:** As a developer, I want comprehensive error handling and logging, so that I can debug issues quickly.

#### Acceptance Criteria

1. WHEN an error occurs in any endpoint, THE Backend SHALL log the error with timestamp and context
2. WHEN a database operation fails, THE Backend SHALL rollback the transaction and return an appropriate error
3. WHEN a Celery task fails, THE Worker SHALL log the full error traceback
4. THE Backend SHALL log all authentication attempts (success and failure)
5. THE Backend SHALL log all file upload operations with file size and user information

### Requirement 10: Service Dependencies

**User Story:** As a system administrator, I want services to start in the correct order, so that dependencies are available when needed.

#### Acceptance Criteria

1. WHEN Docker Compose starts, THE Backend SHALL wait for PostgreSQL to be healthy before starting
2. WHEN Docker Compose starts, THE Backend SHALL wait for Redis to be healthy before starting
3. WHEN Docker Compose starts, THE Celery_Worker SHALL wait for both PostgreSQL and Redis to be healthy
4. WHEN Docker Compose starts, THE Frontend SHALL wait for the Backend to be healthy before starting
5. THE System SHALL implement health checks for all services with appropriate timeouts
