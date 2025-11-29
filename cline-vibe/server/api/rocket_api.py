# Class implementation for rocket api
from dataclasses import dataclass
from models.rocket import RocketResponse


@dataclass()
class RocketAPI:

    def get_rocket(self, rocket_id: str) -> RocketResponse:
        pass

    def create_rocket(self, rocket_name: str) -> RocketResponse:
        pass

    def delete_rocket(self, rocket_id: str) -> None:
        pass

rocket_api = RocketAPI()