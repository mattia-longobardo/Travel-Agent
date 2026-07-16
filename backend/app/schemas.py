from typing import Any
from pydantic import BaseModel

class LoginIn(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    is_active: bool
    group_id: int | None
    class Config: from_attributes = True

class UsersPage(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    group_id: int | None = None
    is_admin: bool = False

class UserUpdate(BaseModel):
    group_id: int | None = None
    is_active: bool | None = None
    is_admin: bool | None = None
    password: str | None = None
    email: str | None = None
    username: str | None = None

class GroupIn(BaseModel):
    name: str


class BulkUsersIn(BaseModel):
    action: str
    user_ids: list[int] | None = None
    all_matching: bool = False
    filters: dict[str, Any] | None = None
    group_id: int | None = None
    value: bool | None = None


class BulkResult(BaseModel):
    affected: int
    skipped: list[dict[str, Any]]

class UsersStats(BaseModel):
    total: int
    active: int
    inactive: int
    admins: int

class ChatGroupIn(BaseModel):
    name: str

class MeUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    current_password: str | None = None
    new_password: str | None = None


class ChatCreate(BaseModel):
    title: str | None = None
    params: dict[str, Any] = {}

class ChatUpdate(BaseModel):
    title: str | None = None
    params: dict[str, Any] | None = None
    status: str | None = None
    chat_group_id: int | None = None

class ChatOut(BaseModel):
    id: int
    title: str
    params_json: dict
    owner_id: int
    permission: str
    status: str = "active"
    chat_group_id: int | None = None
    class Config: from_attributes = True

class ShareIn(BaseModel):
    email: str
    permission: str = "read"

class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    tool_calls_json: dict | None
    created_at: Any
    class Config: from_attributes = True
