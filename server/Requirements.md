Server: FASTAPI/Python + SQLAlchemy for Postgresql database access. Provides standard REST endpoints and websockets for live updates. Provides JWT Auth.

# Endpoints

## Authentication
- **POST /api/v1/login**  
  Login with username and password. Returns JWT token.  
  Request Body:  
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```  
  Response:  
  ```json
  {
    "access_token": "jwt_token_string",
    "token_type": "bearer"
  }
  ```

- **POST /api/v1/logout**  
  Logout current JWT token (invalidate or client-side removal).  
  No request body.  
  Response: 204 No Content

- **POST /api/v1/register**  
  Register a new user.  
  Request Body:  
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```  
  Response:  
  ```json
  {
    "id": "uuid",
    "username": "string",
    "created_at": "datetime"
  }
  ```

## Rocket Job Management

- **POST /api/v1/job**  
  Create a new rocket job and trigger Airflow DAG.  
  Request Body:  
  ```json
  {
    "source": "string",
    "destination": "string",
    "estimated_time": "integer_seconds"
  }
  ```  
  Response:  
  ```json
  {
    "id": "uuid",
    "state": "Preparing",
    "source": "string",
    "destination": "string",
    "location": "string",
    "estimated_time": "integer_seconds",
    "status": "pending",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```

- **GET /api/v1/job**  
  Get all jobs, with optional filters:  
  Query Parameters:  
  - `state` (optional): filter by rocket state (Preparing, Ready, InFlight, Landed_On_Mars)  
  - `status` (optional): filter by job status (pending, running, succeeded, failed, cancelled)  
  - `user_id` (optional): filter by user who created the job  
  Response: List of jobs

- **GET /api/v1/job/{id}**  
  Get job by ID.  
  Response: Job object as above.

- **DELETE /api/v1/job/{id}**  
  Delete job by ID.  
  Response: 204 No Content

- **PATCH /api/v1/job/{id}**  
  Update job details or state (admin or system use).  
  Request Body (any subset):  
  ```json
  {
    "state": "string",
    "location": "string",
    "estimated_time": "integer_seconds",
    "status": "string"
  }
  ```  
  Response: Updated job object.

- **POST /api/v1/job/{id}/trigger**  
  Manually trigger or retrigger the Airflow DAG for the job.  
  Response: Confirmation with DAG run ID.

- **GET /api/v1/job/{id}/history**  
  Get job state transition history/log.  
  Response: List of state changes with timestamps and messages.

## Websockets

- **WS /api/v1/ws/jobs**  
  Websocket endpoint for live job updates. Supports subscription to all jobs or user-specific jobs. Sends messages on job state changes.

# Data Models

## RocketJob
| Field           | Type       | Description                                  |
|-----------------|------------|----------------------------------------------|
| id              | UUID       | Primary key                                  |
| state           | Enum       | Rocket state: Preparing, Ready, InFlight, Landed_On_Mars, RUD (Rapid Unscheduled Destruction) |
| source          | String     | Flight origin (e.g., Earth, Mars)            |
| destination     | String     | Flight destination (e.g., Mars, Earth)       |
| location        | String     | Current location of the rocket                |
| estimated_time  | Integer    | Estimated time left in current state (seconds) |
| status          | Enum       | Job status: pending, running, succeeded, failed, cancelled |
| airflow_dag_run_id | String   | Airflow DAG run identifier (optional)        |
| user_id         | UUID       | Foreign key to User who created the job       |
| created_at      | DateTime   | Timestamp of creation                          |
| updated_at      | DateTime   | Timestamp of last update                        |

## User
| Field           | Type       | Description                                  |
|-----------------|------------|----------------------------------------------|
| id              | UUID       | Primary key                                  |
| username        | String     | Unique username                              |
| password_hash   | String     | Hashed password                              |
| created_at      | DateTime   | Timestamp of creation                        |
| is_active       | Boolean    | User active status                           |

## JobHistory (optional)
| Field           | Type       | Description                                  |
|-----------------|------------|----------------------------------------------|
| id              | UUID       | Primary key                                  |
| job_id          | UUID       | Foreign key to RocketJob                      |
| timestamp       | DateTime   | When the state change occurred                |
| state           | Enum       | Rocket state at this time                      |
| message         | String     | Optional message or log entry                  |

# Notes
- RocketJob also acts as Rocket inventory; only rockets in proper states (e.g., Ready) can be launched.
- All endpoints except `/login` and `/register` require JWT authentication.
- Job creation triggers an Airflow DAG run.
- State transitions are managed by Airflow and backend logic.
- Websocket endpoint provides live updates for job state changes.
- Keep code simple and manageable.
