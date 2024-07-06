from archive import Archive
import oead
from zstd import ZstdContext

import os
from pathlib import Path

GLOBAL_RESOURCESYSTEM_INSTANCE = None

# Simple resource management system that handles loading from archives and mod projects
# When loading a file, use its path relative to the romfs directory/archive path
class ResourceSystem:
    ARCHIVE_CURRENT = 0
    ARCHIVE_RESIDENT = 1
    ARCHIVE_BOOTUP = 2
    
    @classmethod
    def get(cls) -> "ResourceSystem":
        global GLOBAL_RESOURCESYSTEM_INSTANCE
        if not GLOBAL_RESOURCESYSTEM_INSTANCE:
            raise Exception("ResourceSystem has not yet been initialized")
        return GLOBAL_RESOURCESYSTEM_INSTANCE

    def __init__(self, project_path: str, romfs_path: str = "", enable_logs: bool = True):
        self._current_archive: Archive | None = None
        self._is_log: bool = enable_logs
        self.romfs_path = romfs_path
        self.project_path = project_path
        try:
            self.init_zstd_ctx(self.romfs_path)
            self.is_init_ctx = True
            if self._is_log:
                self.log("ZstdContext initialized")
        except:
            self.is_init_ctx = False
            if self._is_log:
                self.log("Failed to initialize ZstdContext")
        self.resident_common: Archive | None = self.load_archive("Pack/ResidentCommon.pack.zs")
        self.bootup: Archive | None = self.load_archive("Pack/Bootup.Nin_NX_NVN.pack.zs")
        self._version: int = self.get_version()
        if self._is_log:
            self.log(f"ResourceSystem initialized | VER: {self.version}")
        global GLOBAL_RESOURCESYSTEM_INSTANCE
        GLOBAL_RESOURCESYSTEM_INSTANCE = self

    def log(self, message: str) -> None:
        print(message) # was gonna do more with this but never got around to it

    def init_zstd_ctx(self, romfs_path: str) -> None:
        self.ctx: ZstdContext = ZstdContext(os.path.join(romfs_path, "Pack/ZsDic.pack.zs"))
        
    def resolve_path(self, path: str, full_path = True) -> str:
        if path.startswith("Work/"):
            path = path[5:]
        elif path.startswith("/") or path.startswith("?"):
            path = path[1:]
        if not full_path or os.path.isabs(path):
            return path.replace(".gyml", ".bgyml")
        if os.path.exists(fixed_path := os.path.join(self.project_path, path)):
            return fixed_path.replace(".gyml", ".bgyml")
        return os.path.join(self.romfs_path, path).replace(".gyml", ".bgyml")

    def _load_file(self, path: str) -> bytes:
        if self._is_log:
            print(f"Loading {path}")
        if self.is_init_ctx:
            return self.ctx.decompress_file(path)
        return Path(path).read_bytes()
    
    def outpath(self, path: str) -> str:
        return os.path.join(self.project_path, path)
    
    def load_archive(self, path: str) -> Archive | None:
        fixed_path = self.resolve_path(path)
        if os.path.exists(fixed_path):
            try:
                return Archive.from_sarc(oead.Sarc(self._load_file(fixed_path)), path)
            except:
                pass
        return None
        
    def load_archive_file(self, archive: Archive, path: str) -> bytes | None:
        if archive is None:
            return None
        file = archive.get_file(self.resolve_path(path, False))
        if file is None:
            return None
        if self._is_log:
            self.log(f"Loading {path} from {os.path.basename(archive.path)}")
        return file
    
    def load_file(self, path: str) -> bytes | None:
        file = self.load_archive_file(self._current_archive, path)
        if file is not None:
            return file
        file = self.load_archive_file(self.resident_common, path)
        if file is not None:
            return file
        file = self.load_archive_file(self.bootup, path)
        if file is not None:
            return file
        path = self.resolve_path(path)
        if os.path.exists(path):
            return self._load_file(path)
        else:
            if self._is_log:
                print(f"Failed to load {path}")
            return None
    
    def save_file(self, path: str, data: bytes | None, compress_type: int = ZstdContext.DICT_TYPE_NONE) -> None:
        if data is None:
            return
        if self._is_log:
            self.log(f"Saving {path}")
        path = os.path.join(self.project_path, path)
        if (dir := os.path.dirname(path)) != "":
            os.makedirs(dir, exist_ok=True)
        with open(path, "wb") as f:
            f.write(self.ctx.compress(data, compress_type))

    def save_archive_file(self, path: str, data: bytes | None, archive_type: int = ARCHIVE_CURRENT) -> None:
        if data is None:
            return
        if self._is_log:
            if archive_type == ResourceSystem.ARCHIVE_CURRENT:
                self.log(f"Saving {path} to {os.path.basename(self._current_archive.path)}")
            elif archive_type == ResourceSystem.ARCHIVE_BOOTUP:
                self.log(f"Saving {path} to {os.path.basename(self.bootup.path)}")
            elif archive_type == ResourceSystem.ARCHIVE_RESIDENT:
                self.log(f"Saving {path} to {os.path.basename(self.resident_common.path)}")
        if archive_type == ResourceSystem.ARCHIVE_CURRENT:
            self._current_archive.update_file(path, data)
        elif archive_type == ResourceSystem.ARCHIVE_RESIDENT:
            self.resident_common.update_file(path, data)
        elif archive_type == ResourceSystem.ARCHIVE_BOOTUP:
            self.resident_common.update_file(path, data)

    def save_archive(self, archive: Archive) -> None:
        if archive is None:
            return
        data = archive.serialize()
        if data is None:
            return
        if self._is_log:
            self.log(f"Saving {os.path.basename(archive.path)}")
        path: str = os.path.join(self.project_path, archive.path)
        if (dir := os.path.dirname(path)) != "":
            os.makedirs(dir, exist_ok=True)
        with open(path, "wb") as f:
            f.write(self.ctx.compress(data, ZstdContext.DICT_TYPE_PACK))
    
    def save(self) -> None:
        self.save_archive(self.bootup)
        self.save_archive(self.resident_common)
        self.save_archive(self._current_archive)
        if self._is_log:
            self.log("Saved project files")

    def change_project_dir(self, project_path: str, is_save: bool = True) -> None:
        if is_save:
            self.save()
        self.project_path = project_path
        self.resident_common: Archive | None = self.load_archive("Pack/ResidentCommon.pack.zs")
        self.bootup: Archive | None = self.load_archive("Pack/Bootup.Nin_NX_NVN.pack.zs")
        self._current_archive: Archive | None = None

    @property
    def archive(self) -> Archive:
        return self._current_archive
    
    @archive.setter
    def archive(self, new_archive: Archive) -> None:
        self.save_archive(self._current_archive)
        self._current_archive = new_archive
        if self._is_log:
            self.log(f"Changing current archive to {os.path.basename(self._current_archive.path)}")
    
    @property
    def is_log(self) -> bool:
        return self._is_log
    
    @is_log.setter
    def is_log(self, state: bool) -> None:
        self._is_log = state
        self.log(f"Logging {'' if self._is_log else 'de'}activated")

    @property
    def version(self) -> int:
        return self._version

    def get_version(self) -> int:
        data: bytes | None = self.load_file("System/RegionLangMask.txt")
        if data is None:
            return 121 # default if failed to load
        text: str = data.decode()
        return int(text.splitlines()[2])
    
    def exists_in_project(self, filepath: str) -> bool:
        return os.path.exists(os.path.join(self.project_path, filepath))
    
    def exists_in_romfs(self, filepath: str) -> bool:
        return os.path.exists(os.path.join(self.romfs_path, filepath))