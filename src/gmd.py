from res import ResourceSystem
from utils import *
from zstd import ZstdContext

import mmh3
import oead

import math
from pathlib import Path
from typing import Dict, List

GAMEDATA_TYPES = [
    "Bool", "BoolArray", "Int", "IntArray", "Float", "FloatArray", "Enum", "EnumArray", "Vector2", "Vector2Array", "Vector3", "Vector3Array",
    "String16", "String16Array", "String32", "String32Array", "String64", "String64Array", "Binary", "BinaryArray", "UInt", "UIntArray",
    "Int64", "Int64Array", "UInt64", "UInt64Array", "WString16", "WString16Array", "WString32", "WString32Array", "WString64","WString64Array",
    "Struct", "BoolExp", "Bool64bitKey"
]

RESET_TYPES = [
    "cOnSceneChange", "cOnGameDayChange", "cOptionReset", "cOnBloodyMoon", "cOnStartNewData", "cOnGameDayChangeRandom",
    "cOnSceneInitialize", "cZonauEnemyRespawnTimer", "cRandomRevival", "cOnStartNewDataOnly"
]

MAP_COLUMNS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

GLOBAL_GAMEDATAMGR_INSTANCE = None

class FlagHandle:
    def __init__(self, name: str, datatype: str, copy_name: str, parent: str = "", members: List[tuple[str, str]] = []):
        self.name: str = name
        self.datatype: str = datatype
        self.parent: str = parent
        self.flag_to_copy: str = copy_name
        self.members: List[tuple[str, str]]
        if self.datatype == "Struct":
            self.members = members
        else:
            self.members = []

