## Database Requirements for Rocket Flight Inventory Simulation

**Techstack**: PostgreSQL + SQLAlchemy

### Directory Structure

├── src
├── db
│   └── models
│       └── enums.py               # Contains all necessary enums
│       └── rocket_orm.py          # Contains the Rocket table model
│       └── flight_orm.py          # Contains the Flight history association table
|       
### Data Models

#### Rocket
| Field           | Type       | Description                                                            |
|-----------------|------------|------------------------------------------------------------------------|
| id              | UUID       | Primary key                                                            |
| state           | Enum       | Rocket state: Preparing, Ready, InFlight, Landed, RUD                  |
| name            | String     | Name of the rocket (must be unique)                                    |

#### User
| Field           | Type       | Description                                                            |
|-----------------|------------|------------------------------------------------------------------------|
| id              | UUID       | Primary key                                                            |
| username        | String     | Unique username                                                        |
| password_hash   | String     | Hashed password                                                        |
| created_at      | DateTime   | Timestamp of creation                                                  |
| is_active       | Boolean    | Indicates if the user is currently active                              |

#### Flight (Optional)
Contains the flight history of a Rocket.

| Field           | Type       | Description                                                            |
|-----------------|------------|------------------------------------------------------------------------|
| id              | UUID       | Primary key                                                            |
| rocket_id       | UUID       | Foreign key referencing Rocket                                         |
| state           | Enum       | Rocket state at this time                                              |
| source          | String     | Flight origin (e.g., Earth, Mars)                                      |
| destination     | String     | Flight destination (e.g., Mars, Earth)                                 |
| location        | String     | Current location of the rocket (just a json string)                    |
| estimated_time  | Integer    | Estimated time left in current state (seconds)                         |
| status          | Enum       | Job status: queued, running, succeeded, failed, cancelled              |
| process_id      | String     | Process ID of the long operation                                       |
| user_id         | UUID       | Foreign key referencing User who created the job                       |
| created_at      | DateTime   | Timestamp of creation                                                  |
| updated_at      | DateTime   | Timestamp of last update                                               |
| message         | String     | Optional message or log entry                                          |

### Edge Cases
- Rocket names must be unique (no duplicates allowed).

