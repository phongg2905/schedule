from typing import Literal

from pydantic import BaseModel, Field


class LanguagePreferenceResponse(BaseModel):
    language: Literal["en", "vi"]


class LanguagePreferenceUpdateRequest(BaseModel):
    language: Literal["en", "vi"]


class PreferencesUpdateRequest(BaseModel):
    timezone: str = Field(min_length=1, max_length=64)
    work_start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    work_end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    lunch_start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    lunch_end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    day_offs: list[str] = Field(default_factory=list)
    focus_hours: list[str] = Field(default_factory=list)


class PreferencesResponse(BaseModel):
    timezone: str
    work_start_time: str
    work_end_time: str
    lunch_start_time: str
    lunch_end_time: str
    day_offs: list[str]
    focus_hours: list[str]
