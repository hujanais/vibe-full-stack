"""Rocket state machine and launch logic."""
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from db_models.rocket_orm import Rocket as RocketORM
from db_models.flight_orm import Flight as FlightORM
from db_models.enums import RocketState, JobStatus
from core.config import settings


class RocketProcessManager:
    """Manages background threads for rocket state transitions."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure one manager instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, operation_duration_seconds: int = 30):
        """Initialize the rocket process manager.
        
        Args:
            operation_duration_seconds: Total duration for a rocket flight (default: 30 seconds)
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._processes: Dict[str, threading.Thread] = {}
        self._process_stop_flags: Dict[str, threading.Event] = {}
        self.operation_duration = timedelta(seconds=operation_duration_seconds)
        
        # State progression timing (as percentage of total operation)
        self._state_timings = {
            RocketState.PREPARING: (0.0, 0.2),      # 0-20% of operation
            RocketState.READY: (0.2, 0.25),         # 20-25% of operation
            RocketState.IN_FLIGHT: (0.25, 0.9),     # 25-90% of operation
            RocketState.LANDED: (0.9, 1.0),         # 90-100% of operation
        }
        
        # Create a separate engine for background threads
        self.engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            echo=False
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._initialized = True
    
    def _get_db_session(self) -> Session:
        """Get a database session for the background thread."""
        return self.SessionLocal()
    
    def _rocket_state_transition_worker(
        self,
        flight_id: str,
        rocket_id: str,
        source: str,
        destination: str,
        estimated_time: int,
        stop_event: threading.Event
    ):
        """Background worker that transitions rocket and flight states.
        
        Args:
            flight_id: The flight UUID as string
            rocket_id: The rocket UUID as string
            source: Flight origin
            destination: Flight destination
            estimated_time: Estimated flight time in seconds
            stop_event: Event to signal when to stop the process
        """
        start_time = datetime.utcnow()
        # Use the flight's estimated_time if provided, otherwise use default
        duration_seconds = estimated_time if estimated_time > 0 else self.operation_duration.total_seconds()
        end_time = start_time + timedelta(seconds=duration_seconds)
        
        # Update interval (every second)
        update_interval = 1.0
        last_state = None
        
        while not stop_event.is_set():
            now = datetime.utcnow()
            
            # Check if we've exceeded the end time
            if now >= end_time:
                # Final state: LANDED
                db = self._get_db_session()
                try:
                    flight = db.query(FlightORM).filter(FlightORM.id == uuid.UUID(flight_id)).first()
                    rocket = db.query(RocketORM).filter(RocketORM.id == uuid.UUID(rocket_id)).first()
                    
                    if flight and rocket:
                        if rocket.state != RocketState.LANDED:
                            rocket.state = RocketState.LANDED
                            flight.state = RocketState.LANDED
                            flight.status = JobStatus.SUCCEEDED
                            flight.location = destination
                            db.commit()
                    
                    db.close()
                    break
                except Exception as e:
                    print(f"Error updating final state for flight {flight_id}: {e}")
                    db.rollback()
                    db.close()
                    break
            
            # Calculate progress (0.0 to 1.0)
            elapsed = (now - start_time).total_seconds()
            progress = elapsed / duration_seconds if duration_seconds > 0 else 0.0
            progress = min(progress, 1.0)
            
            # Determine current state based on progress
            current_state = None
            for state, (start_pct, end_pct) in self._state_timings.items():
                if start_pct <= progress < end_pct:
                    current_state = state
                    break
            
            # If we're at the end, set to LANDED
            if progress >= 0.9:
                current_state = RocketState.LANDED
            
            # Update database if state changed
            if current_state and current_state != last_state:
                db = self._get_db_session()
                try:
                    flight = db.query(FlightORM).filter(FlightORM.id == uuid.UUID(flight_id)).first()
                    rocket = db.query(RocketORM).filter(RocketORM.id == uuid.UUID(rocket_id)).first()
                    
                    if flight and rocket:
                        rocket.state = current_state
                        flight.state = current_state
                        
                        # Update status based on state
                        if current_state == RocketState.IN_FLIGHT:
                            flight.status = JobStatus.RUNNING
                            # Update location during flight (interpolate between source and destination)
                            if progress < 0.9:
                                flight.location = source  # Could be more sophisticated
                        elif current_state == RocketState.LANDED:
                            flight.status = JobStatus.SUCCEEDED
                            flight.location = destination
                        
                        db.commit()
                        last_state = current_state
                    
                    db.close()
                except Exception as e:
                    print(f"Error updating state for flight {flight_id}: {e}")
                    db.rollback()
                    db.close()
            
            # Sleep until next update
            time.sleep(update_interval)
        
        # Clean up
        with self._lock:
            if flight_id in self._processes:
                del self._processes[flight_id]
            if flight_id in self._process_stop_flags:
                del self._process_stop_flags[flight_id]
    
    def start_rocket_process(
        self,
        flight_id: str,
        rocket_id: str,
        source: str,
        destination: str,
        estimated_time: int
    ):
        """Start a background thread to transition rocket and flight states.
        
        Args:
            flight_id: The flight UUID as string
            rocket_id: The rocket UUID as string
            source: Flight origin
            destination: Flight destination
            estimated_time: Estimated flight time in seconds
        """
        # Stop any existing process for this flight
        if flight_id in self._processes:
            self.stop_rocket_process(flight_id)
        
        # Create stop event
        stop_event = threading.Event()
        with self._lock:
            self._process_stop_flags[flight_id] = stop_event
        
        # Create and start thread
        thread = threading.Thread(
            target=self._rocket_state_transition_worker,
            args=(flight_id, rocket_id, source, destination, estimated_time, stop_event),
            daemon=True
        )
        thread.start()
        with self._lock:
            self._processes[flight_id] = thread
    
    def stop_rocket_process(self, flight_id: str):
        """Stop the background process for a flight.
        
        Args:
            flight_id: The flight UUID as string
        """
        with self._lock:
            if flight_id in self._process_stop_flags:
                self._process_stop_flags[flight_id].set()
            
            if flight_id in self._processes:
                thread = self._processes[flight_id]
                thread.join(timeout=2.0)  # Wait up to 2 seconds for thread to finish


# Global singleton instance
_rocket_process_manager = None
_manager_lock = threading.Lock()


def get_rocket_process_manager() -> RocketProcessManager:
    """Get the singleton RocketProcessManager instance."""
    global _rocket_process_manager
    if _rocket_process_manager is None:
        with _manager_lock:
            if _rocket_process_manager is None:
                _rocket_process_manager = RocketProcessManager()
    return _rocket_process_manager


class RocketLaunchService:
    """Handles rocket launch business logic."""
    
    @staticmethod
    def start_launch(flight: FlightORM, rocket: RocketORM, session: Session) -> None:
        """Start the launch process for a flight.
        
        Args:
            flight: The flight to launch
            rocket: The rocket to launch
            session: Database session
        """
        # Update rocket state to PREPARING to start the launch sequence
        rocket.state = RocketState.PREPARING
        
        # Update flight state to PREPARING
        flight.state = RocketState.PREPARING
        flight.status = JobStatus.RUNNING
        
        session.commit()
        
        # Start background thread for state transitions
        process_manager = get_rocket_process_manager()
        process_manager.start_rocket_process(
            flight_id=str(flight.id),
            rocket_id=str(rocket.id),
            source=flight.source,
            destination=flight.destination,
            estimated_time=flight.estimated_time
        )

