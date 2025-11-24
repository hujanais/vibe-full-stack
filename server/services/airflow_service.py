"""Airflow integration service."""
import requests
from typing import Optional
from core.config import settings
import uuid


class AirflowService:
    """Service for interacting with Airflow API."""
    
    def __init__(self):
        self.base_url = settings.AIRFLOW_BASE_URL
        self.auth = None
        if settings.AIRFLOW_USERNAME and settings.AIRFLOW_PASSWORD:
            self.auth = (settings.AIRFLOW_USERNAME, settings.AIRFLOW_PASSWORD)
    
    def trigger_dag(self, dag_id: str, job_id: uuid.UUID, conf: Optional[dict] = None) -> Optional[str]:
        """Trigger an Airflow DAG run for a job.
        
        Args:
            dag_id: The DAG identifier
            job_id: The rocket job UUID
            conf: Optional configuration to pass to the DAG
            
        Returns:
            DAG run ID if successful, None otherwise
        """
        url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns"
        
        payload = {
            "dag_run_id": f"rocket_job_{job_id}",
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


airflow_service = AirflowService()


