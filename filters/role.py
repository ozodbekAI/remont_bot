from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from typing import Union, Dict, Any

class RoleFilter(BaseFilter):
    def __init__(self, role: str):
        self.role = role

    async def __call__(
        self, 
        event: Union[Message, CallbackQuery],
        **kwargs: Dict[str, Any]  # Bu yerda o'zgartirdik!
    ) -> bool:
        role = kwargs.get("role")  # data ichidan olamiz
        print(f"🔍 RoleFilter: expected={self.role}, got={role}, all_kwargs={list(kwargs.keys())}")
        return role == self.role