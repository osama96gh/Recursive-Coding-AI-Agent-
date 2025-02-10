"""Schema definitions for file operation tools."""
from typing import Optional
from pydantic import BaseModel

class ReadFileInput(BaseModel):
    """Schema for file read operations."""
    path: str

class WriteFileInput(BaseModel):
    """Schema for file write operations."""
    path: str
    content: str

class ListDirectoryInput(BaseModel):
    """Schema for directory listing operations."""
    path: str = "."
    recursive: Optional[bool] = False

class DeletePathInput(BaseModel):
    """Schema for path deletion operations."""
    path: str
