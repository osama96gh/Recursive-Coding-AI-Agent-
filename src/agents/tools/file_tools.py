"""Tools for file system operations."""
from typing import Dict, List
from pathlib import Path

from langchain.tools import Tool, StructuredTool

from .file_schemas import ReadFileInput, WriteFileInput, ListDirectoryInput, DeletePathInput

class FileTools:
    """Collection of tools for file system operations."""
    
    def __init__(self, project_root: Path):
        """Initialize file tools with project root directory."""
        self.project_root = project_root
        
    def _validate_path(self, path: str) -> Path:
        """Validate and resolve a file path."""
        resolved_path = (self.project_root / path).resolve()
        if not str(resolved_path).startswith(str(self.project_root)):
            raise ValueError(f"Path {path} is outside project root")
        return resolved_path
    
    def read_file(self, input_data: ReadFileInput) -> Dict:
        """Read contents of a file."""
        try:
            file_path = self._validate_path(input_data.path)
            if not file_path.exists():
                return {
                    "status": "error",
                    "error": f"File {input_data.path} does not exist"
                }
            
            content = file_path.read_text()
            return {
                "status": "success",
                "content": content,
                "path": str(input_data.path)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def write_file(self, input_data: WriteFileInput) -> Dict:
        """Write content to a file."""
        try:
            file_path = self._validate_path(input_data.path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(input_data.content)
            return {
                "status": "success",
                "path": str(input_data.path)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def list_directory(self, input_data: ListDirectoryInput) -> Dict:
        """List contents of a directory."""
        try:
            dir_path = self._validate_path(input_data.path)
            if not dir_path.is_dir():
                return {
                    "status": "error",
                    "error": f"{input_data.path} is not a directory"
                }
            
            files = []
            directories = []
            
            if input_data.recursive:
                for item in dir_path.rglob("*"):
                    rel_path = item.relative_to(self.project_root)
                    if item.is_file():
                        files.append(str(rel_path))
                    else:
                        directories.append(str(rel_path))
            else:
                for item in dir_path.iterdir():
                    rel_path = item.relative_to(self.project_root)
                    if item.is_file():
                        files.append(str(rel_path))
                    else:
                        directories.append(str(rel_path))
            
            return {
                "status": "success",
                "files": files,
                "directories": directories,
                "path": str(input_data.path)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def delete_path(self, input_data: DeletePathInput) -> Dict:
        """Delete a file or directory."""
        try:
            target_path = self._validate_path(input_data.path)
            if target_path.is_file():
                target_path.unlink()
            elif target_path.is_dir():
                import shutil
                shutil.rmtree(target_path)
            return {
                "status": "success",
                "path": str(input_data.path)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_tools(self) -> List[Tool]:
        """Get all file operation tools."""
        return [
            Tool(
                name="read_file",
                description="Read contents of a file",
                func=self.read_file,
                args_schema=ReadFileInput
            ),
            Tool(
                name="write_file",
                description="Write content to a file",
                func=self.write_file,
                args_schema=WriteFileInput
            ),
            Tool(
                name="list_directory",
                description="List contents of a directory",
                func=self.list_directory,
                args_schema=ListDirectoryInput
            ),
            Tool(
                name="delete_path",
                description="Delete a file or directory",
                func=self.delete_path,
                args_schema=DeletePathInput
            )
        ]
