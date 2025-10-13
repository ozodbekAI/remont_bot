"""
Repositories Package
Содержит все репозитории для работы с базой данных
"""

from .order import OrderRepository
from .master import MasterRepository
from .assignment import AssignmentRepository
from .skill import SkillRepository

__all__ = [
    "OrderRepository",
    "MasterRepository",
    "AssignmentRepository",
    "SkillRepository",
]