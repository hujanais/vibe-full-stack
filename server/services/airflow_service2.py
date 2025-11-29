"""Process-based rocket state transition service."""
from typing import Optional, Dict, Any
import uuid
import threading
import time
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.enums import RocketState, JobStatus
from models.rocket_job import Rocket
from models.job_history import JobHistory
from core.database import SessionLocal
from core.config import settings
from api.websockets import broadcast_job_update


class RocketProcessManager:
    """Manages background processes for rocket state transitions."""
    
    def __init__(self, operation_duration_seconds: int = 30):
        """Initialize the rocket process manager.
        
        Args:
            operation_duration_seconds: Total duration for a rocket flight (default: 30 seconds)
        """
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
    
    def _get_db_session(self) -> Session:
        """Get a database session for the background thread."""
        return self.SessionLocal()
    
    def _rocket_state_transition_worker(
        self,
        rocket_id: str,
        source: str,
        destination: str,
        stop_event: threading.Event
    ):
        """Background worker that transitions rocket states.
        
        Args:
            rocket_id: The rocket UUID as string
            source: Flight origin
            destination: Flight destination
            stop_event: Event to signal when to stop the process
        """
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        start_time = datetime.utcnow()
        end_time = start_time + self.operation_duration
        total_duration_seconds = self.operation_duration.total_seconds()
        
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
                    rocket = db.query(Rocket).filter(Rocket.id == rocket_id).first()
                    if rocket:
                        if rocket.state != RocketState.LANDED:
                            rocket.state = RocketState.LANDED
                            rocket.location = destination
                            rocket.estimated_time = 0
                            rocket.status = JobStatus.SUCCEEDED
                            rocket.updated_at = now
                            
                            # Create history entry
                            history_entry = JobHistory(
                                rocket_id=rocket.id,
                                state=RocketState.LANDED,
                                message=f"Rocket landed at {destination}"
                            )
                            db.add(history_entry)
                            db.commit()
                            
                            # Broadcast update
                            db.refresh(rocket)
                            try:
                                loop.run_until_complete(broadcast_job_update(rocket, rocket.user_id))
                            except Exception as e:
                                print(f"Error broadcasting update: {e}")
                        
                        db.close()
                        break
                except Exception as e:
                    print(f"Error updating rocket {rocket_id}: {e}")
                    db.rollback()
                    db.close()
                finally:
                    if db:
                        db.close()
                break
            
            # Calculate progress
            elapsed = (now - start_time).total_seconds()
            progress = elapsed / total_duration_seconds
            
            # Determine current state based on progress
            current_state = RocketState.PREPARING
            for state, (start_pct, end_pct) in self._state_timings.items():
                if start_pct <= progress < end_pct:
                    current_state = state
                    break
            if progress >= 1.0:
                current_state = RocketState.LANDED
            
            # Calculate location
            if current_state == RocketState.PREPARING or current_state == RocketState.READY:
                location = source
            elif current_state == RocketState.IN_FLIGHT:
                location = f"en route from {source} to {destination}"
            elif current_state == RocketState.LANDED:
                location = destination
            else:
                location = source
            
            # Calculate remaining estimated time
            estimated_time = max(0, int((end_time - now).total_seconds()))
            
            # Update database if state changed
            if current_state != last_state:
                db = self._get_db_session()
                try:
                    rocket = db.query(Rocket).filter(Rocket.id == rocket_id).first()
                    if rocket:
                        rocket.state = current_state
                        rocket.location = location
                        rocket.estimated_time = estimated_time
                        rocket.status = JobStatus.RUNNING
                        rocket.updated_at = now
                        
                        # Create history entry for state change
                        state_messages = {
                            RocketState.PREPARING: f"Rocket preparing at {source}",
                            RocketState.READY: f"Rocket ready for launch at {source}",
                            RocketState.IN_FLIGHT: f"Rocket launched, en route to {destination}",
                            RocketState.LANDED: f"Rocket landed at {destination}"
                        }
                        message = state_messages.get(current_state, f"State changed to {current_state.value}")
                        
                        history_entry = JobHistory(
                            rocket_id=rocket.id,
                            state=current_state,
                            message=message
                        )
                        db.add(history_entry)
                        db.commit()
                        
                        # Broadcast update
                        db.refresh(rocket)
                        try:
                            loop.run_until_complete(broadcast_job_update(rocket, rocket.user_id))
                        except Exception as e:
                            print(f"Error broadcasting update: {e}")
                        
                        last_state = current_state
                except Exception as e:
                    print(f"Error updating rocket {rocket_id}: {e}")
                    db.rollback()
                finally:
                    db.close()
            else:
                # Update estimated_time and location even if state hasn't changed
                db = self._get_db_session()
                try:
                    rocket = db.query(Rocket).filter(Rocket.id == rocket_id).first()
                    if rocket:
                        rocket.location = location
                        rocket.estimated_time = estimated_time
                        rocket.updated_at = now
                        db.commit()
                except Exception as e:
                    print(f"Error updating rocket {rocket_id}: {e}")
                    db.rollback()
                finally:
                    db.close()
            
            # Sleep until next update
            time.sleep(update_interval)
        
        # Clean up
        loop.close()
        if rocket_id in self._processes:
            del self._processes[rocket_id]
        if rocket_id in self._process_stop_flags:
            del self._process_stop_flags[rocket_id]
    
    def start_rocket_process(
        self,
        rocket_id: str,
        source: str,
        destination: str,
        db: Optional[Session] = None
    ):
        """Start a background process to transition rocket states.
        
        Args:
            rocket_id: The rocket UUID as string
            source: Flight origin
            destination: Flight destination
            db: Optional database session (for initial status update)
        """
        # Stop any existing process for this rocket
        if rocket_id in self._processes:
            self.stop_rocket_process(rocket_id)
        
        # Update initial status in database
        if db:
            try:
                rocket = db.query(Rocket).filter(Rocket.id == rocket_id).first()
                if rocket:
                    rocket.status = JobStatus.RUNNING
                    db.commit()
            except Exception as e:
                print(f"Error updating rocket status: {e}")
                db.rollback()
        
        # Create stop event
        stop_event = threading.Event()
        self._process_stop_flags[rocket_id] = stop_event
        
        # Create and start thread
        thread = threading.Thread(
            target=self._rocket_state_transition_worker,
            args=(rocket_id, source, destination, stop_event),
            daemon=True
        )
        thread.start()
        self._processes[rocket_id] = thread
    
    def stop_rocket_process(self, rocket_id: str):
        """Stop the background process for a rocket.
        
        Args:
            rocket_id: The rocket UUID as string
        """
        if rocket_id in self._process_stop_flags:
            self._process_stop_flags[rocket_id].set()
        
        if rocket_id in self._processes:
            thread = self._processes[rocket_id]
            thread.join(timeout=2.0)  # Wait up to 2 seconds for thread to finish
        
        # Update rocket status to cancelled if still running
        db = self._get_db_session()
        try:
            rocket = db.query(Rocket).filter(Rocket.id == rocket_id).first()
            if rocket and rocket.status == JobStatus.RUNNING:
                rocket.status = JobStatus.CANCELLED
                rocket.updated_at = datetime.utcnow()
                
                history_entry = JobHistory(
                    rocket_id=rocket.id,
                    state=rocket.state,
                    message="Rocket process cancelled"
                )
                db.add(history_entry)
                db.commit()
                
                db.refresh(rocket)
                try:
                    # Create a new event loop for this operation
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(broadcast_job_update(rocket, rocket.user_id))
                    loop.close()
                except Exception as e:
                    print(f"Error broadcasting update: {e}")
        except Exception as e:
            print(f"Error cancelling rocket {rocket_id}: {e}")
            db.rollback()
        finally:
            db.close()
    
    def get_rocket_process_status(self, rocket_id: str) -> bool:
        """Check if a rocket process is running.
        
        Args:
            rocket_id: The rocket UUID as string
            
        Returns:
            True if process is running, False otherwise
        """
        if rocket_id not in self._processes:
            return False
        
        thread = self._processes[rocket_id]
        return thread.is_alive()


# Module-level instance for convenience
airflow_service2 = RocketProcessManager()
