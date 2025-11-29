# Class implementation for flights api
from dataclasses import dataclass
from typing import Any, Dict, List
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.database import SessionLocal
from db_models.flight_orm import Flight as FlightORM
from models.rocket import Flight, UpdateFlight


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