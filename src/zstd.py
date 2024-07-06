import zstandard
from oead import Sarc

from functools import lru_cache
from pathlib import Path
from typing import Dict, List

class ZstdContext:
    # Assumes the dictionary IDs have not been altered
    DICT_TYPE_NONE: int = 0
    DICT_TYPE_DEFAULT: int = 1
    DICT_TYPE_BCETT: int = 2
    DICT_TYPE_PACK: int = 3

    @lru_cache
    def __init__(self, dict_path: str = ""):
        decompressor_none: zstandard.ZstdDecompressor = zstandard.ZstdDecompressor()
        archive: Sarc = Sarc(decompressor_none.decompress(Path(dict_path).read_bytes()))
        dicts: Dict[str, zstandard.ZstdCompressionDict] = {f.name: zstandard.ZstdCompressionDict(f.data) for f in archive.get_files()}
        self.decompressors: List[zstandard.ZstdDecompressor] = [
            decompressor_none, # redundant but left in so the indices line up
            zstandard.ZstdDecompressor(dict_data = dicts["zs.zsdic"]),
            zstandard.ZstdDecompressor(dict_data = dicts["bcett.byml.zsdic"]),
            zstandard.ZstdDecompressor(dict_data = dicts["pack.zsdic"])
        ]
        self.compressors: List[zstandard.ZstdCompressor] = [
            zstandard.ZstdCompressor(level = 22),
            zstandard.ZstdCompressor(level = 22, dict_data = dicts["zs.zsdic"], write_dict_id = True, write_content_size = True),
            zstandard.ZstdCompressor(level = 22, dict_data = dicts["bcett.byml.zsdic"], write_dict_id = True, write_content_size = True),
            zstandard.ZstdCompressor(level = 22, dict_data = dicts["pack.zsdic"], write_dict_id = True, write_content_size = True)
        ]
    
    def decompress_file(self, filepath: str) -> bytes:
        if not(filepath.endswith(".zs") or filepath.endswith(".zstd")):
            return Path(filepath).read_bytes()
        data: bytes = Path(filepath).read_bytes()
        return self.decompressors[self.get_dict_id(data)].decompress(data)
    
    def compress_file(self, filepath: str, dict_id: int) -> bytes:
        return self.compressors[dict_id].compress(Path(filepath).read_bytes())
    
    def decompress(self, data: bytes) -> bytes:
        return self.decompressors[self.get_dict_id(data)].decompress(data)
    
    def compress(self, data: bytes, dict_id: int) -> bytes:
        return self.compressors[dict_id].compress(data)

    @staticmethod
    def get_dict_id(data: bytes) -> int:
        if len(data) < 6:
            return 0
        if flag := data[4] & 3 != 0:
            size = 2 ** (flag - 1)
        else:
            return 0
        if data[4] & 0x20 != 0:
            return int.from_bytes(data[5:5+size], "little")
        else:
            return int.from_bytes(data[6:6+size], "little")