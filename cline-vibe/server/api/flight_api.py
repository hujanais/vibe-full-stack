# Class implementation for flights api
from dataclasses import dataclass
from typing import Any, Dict, List
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from core.database import SessionLocal
from db_models.flight_orm import Flight as FlightORM
from db_models.rocket_orm import Rocket as RocketORM
from db_models.enums import RocketState
from models.rocket import Flight, UpdateFlight
from api.rocket_statemachine import RocketLaunchService


@dataclass()
class FlightAPI:
    """Business logic for querying and mutating flight history."""

    def _get_session(self) -> Session:
        """Return a new DB session."""
        return SessionLocal()

    def _serialize(self, db_flight: FlightORM) -> Flight:
        """Convert ORM object to Pydantic response."""
        return Flight.model_validate(db_flight)

    def _coerce_uuid(self, value: Any, field_name: str) -> uuid.UUID:
        """Convert incoming identifier to UUID, raising a 400 if invalid."""
        try:
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {field_name}",
            ) from exc

    def get_flights(self, rocket_id: str | None) -> List[Flight]:
        """Return all flights or the subset for a given rocket."""
        session = self._get_session()
        try:
            query = session.query(FlightORM).order_by(FlightORM.created_at.desc())
            if rocket_id:
                rocket_uuid = self._coerce_uuid(rocket_id, "rocket_id")
                query = query.filter(FlightORM.rocket_id == rocket_uuid)

            flights = query.all()
            return [self._serialize(flight) for flight in flights]
        except SQLAlchemyError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to fetch flights",
            ) from exc
        finally:
            session.close()

    def create_flight(self, flight_data: UpdateFlight) -> Flight:
        """Create a new flight. Rocket must be in READY state."""
        session = self._get_session()
        try:
            # Check that the rocket exists and is in READY state
            rocket = session.query(RocketORM).filter(RocketORM.id == flight_data.rocket_id).first()
            if not rocket:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Rocket not found",
                )
            
            if rocket.state != RocketState.LANDED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Rocket must be in READY state to create a flight. Current state: {rocket.state.value}",
                )

            # Create the flight
            flight = FlightORM(
                rocket_id=flight_data.rocket_id,
                state=RocketState.PREPARING,
                source=flight_data.source,
                destination=flight_data.destination,
                location=flight_data.location,
                estimated_time=flight_data.estimated_time,
                status=flight_data.status,
                process_id=flight_data.process_id,
                user_id=flight_data.user_id,
                message=flight_data.message,
            )
            session.add(flight)
            session.commit()
            session.refresh(flight)

            return self._serialize(flight)
        except HTTPException:
            session.rollback()
            raise
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to create flight due to database constraint violation",
            ) from exc
        except SQLAlchemyError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to create flight",
            ) from exc
        finally:
            session.close()

    def trigger_flight(self, flight: UpdateFlight) -> Flight:
        """Trigger a flight launch. Rocket must be in LANDED state."""
        session = self._get_session()
        try:
            # Get flight ID from the update payload
            flight_id = getattr(flight, "id", None) or getattr(flight, "flight_id", None)
            if not flight_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Flight id is required",
                )

            flight_uuid = self._coerce_uuid(flight_id, "flight_id")
            db_flight = session.query(FlightORM).filter(FlightORM.id == flight_uuid).first()

            if not db_flight:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Flight not found",
                )

            # Get the rocket associated with this flight
            rocket = session.query(RocketORM).filter(RocketORM.id == db_flight.rocket_id).first()
            if not rocket:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Rocket not found for this flight",
                )

            # Check that rocket is in LANDED state
            if rocket.state != RocketState.LANDED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Rocket must be in LANDED state to trigger a flight. Current state: {rocket.state.value}",
                )

            # Start the launch process (handled in separate service)
            RocketLaunchService.start_launch(db_flight, rocket, session)
            
            session.refresh(db_flight)
            return self._serialize(db_flight)
        except HTTPException:
            session.rollback()
            raise
        except SQLAlchemyError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to trigger flight",
            ) from exc
        finally:
            session.close()


    def update_flight(self, flight: UpdateFlight) -> Flight:
        """Apply partial updates to a flight row."""
        session = self._get_session()
        try:
            flight_id = getattr(flight, "id", None) or getattr(flight, "flight_id", None)
            if not flight_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Flight id is required",
                )

            flight_uuid = self._coerce_uuid(flight_id, "flight_id")
            db_flight = session.query(FlightORM).filter(FlightORM.id == flight_uuid).first()

            if not db_flight:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Flight not found",
                )

            update_payload: Dict[str, Any]
            if hasattr(flight, "model_dump"):
                update_payload = flight.model_dump(exclude_none=True, exclude_unset=True)
            else:
                update_payload = {k: v for k, v in vars(flight).items() if v is not None}

            # Remove identifier keys so we don't overwrite PK
            update_payload.pop("id", None)
            update_payload.pop("flight_id", None)

            for field_name, value in update_payload.items():
                if field_name in {"rocket_id", "user_id"}:
                    value = self._coerce_uuid(value, field_name)
                setattr(db_flight, field_name, value)

            session.commit()
            session.refresh(db_flight)

            return self._serialize(db_flight)
        except SQLAlchemyError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to update flight",
            ) from exc
        finally:
            session.close()


flight_api = FlightAPI()