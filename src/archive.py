import oead

from typing import Dict, List

class Archive:
    def __init__(self):
        self._is_changed: bool = False
        self._files: Dict[str, bytes] = {}
        self._path: str = ""

    @classmethod
    def from_sarc(cls, sarc: oead.Sarc, path: str) -> "Archive":
        archive = Archive()
        archive._is_changed = False
        archive._files = { f.name: bytes(f.data) for f in sarc.get_files() }
        archive._path = path
        return archive

    def serialize(self) -> bytes | None:
        if not self._is_changed:
            return None
        writer: oead.SarcWriter = oead.SarcWriter(oead.Endianness.Little)
        for file in self._files:
            writer.files[file] = self._files[file]
        self._is_changed = False
        return writer.write()[1]
    
    def add_file(self, filename: str, data: bytes) -> bool:
        if filename in self._files:
            return False
        self._files[filename] = data
        self._is_changed = True
        return True
    
    def remove_file(self, filename: str) -> bool:
        if filename in self._files:
            del self._files[filename]
            self._is_changed = True
            return True
        return False
    
    def replace_file(self, filename: str, data: bytes) -> bool:
        if filename in self._files:
            self._files[filename] = data
            self._is_changed = True
            return True
        return False
    
    def rename_file(self, old_name: str, new_name: str) -> bool:
        if old_name == new_name:
            return True
        if old_name not in self._files or new_name in self._files:
            return False
        self._files[new_name] = self._files[old_name]
        del self._files[old_name]
        self._is_changed = True
        return True
    
    # does not check if the file already exists or not
    def update_file(self, filename: str, data: bytes) -> None:
        self._files[filename] = data
        self._is_changed = True
    
    def get_file(self, filename: str) -> bytes | None:
        if filename in self._files:
            return self._files[filename]
        return None
    
    def is_exist(self, filename: str) -> bool:
        return filename in self._files
    
    @property
    def filenames(self) -> List[str]:
        return list(self._files.keys())
    
    @property
    def file_count(self) -> int:
        return len(self._files)
    
    @property
    def is_changed(self) -> bool:
        return self._is_changed
    
    @property
    def path(self) -> str:
        return self._path

    @path.setter
    def path(self, new_path: str) -> None:
        self._path = new_path
        self._is_changed = True