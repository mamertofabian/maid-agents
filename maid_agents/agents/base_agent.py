"""Base Agent - Abstract base class for all MAID agents."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    """Abstract base class for all MAID agents."""

    def __init__(self, dry_run: bool = False):
        """Initialize base agent.

        Args:
            dry_run: If True, skip expensive operations like subprocess calls
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.dry_run = dry_run

    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """Execute agent logic.

        Returns:
            Dict with execution results
        """
        pass
