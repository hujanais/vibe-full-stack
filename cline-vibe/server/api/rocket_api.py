# Class implementation for rocket api
from dataclasses import dataclass
from typing import List, Union
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from core.database import SessionLocal
from db_models.enums import RocketState
from db_models.rocket_orm import Rocket as RocketORM
from db_models.flight_orm import Flight as FlightORM
from models.rocket import RocketResponse


@dataclass()
class RocketAPI:
    """Business logic for Rocket CRUD operations."""

    def _get_session(self) -> Session:
        """Create a new database session."""
        return SessionLocal()

    def _serialize(self, rocket: RocketORM) -> RocketResponse:
        """Convert ORM object into API response."""
        return RocketResponse.model_validate(rocket)

    def _coerce_uuid(self, value: str | uuid.UUID, field_name: str) -> uuid.UUID:
        """Normalize identifiers to UUID objects."""
        try:
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {field_name}",
            ) from exc

    def get_rocket(self, rocket_id: str | None) -> Union[RocketResponse, List[RocketResponse]]:
        # Get rocket from database. null means return all.
        session = self._get_session()
        try:
            if rocket_id:
                rocket_uuid = self._coerce_uuid(rocket_id, "rocket_id")
                rocket = session.query(RocketORM).filter(RocketORM.id == rocket_uuid).first()
                if not rocket:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Rocket not found",
                    )
                return self._serialize(rocket)

            rockets = session.query(RocketORM).order_by(RocketORM.name.asc()).all()
            return [self._serialize(r) for r in rockets]
        except SQLAlchemyError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to fetch rocket data",
            ) from exc
        finally:
            session.close()

    def create_rocket(self, rocket_name: str) -> RocketResponse:
        # Create a new rocket in the database
        if not rocket_name or not rocket_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rocket name is required",
            )

        session = self._get_session()
        try:
            rocket = RocketORM(name=rocket_name.strip())
            session.add(rocket)
            session.commit()
            session.refresh(rocket)
            return self._serialize(rocket)
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Rocket with that name already exists",
            ) from exc
        except SQLAlchemyError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to create rocket",
            ) from exc
        finally:
            session.close()

    def delete_rocket(self, rocket_id: str) -> None:
        # Delete a rocket.  You can only delete if rocket state is in PREPARING or READY.
        session = self._get_session()
        try:
            rocket_uuid = self._coerce_uuid(rocket_id, "rocket_id")
            rocket = session.query(RocketORM).filter(RocketORM.id == rocket_uuid).first()
            if not rocket:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Rocket not found",
                )

            if rocket.state not in {RocketState.PREPARING, RocketState.READY}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Rocket cannot be deleted in its current state",
                )

            session.query(FlightORM).filter(FlightORM.rocket_id == rocket_uuid).delete(synchronize_session=False)
            session.delete(rocket)
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to delete rocket",
            ) from exc
        finally:
            session.close()


rocket_api = RocketAPI()