class GameDataMgr:
    @classmethod
    def get(cls) -> "GameDataMgr":
        global GLOBAL_GAMEDATAMGR_INSTANCE
        if GLOBAL_GAMEDATAMGR_INSTANCE is None:
            raise Exception("GameDataMgr has not yet been initialized")
        return GLOBAL_GAMEDATAMGR_INSTANCE

    def __init__(self):
        self.sys: ResourceSystem = ResourceSystem.get()
        self._list: oead.byml.Dictionary = oead.byml.from_binary(
            self.sys.load_file(f"GameData/GameDataList.Product.{100 if self.sys.version == 100 else 110}.byml.zs"))
        hashes: oead.byml.Dictionary = oead.byml.from_binary(Path("res/hashes.byml").read_bytes())
        self.hash_map: Dict[int, str] = {int(k): hashes[k] for k in hashes}
        self._is_changed: bool = False
        global GLOBAL_GAMEDATAMGR_INSTANCE
        GLOBAL_GAMEDATAMGR_INSTANCE = self

    @staticmethod
    def hash(string: str) -> oead.U32:
        return oead.U32(mmh3.hash(string, signed=False))
    
    def try_reverse_hash(self, hash: int | oead.U32) -> str | None:
        hash = int(hash)
        if hash in self.hash_map:
            return self.hash_map[hash] if self.hash_map[hash] != "???" else None
        return None
    
    def add_string(self, string: str) -> None:
        if (mm_hash := self.hash(string)) not in self.hash_map:
            self.hash_map[mm_hash] = string

    @staticmethod
    def reset_type_value(*types: str) -> oead.S32:
        value: int = 0
        for t in types:
            if t in RESET_TYPES:
                value |= (2 ** RESET_TYPES.index(t))
        return oead.S32(value)
    
    @staticmethod
    def get_reset_types(value: int | oead.S32) -> List[str]:
        value = int(value)
        types: List[str] = []
        for i in range(len(RESET_TYPES)):
            if value & (2 ** i):
                types.append(RESET_TYPES[i])
        return types
    
    @staticmethod
    def extra_byte(map_unit: str) -> oead.S32:
        # needs to be A1 - J8
        if len(map_unit) != 2:
            return oead.S32(0) # invalid
        if map_unit[0] not in MAP_COLUMNS:
            return oead.S32(0)
        if not map_unit[1].isdigit() or int(map_unit[1]) not in range(9):
            return oead.S32(0)
        return oead.S32(MAP_COLUMNS.index(map_unit[0]) + 10 * (int(map_unit[1]) - 1) + 1)
    
    @staticmethod
    def get_map_unit(extra_byte: int | oead.S32) -> str | None:
        extra_byte = int(extra_byte)
        if extra_byte > 80 or extra_byte < 1:
            return None
        return MAP_COLUMNS[(extra_byte - 1) % 10] + str(int(((extra_byte - 1) - (extra_byte - 1) % 10) / 10 + 1))
    
    @staticmethod
    def get_data_size(datatype: str, entry: oead.byml.Dictionary) -> int:
        size: int = 8
        n: int
        if "Array" in datatype:
            size += 4
            if "ArraySize" in entry:
                n = int(entry["ArraySize"])
            elif "Size" in entry:
                n = int(entry["Size"])
            elif isinstance(entry["DefaultValue"], oead.byml.Array):
                n = len(entry["DefaultValue"])
            else:
                raise ValueError(f"Could not determine array size for {datatype} - {'0x%08x' % int(entry['Hash'])}")
        else:
            n = 1
        if datatype in ["Bool", "Int", "UInt", "Float", "Enum"]:
            pass
        elif datatype == "BoolArray":
            size += math.ceil((4 if math.ceil(n / 8) < 4 else math.ceil(n / 8)) / 4) * 4
        elif datatype in ["IntArray", "FloatArray", "UIntArray", "EnumArray"]:
            size += n * 4
        elif "Vector2" in datatype:
            size += n * 8
        elif "Vector3" in datatype:
            size += n * 12
        elif "WString16" in datatype:
            size += n * 32
        elif "WString32" in datatype:
            size += n * 64
        elif "WString64" in datatype:
            size += n * 128
        elif "String16" in datatype:
            size += n * 16
        elif "String32" in datatype:
            size += n * 32
        elif "String64" in datatype:
            size += n * 64
        elif "Int64" in datatype or "UInt64" in datatype:
            size += n * 8
        elif datatype == "Bool64bitKey":
            pass
        elif "Binary" in datatype:
            size += n * 4
            size += n * int(entry["DefaultValue"])
        elif datatype in ["Struct", "BoolExp"]:
            pass
        else:
            raise ValueError(f"Invalid Type: {datatype}")
        return size

    def calc_save_file_size(self) -> tuple[List[int], List[int], int, int]:
        sizes: List[int] = [0x20 + 8 * 34 for i in range(7)]
        offsets: List[int] = [0x20 + 8 * 34 for i in range(7)]
        size: int = 0x20 + 8 * 34
        offset: int = 0x20 + 8 * 34
        has_key: bool = False
        has_keys: List[bool] = [False for i in range(7)]
        for datatype in GAMEDATA_TYPES:
            if datatype in ["Struct", "BoolExp"]:
                continue
            if datatype in self._list["Data"]:
                for entry in self._list["Data"][datatype]:
                    if datatype == "Bool64bitKey":
                        has_key = True
                    else:
                        offset += 8
                    size += (s := self.get_data_size(datatype, entry))
                    if (i := int(entry["SaveFileIndex"])) != -1:
                        if datatype == "Bool64bitKey":
                            has_keys[i] = True
                        else:
                            offsets[i] += 8
                        sizes[i] += s
        sizes = [sizes[i] + 8 if has_keys[i] else sizes[i] for i in range(7)]
        if has_key:
            size += 8
        for i in range(7):
            if self._list["MetaData"]["SaveDirectory"][i] == "":
                sizes[i] = 0
                offsets[i] = 0
        return sizes, offsets, size, offset
    
    def update_metadata(self) -> None:
        sizes, offsets, size, offset = self.calc_save_file_size()
        self._list["MetaData"] = {
            "AllDataSaveOffset": oead.S32(offset),
            "AllDataSaveSize": oead.S32(size),
            "FormatVersion": oead.S32(1),
            "SaveDataOffsetPos": to_array([oead.S32(i) for i in offsets]),
            "SaveDataSize": to_array([oead.S32(i) for i in sizes]),
            "SaveDirectory": self._list["MetaData"]["SaveDirectory"],
            "SaveTypeHash": self._list["MetaData"]["SaveTypeHash"]
        }

    def save(self) -> None:
        if not self._is_changed:
            return
        self.update_metadata()
        sys:ResourceSystem = ResourceSystem.get()
        sys.save_file(f"GameData/GameDataList.Product.{100 if self.sys.version == 100 else 110}.byml.zs",
                      oead.byml.to_binary(self._list, False, 7), ZstdContext.DICT_TYPE_DEFAULT) # vanilla file is big endian but who cares
        self._is_changed = False
    
    def add_flag(self, flag: oead.byml.Dictionary, datatype: str, overwrite: bool = True) -> bool:
        if datatype not in GAMEDATA_TYPES:
            return False
        if datatype not in self._list["Data"]:
            self._list["Data"][datatype] = oead.byml.Array()
            self._list["Data"][datatype].append(flag)
            return True
        for i, f in enumerate(self._list["Data"][datatype]):
            if int(f["Hash"]) == int(flag["Hash"]):
                if overwrite:
                    self._list["Data"][datatype][i] = flag
                    return True
                else:
                    return False
        self._list["Data"][datatype].append(flag)
        self._is_changed = True
        return True
    
    def delete_flag(self, hash: int | oead.U32, datatype: str) -> bool:
        if datatype not in self._list["Data"]:
            return False
        hash = int(hash)
        for i, f in enumerate(self._list["Data"][datatype]):
            if hash == int(f["Hash"]):
                self._list["Data"][datatype].pop(i)
                self._is_changed = True
                return True
        return False
    
    def get_flag(self, hash: int | oead.U32, datatype: str) -> oead.byml.Dictionary | None:
        if datatype not in self._list["Data"]:
            return False
        hash = int(hash)
        for i, f in enumerate(self._list["Data"][datatype]):
            if hash == int(f["Hash"]):
                return self._list["Data"][datatype][i]
        return None
    
    def get_struct_flag(self, hash: int | oead.U32, datatype: str, struct: oead.byml.Dictionary) -> oead.byml.Dictionary | None:
        if datatype not in self._list["Data"]:
            return False
        hash = int(hash)
        for member in struct["DefaultValue"]:
            if hash == int(member["Hash"]):
                return self.get_flag(member["Value"], datatype)
        return False
    
    def get_struct_flag_by_name(self, member_name: str, struct_name: str, datatype: str) -> oead.byml.Dictionary | None:
        if datatype not in self._list["Data"]:
            return None
        struct: oead.byml.Dictionary | None = self.get_flag(self.hash(struct_name), "Struct")
        if struct is None:
            return None
        return self.get_struct_flag(self.hash(member_name), datatype, struct)
    
    def add_struct_flag(self, flag: oead.byml.Dictionary, datatype: str, struct: oead.byml.Dictionary,
                        member_hash: int | oead.U32, overwrite: bool = True) -> bool:
        if datatype not in GAMEDATA_TYPES:
            return False
        if datatype not in self._list["Data"]:
            self._list["Data"][datatype] = oead.byml.Array()
        for member in struct["DefaultValue"]:
            if int(member["Value"]) == int(flag["Hash"]) and overwrite:
                member["Hash"] = oead.U32(member_hash)
                return self.add_flag(flag, datatype, overwrite)
            else:
                return False
        member.append(to_dict({"Hash" : oead.U32(member_hash), "Value" : oead.U32(flag["Hash"])}))
        return self.add_flag(flag, datatype, overwrite)
    
    def hash_exists(self, hash: int | oead.U32, datatype: str) -> bool:
        if datatype not in self._list["Data"]:
            return False
        for flag in self._list["Data"]:
            if int(flag["Hash"]) == int(hash):
                return True
        return False

    def copy_flag(self, old_hash: int | oead.U32, new_hash: int | oead.U32, datatype: str) -> bool:
        if int(old_hash) == int(new_hash):
            return False
        if self.hash_exists(new_hash):
            return False
        new_flag: oead.byml.Dictionary = self.get_flag(old_hash, datatype)
        if new_flag is None:
            return False
        else:
            new_flag = copy_dict(new_flag)
        new_flag["Hash"] = oead.U32(new_hash)
        return self.add_flag(new_flag, datatype)
    
    def copy_struct_flag(self, old_name: str, new_name: str, struct_name: str, datatype: str) -> bool:
        if datatype not in self._list["Data"]:
            return False
        if old_name == new_name:
            return False
        old_hash: oead.U32 = self.hash(old_name)
        new_hash: oead.U32 = self.hash(new_name)
        struct_hash: oead.U32 = self.hash(struct_name)
        struct : oead.byml.Dictionary | None = self.get_flag(struct_hash, "Struct")
        if struct is None:
            return False
        exists: bool = False
        for member in struct:
            if int(member["Hash"]) == int(new_hash):
                return False
            elif int(member["Hash"]) == int(old_hash):
                exists = True
                hash: oead.U32 = member["Value"]
        if not exists:
            return False
        new_flag: oead.byml.Dictionary | None = self.get_flag(hash, datatype)
        if new_flag is None:
            return False
        else:
            new_flag = copy_dict(new_flag)
        new_flag["Hash"] = new_flag_hash = self.hash(f"{struct_name}.{new_name}")
        struct.append(to_dict({"Hash" : new_hash, "Value" : new_flag_hash}))
        return self.add_flag(new_flag, datatype)
    
    @staticmethod
    def clear_struct(struct: oead.byml.Dictionary) -> None:
        struct["DefaultValue"] = to_array([])
    
    def add_flag_handle(self, handle: FlagHandle) -> bool:
        copy_name: str = f"{handle.parent}.{handle.flag_to_copy}" if handle.parent else handle.flag_to_copy
        flag: oead.byml.Dictionary | None = self.get_flag(self.hash(copy_name), handle.datatype)
        if flag is None:
            print(f"Original flag {copy_name} did not exist")
            return False
        new_flag = copy_dict(flag)
        name_hash: oead.U32 = self.hash(handle.name)
        full_name: str
        if handle.parent != "":
            parent: oead.byml.Dictionary | None = self.get_flag(self.hash(handle.parent), "Struct")
            if parent is None:
                print(f"Could not find parent struct {handle.parent}")
                return False
            full_name = f"{handle.parent}.{handle.name}"
            for member in parent["DefaultValue"]:
                if int(member["Hash"]) == int(name_hash):
                    print(f"Flag {handle.name} already exists in parent struct")
                    return False
            parent["DefaultValue"].append(to_dict({"Hash" : name_hash, "Value" : self.hash(full_name)}))
        else:
            full_name = handle.name
        new_flag["Hash"] = self.hash(full_name)
        if handle.datatype == "Struct":
            self.clear_struct(new_flag)
            for member in handle.members:
                mem_flag: oead.byml.Dictionary | None = self.get_flag(self.hash(f"{copy_name}.{member[0]}"), member[1])
                if mem_flag is None:
                    print(f"Could not find flag {copy_name}.{member[0]} to copy")
                    return False
                mem_flag["Hash"] = mem_hash = self.hash(f"{full_name}.{member[0]}")
                self.add_flag(mem_flag, member[1])
                new_flag["DefaultValue"].append(to_dict({"Hash" : self.hash(member[0]), "Value" : mem_hash}))
        return self.add_flag(new_flag, handle.datatype)