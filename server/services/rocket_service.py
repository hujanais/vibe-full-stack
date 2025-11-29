from typing import List, Optional
from server.models.enums import JobStatus, RocketState
from server.models.rocket_job import Rocket
from server.models.user import User
from server.schemas.rocket_job import RocketCreate, RocketResponse, RocketUpdate
from core.database import get_db
from sqlalchemy.orm import Session

class RocketService:
    def __init__(self):
        pass

    def create_rocket(self, rocket: RocketCreate, current_user: User) -> Rocket:
        """Create a new rocket."""
        # Create new rocket
        new_job = Rocket(
            state=RocketState.PREPARING,
            name=rocket.name,
            source='earth',
            destination='mars',
            location='earth',  # Start at source
            estimated_time=999999,
            status=JobStatus.IDLE,
            user_id=current_user.id
        )
        db: Session = get_db
        db.add(new_job)
        db.commit()
        db.refresh(new_job)

        return new_job
    
    def get_rocket(self, rocket_id: str, db: Session) -> Optional[RocketResponse]:
        rocket = db.query(Rocket).filter(Rocket.id == rocket_id).first()
        if rocket is None:
            return None
        return RocketResponse.from_orm(rocket)
    
    def delete_rocket(self, rocket_id: str, db: Session) -> None:
        rocket = db.query(Rocket).filter(Rocket.id == rocket_id).first()
        if rocket:
            db.delete(rocket)
            db.commit()
    
    def update_rocket(self, rocket_update: RocketUpdate, db: Session) -> Optional[RocketResponse]:
        rocket = db.query(Rocket).filter(Rocket.id == rocket_update.id).first()
        if not rocket:
            return None
        update_data = rocket_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rocket, key, value)
        db.commit()
        db.refresh(rocket)
        return RocketResponse.from_orm(rocket)


rocket_service = RocketService()
