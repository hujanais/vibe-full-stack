Project Overview
The showcase application is designed to demonstrate the integration of modern web technologies to create a robust, end-to-end system for managing asynchronous jobs. The stack includes a React frontend, a FastAPI backend, an Apache Airflow orchestrator, and a PostgreSQL database. The primary function of the application is to allow users to create and monitor jobs from a frontend interface, triggering and processing these jobs in the backend using Airflow, and storing job-related data in the database.

The project theme is about the flight of rockets from Earth to Mars(or other planets) and back.
Rocket states:
Preparing: Rocket under preparation.
Ready: Ready to launch.
InFlight: Rocket launched and en-route to Mars. indicated as {source: Earth, destination: Mars}
Landed_On_Mars: landed and unloading.
Inflight: Return flight to Earth. indicated as {source: Mars, destination: Earth}
After return to earth, state transitions back to Preparing. {source: Mars, destination: Earth}

The data-model of a rocket may contain.
state: Preparing, Ready, InFlight, Landed_On_Mars
source: The origination of the flight.
destination: The destination of the flight.
location: The current location of the spaceship.
estimated_time: The time left in this state.

Technology Stack:
Front-End: React/Typescrpt/SCSS/Material-UI.  Do not use Redux for state management.  Use React native context-api.  For more complex state management, use Zustand only if absolutely neccessary.  
Server: FASTAPI/Python + SQLAlchemy for Postgresql database access.  Provides standard REST endpoints and websockets for live updates. Provides JWT Auth.
Database: Containerized Docker deployment.
Apache Airflow: For running "DAGs" (Directed Acyclic Graphs) when created by server.
Containerization and Deployment: Uses Docker for local and cloud deployment.  Plan for Kubernetes deployment.

Project Folder Structures:  Contains 3 main projects folders.
airflow: Scripts and configurations for DAGs, deployment configurations.
client: React app using TypeScript for type safety, SCSS for styling, and any additional structure (such as components, utils).
server: Endpoints, models, and services using FastAPI with SQLAlchemy ORM for database interactions.

Deliverable: 
Keep code simple and manageable.
No Unit-tests are required for this project.
