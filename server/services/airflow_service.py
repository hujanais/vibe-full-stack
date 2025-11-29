"""Airflow integration service."""
import requests
from typing import Optional, Dict, Any
from core.config import settings
import uuid


class AirflowService:
    """Service for interacting with Airflow API."""
    
    def __init__(self):
        self.base_url = settings.AIRFLOW_BASE_URL
        self.auth = None
        if settings.AIRFLOW_USERNAME and settings.AIRFLOW_PASSWORD:
            self.auth = (settings.AIRFLOW_USERNAME, settings.AIRFLOW_PASSWORD)
    
    def trigger_dag(self, dag_id: str, rocket_id: uuid.UUID, conf: Optional[dict] = None) -> Optional[str]:
        """Trigger an Airflow DAG run for a job.
        
        Args:
            dag_id: The DAG identifier
            rocket_id: The rocket job UUID
            conf: Optional configuration to pass to the DAG
            
        Returns:
            DAG run ID if successful, None otherwise
        """
        url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns"
        
        payload = {
            "dag_run_id": f"rocket_job_{rocket_id}",
            "conf": conf or {}
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                auth=self.auth,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("dag_run_id")
        except requests.RequestException as e:
            # Log error in production
            print(f"Error triggering Airflow DAG: {e}")
            return None
    
    def get_dag_run_status(self, dag_id: str, dag_run_id: str) -> Optional[str]:
        """Get the status of an Airflow DAG run.
        
        Args:
            dag_id: The DAG identifier
            dag_run_id: The DAG run identifier
            
        Returns:
            Status string if successful, None otherwise
        """
        url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"
        
        try:
            response = requests.get(url, auth=self.auth)
            response.raise_for_status()
            data = response.json()
            return data.get("state")
        except requests.RequestException as e:
            print(f"Error getting DAG run status: {e}")
            return None
    
    def get_job_info(self, dag_id: str, dag_run_id: str) -> Optional[Dict[str, Any]]:
        """Get rocket job information including state, estimated_time, and location.
        
        This method queries the Airflow pod/DAG run to get relevant information about
        the rocket job's current state, estimated_time, and location.
        
        Args:
            dag_id: The DAG identifier
            dag_run_id: The DAG run identifier
            
        Returns:
            Dictionary with {state, estimated_time, location} if successful, None otherwise
        """
        # Try to get task instance information from Airflow
        # The exact endpoint may vary based on your Airflow setup
        # This assumes the DAG has a task that returns this information
        url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances"
        
        try:
            response = requests.get(url, auth=self.auth)
            response.raise_for_status()
            task_instances = response.json()
            
            # Look for a task that returns job info (e.g., a task named "get_rocket_status" or similar)
            # This is a placeholder - adjust based on your actual Airflow DAG structure
            for task_instance in task_instances.get("task_instances", []):
                task_id = task_instance.get("task_id", "")
                
                # If there's a specific task that returns rocket info, query it
                # For now, we'll try to get info from task logs or XComs
                if "rocket" in task_id.lower() or "status" in task_id.lower():
                    # Try to get XCom value (Airflow's cross-communication mechanism)
                    xcom_url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/xcomEntries"
                    xcom_response = requests.get(xcom_url, auth=self.auth)
                    
                    if xcom_response.status_code == 200:
                        xcom_data = xcom_response.json()
                        # Look for job info in XCom entries
                        for entry in xcom_data.get("xcom_entries", []):
                            value = entry.get("value")
                            if isinstance(value, dict) and "state" in value:
                                return {
                                    "state": value.get("state"),
                                    "estimated_time": value.get("estimated_time", 0),
                                    "location": value.get("location", "unknown")
                                }
            
            # Fallback: Try to get info from DAG run conf
            dag_run_url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"
            dag_run_response = requests.get(dag_run_url, auth=self.auth)
            
            if dag_run_response.status_code == 200:
                dag_run_data = dag_run_response.json()
                conf = dag_run_data.get("conf", {})
                
                # If the conf contains job info, return it
                if "state" in conf or "location" in conf:
                    return {
                        "state": conf.get("state", "unknown"),
                        "estimated_time": conf.get("estimated_time", 0),
                        "location": conf.get("location", "unknown")
                    }
            
            return None
            
        except requests.RequestException as e:
            print(f"Error getting job info from Airflow: {e}")
            return None


airflow_service = AirflowService()


