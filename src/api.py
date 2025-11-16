from enum import Enum
from typing import Optional, List
import httpx
from schemas import (
    LoginResponse, 
    StatsResponse,
    Site,
    Shift,
    CallLog,
    PaginatedResponse
)

class ENDPOINTS(Enum):
    LOGIN = "/auth/signin"
    STATS = "/stats"
    SITES = "/sites"
    SITE_SHIFTS = "/sites/{site_id}/shifts"
    SITE_CALL_LOGS = "/sites/{site_id}/call-logs"
    SITE_NOTIFICATIONS = "/sites/{site_id}/notifications"

class AskariPatrolClient(httpx.Client):
    _BASE_URL = "https://guardtour.legitsystemsug.com"

    def __init__(self):
        super().__init__(base_url=self._BASE_URL)
    
    def login(self, username: str, password: str) -> LoginResponse:
        response = self.post(
            ENDPOINTS.LOGIN.value,
            json={"username": username, "password": password},
        )
        response.raise_for_status()
        return response.json()
    
    def _set_auth_header(self, token: str):
        self.headers.update({"Authorization": f"Bearer {token}"})
    
    def get_stats(self) -> StatsResponse:
        response = self.get(ENDPOINTS.STATS.value)
        response.raise_for_status()
        return response.json()
    
    def get_sites(self, page: Optional[int]=None) -> PaginatedResponse[Site]:
        response = self.get(ENDPOINTS.SITES.value, params={"page": page})
        response.raise_for_status()
        return response.json()
    
    def get_site_shifts(self, site_id: int) -> List[Shift]:
        response = self.get(ENDPOINTS.SITE_SHIFTS.value.format(site_id=site_id))
        response.raise_for_status()
        return response.json()
    
    def get_site_call_logs(self, site_id: int, page: Optional[int]=None) -> PaginatedResponse[CallLog]:
        response = self.get(ENDPOINTS.SITE_CALL_LOGS.value.format(site_id=site_id), params={"page": page})
        response.raise_for_status()
        return response.json()

    def get_site_notifications(self, site_id: int, page: Optional[int]=None) -> PaginatedResponse[dict]:
        response = self.get(ENDPOINTS.SITE_NOTIFICATIONS.value.format(site_id=site_id), params={"page": page})
        response.raise_for_status()
        return response.json()

    