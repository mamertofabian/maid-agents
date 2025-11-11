"""Base Agent - Abstract base class for all MAID agents."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    """Abstract base class for all MAID agents."""

    def __init__(self):
        """Initialize base agent."""
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """Execute agent logic.

        Returns:
            Dict with execution results
        """
        pass
