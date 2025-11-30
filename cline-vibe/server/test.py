import sys
import time
from pathlib import Path

# Add cline-vibe/server to path to import APIs
# project_root = Path(__file__).parent.parent
# cline_vibe_server = project_root / "cline-vibe" / "server"
# sys.path.insert(0, str(cline_vibe_server))

from api.rocket_api import rocket_api
from api.flight_api import flight_api
from models.rocket import UpdateFlight
from db_models.enums import RocketState, JobStatus
from db_models.rocket_orm import Rocket as RocketORM
from core.database import SessionLocal
import uuid


def integration_test():
    """Run a quick integration test to make sure all apis are up and running"""
    print("=" * 60)
    print("Starting Integration Test")
    print("=" * 60)
    
    # 1. Create a new rocket
    print("\n1. Creating a new rocket...")
    rocket_name = f"TestRocket_{uuid.uuid4().hex[:8]}"
    rocket = rocket_api.create_rocket(rocket_name)
    print(f"   ✓ Rocket created: {rocket.name} (ID: {rocket.id}, State: {rocket.state.value})")
    
    # Verify rocket is in PREPARING state
    assert rocket.state == RocketState.PREPARING, f"Expected PREPARING, got {rocket.state.value}"
    
    # 2. Set rocket to LANDED state (required for creating and triggering flights)
    print("\n2. Setting rocket to LANDED state...")
    session = SessionLocal()
    try:
        db_rocket = session.query(RocketORM).filter(RocketORM.id == rocket.id).first()
        db_rocket.state = RocketState.LANDED
        session.commit()
        session.refresh(db_rocket)
        print(f"   ✓ Rocket state updated to: {db_rocket.state.value}")
        assert db_rocket.state == RocketState.LANDED
    finally:
        session.close()
    
    # 3. Create a flight
    print("\n3. Creating a flight...")
    # Create a test user ID (in real scenario, this would come from auth)
    test_user_id = uuid.uuid4()
    
    flight_data = UpdateFlight(
        rocket_id=rocket.id,
        state=RocketState.PREPARING,  # Will be set by create_flight
        source="Earth",
        destination="Mars",
        location="Earth",
        estimated_time=30,  # 30 seconds for quick test
        status=JobStatus.QUEUED,
        user_id=test_user_id,
        message="Integration test flight"
    )
    
    flight = flight_api.create_flight(flight_data)
    print(f"   ✓ Flight created: {flight.id} (State: {flight.state.value})")
    assert flight.rocket_id == rocket.id
    assert flight.state == RocketState.PREPARING
    
    # 4. Trigger the flight
    print("\n4. Triggering flight...")
    # First, ensure rocket is still in LANDED state
    session = SessionLocal()
    try:
        db_rocket = session.query(RocketORM).filter(RocketORM.id == rocket.id).first()
        if db_rocket.state != RocketState.LANDED:
            db_rocket.state = RocketState.LANDED
            session.commit()
    finally:
        session.close()
    
    update_flight = UpdateFlight(id=flight.id)
    triggered_flight = flight_api.trigger_flight(update_flight)
    print(f"   ✓ Flight triggered (State: {triggered_flight.state.value})")
    assert triggered_flight.state == RocketState.PREPARING
    
    # 5. Monitor flight state changes
    print("\n5. Monitoring flight state changes...")
    print("   Expected sequence: PREPARING -> READY -> IN_FLIGHT -> LANDED")
    
    expected_states = [RocketState.PREPARING, RocketState.READY, RocketState.IN_FLIGHT, RocketState.LANDED]
    observed_states = [RocketState.PREPARING]  # We already know it starts here
    max_wait_time = 60  # Maximum time to wait for completion (seconds)
    check_interval = 0.5  # Check every 0.5 seconds
    start_time = time.time()
    last_state = RocketState.PREPARING
    
    while time.time() - start_time < max_wait_time:
        time.sleep(check_interval)
        
        # Get current flight state using flight_api
        try:
            flights = flight_api.get_flights(str(rocket.id))
            if flights:
                current_flight = next((f for f in flights if f.id == flight.id), None)
                if current_flight:
                    current_state = current_flight.state
                    if current_state != last_state:
                        print(f"   → State changed: {last_state.value} -> {current_state.value}")
                        if current_state not in observed_states:
                            observed_states.append(current_state)
                        last_state = current_state
                        
                        # Check if we've reached LANDED state
                        if current_state == RocketState.LANDED:
                            print(f"   ✓ Flight completed successfully!")
                            break
        except Exception as e:
            print(f"   Warning: Error checking state: {e}")
    
    # Verify we observed all expected states
    print("\n6. Verifying state transitions...")
    for expected_state in expected_states:
        if expected_state in observed_states:
            print(f"   ✓ Observed state: {expected_state.value}")
        else:
            print(f"   ✗ Missing state: {expected_state.value}")
    
    # Final verification
    print("\n7. Verifying final state...")
    try:
        final_flights = flight_api.get_flights(str(rocket.id))
        if final_flights:
            final = next((f for f in final_flights if f.id == flight.id), None)
            if final:
                print(f"   Final flight state: {final.state.value}")
                print(f"   Final flight status: {final.status.value}")
                assert final.state == RocketState.LANDED, f"Expected LANDED, got {final.state.value}"
                print(f"   ✓ Final state verification passed")
            else:
                print(f"   ✗ Flight not found in final check")
        else:
            print(f"   ✗ No flights found for rocket")
    except Exception as e:
        print(f"   ✗ Error in final verification: {e}")
        raise
    
    print("\n" + "=" * 60)
    print("Integration Test Completed Successfully!")
    print("=" * 60)


if __name__ == "__main__":
    integration_test()
