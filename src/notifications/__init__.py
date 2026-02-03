from typing import Dict, Any
from abc import ABC, abstractmethod

class NotificationProvider(ABC):
    @abstractmethod
    def send_notification(self, target: str, data: Dict[str, Any]) -> None:
        """
        Sends a notification to the target.
        :param target: The destination (URL, ARN, etc.)
        :param data: The data dictionary containing log info.
        :return: Boolean success status.
        """
        pass
