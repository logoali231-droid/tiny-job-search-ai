from abc import ABC, abstractmethod
from typing import List, Dict


class BaseScraper(ABC):
    """Every job source implements this. Return a list of normalized job dicts."""

    id: str = "base"
    name: str = "Base"

    @abstractmethod
    def search(self, query: str, skills: List[str],
               min_period: int = 0) -> List[Dict]:
        """
        query     : keyword string produced by the Q-agent
        skills    : list of selected skills, e.g. ["python", "sql", "aws"]
        min_period: minimum university semester the user is in (0 = ignore)
        Returns   : list of dicts with keys
                    title, company, location, salary, url, source, tags
        """
        raise NotImplementedError