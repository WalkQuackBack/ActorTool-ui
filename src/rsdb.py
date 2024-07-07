from res import ResourceSystem
from utils import *
from zstd import ZstdContext

from bitarray import bitarray
import oead

import copy
from pathlib import Path
from typing import Dict, List

GLOBAL_RSDBMGR_INSTANCE = None

RSDB_EXT_MAP = {
    "ActorInfo" : "engine__rsdb__ActorInfoTable.bgyml",
    "GameActorInfo" : "game__GameActorInfoTable.bgyml",
    "AttachmentActorInfo" : "game__AttachmentActorInfoTable.bgyml",
    "XLinkPropertyTable" : "engine__rsdb__XLinkPropertyTable.bgyml",
    "XLinkPropertyTableList" : "engine__rsdb__XLinkProeprtyTableListTable.bgyml",
    "EnhancementMaterialInfo" : "game__EnhancementMaterialInfoTable.bgyml"
}

# ignores the RankTable since it's seemingly unused
class TagTable:
    def __init__(self, data: oead.byml.Dictionary):
        self._tags: List[sorted] = list(data["TagList"])
        tag_count = len(self._tags)
        tag_data = bitarray()
        tag_data.frombytes(data["BitTable"])
        tag_data.bytereverse()
        self._actors: Dict[str, List[str]] = {}
        self._scenes: Dict[str, List[str]] = {}
        actor_count: int = int(len(data["PathList"]) / 3)
        for actor_id in range(actor_count):
            if data["PathList"][actor_id * 3 + 2] == ".engine__actor__ActorParam.gyml":
                self._actors[name := data["PathList"][actor_id * 3 + 1]] = []
                for tag_id, tag in enumerate(self._tags):
                    if tag_data[actor_id * tag_count + tag_id]:
                        self._actors[name].append(tag)
            else:
                self._scenes[name := data["PathList"][actor_id * 3 + 1]] = []
                for tag_id, tag in enumerate(self._tags):
                    if tag_data[actor_id * tag_count + tag_id]:
                        self._scenes[name].append(tag)
        self._is_changed: bool = False
        
    def serialize(self) -> bytes | None:
        if self._is_changed:
            self._tags.sort()
            actors: List[str] = list(self._actors.keys())
            actors.sort()
            scenes: List[str] = list(self._scenes.keys())
            scenes.sort()
            output: oead.byml.Dictionary = to_dict({
                "BitTable" : oead.Bytes(b''),
                "PathList" : to_array([]),
                "RankTable": oead.Bytes(b''),
                "TagList" : to_array([])
            })
            output["TagList"] = to_array(self._tags)
            bits: List[int] = []
            for actor in actors:
                output["PathList"].append("Work/Actor/")
                output["PathList"].append(actor)
                output["PathList"].append(".engine__actor__ActorParam.gyml")
                for tag in self._tags:
                    if tag not in self._actors[actor]:
                        bits.append(0)
                    else:
                        bits.append(1)
            for scene in scenes:
                output["PathList"].append("Work/Scene/")
                output["PathList"].append(scene)
                output["PathList"].append(".engine__scene__SceneParam.gyml")
                for tag in self._tags:
                    if tag not in self._scenes[scene]:
                        bits.append(0)
                    else:
                        bits.append(1)
            bit_table: bitarray = bitarray(bits)
            bit_table.bytereverse()
            output["BitTable"] = oead.Bytes(bit_table.tobytes())
            self._is_changed = False
            return oead.byml.to_binary(output, False, 7)
        return None
    
    def add_tag(self, tag: str) -> None:
        if tag not in self._tags:
            self._tags.append(tag)
            self._is_changed = True

    # this might break things in tag def
    def remove_tag(self, tag: str) -> None:
        if tag in self._tags:
            print(f"Warning: Globally removing tag {tag} from tag list")
            self._tags.remove(tag)
            self._is_changed = True

    @property
    def tags(self) -> List[str]:
        return self._tags
    
    @property
    def actors(self) -> List[str]:
        return list(self._actors.keys())

    def actor_has_tags(self, actor: str) -> List[str]:
        if actor not in self._actors:
            return False
        return bool(self._actors[actor])
    
    def actor_add_tag(self, actor: str, tag: str, force_add: bool = False) -> bool:
        if actor not in self._actors:
            self._actors[actor] = []
        if tag in self._tags:
            self._actors[actor].append(tag)
            self._is_changed = True
            return True
        elif force_add:
            self._tags.append(tag)
            self._actors[actor].append(tag)
            self._is_changed = True
            return True
        else:
            return False
    
    def actor_remove_tag(self, actor: str, tag: str) -> None:
        if actor not in self._actors:
            return
        if tag in self._actors[actor]:
            self._actors[actor].remove(tag)
            self._is_changed = True
    
    def actor_clear_tags(self, actor: str) -> None:
        if actor not in self._actors:
            return
        self._actors[actor] = []
        self._is_changed = True

    def actor_set_tags(self, actor: str, tags: List[str]) -> None:
        if actor not in self._actors:
            self._actors[actor] = []
        tags = [tag for tag in tags if tag in self.tags]
        self._actors[actor] = tags
        self._is_changed = True

    def add_actor(self, actor: str) -> None:
        if actor not in self._actors:
            self._actors[actor] = []
            self._is_changed = True
    
    def delete_actor(self, actor: str) -> None:
        if actor in self._actors:
            del self._actors[actor]
            self._is_changed = True

    def copy_actor(self, new_actor: str, base_actor: str, allow_overwrite: bool = False) -> bool:
        if base_actor not in self._actors:
            return False
        if new_actor in self._actors and not allow_overwrite:
            return False
        self._actors[new_actor] = copy.copy(self._actors[base_actor])
        self._is_changed = True
        return True

    def get_actor_tags(self, actor: str) -> List[str]:
        return self._actors.get(actor, [])

class ResourceTable:
    def __init__(self, data: oead.byml.Array, name: str):
        self._table: oead.byml.Array = data
        self._name: str = name
        self._is_changed: bool = False

    def is_exist(self, key: str) -> bool:
        for row in self._table:
            if row["__RowId"] == key:
                return True
        return False

    def find_row(self, key: str) -> oead.byml.Dictionary | None:
        for row in self._table:
            if row["__RowId"] == key:
                return row
        return None
    
    def add_row(self, row: oead.byml.Dictionary) -> None:
        self._table.append(row)
        self._is_changed = True
    
    def add_row_by_id(self, row_id: str) -> None:
        self.add_row(self.get_new_default_row(row_id))
        self._is_changed = True

    def copy_row(self, from_id: str, to_id: str) -> bool:
        if self.is_exist(to_id):
            return False
        row: oead.byml.Dictionary | None = self.find_row(from_id)
        if row is None:
            return False
        new_row: oead.byml.Dictionary = copy_dict(row)
        new_row["__RowId"] = to_id
        self._table.append(new_row)
        self._is_changed = True
        return True
    
    def copy_row_to(self, from_id: str, to_id: str) -> bool:
        row: oead.byml.Dictionary | None = self.find_row(from_id)
        if row is None:
            return False
        new_row: oead.byml.Dictionary = copy_dict(row)
        new_row["__RowId"] = to_id
        if self.is_exist(to_id):
            for i, r in enumerate(self._table):
                if r["__RowId"] == to_id:
                    self._table[i] = new_row
                    break
        else:
            self._table.append(new_row)
        self._is_changed = True
        return True
    
    def get_default_row(self) -> oead.byml.Dictionary:
        return oead.byml.from_binary(Path(f"res/RSDB/{RSDB_EXT_MAP[self._name]}").read_bytes())

    def get_new_default_row(self, row_id: str) -> oead.byml.Dictionary:
        row: oead.byml.Dictionary = self.get_default_row()
        row["__RowId"] = row_id
        return row
    
    def serialize(self) -> bytes | None:
        if self._is_changed == True:
            self._is_changed = False
            return oead.byml.to_binary(self._table, False, 7)
        return None

class RSDBMgr:
    @classmethod
    def get(cls) -> "RSDBMgr":
        global GLOBAL_RSDBMGR_INSTANCE
        if GLOBAL_RSDBMGR_INSTANCE is None:
            raise Exception("RSDBMGr has not yet been initialized")
        return GLOBAL_RSDBMGR_INSTANCE

    def __init__(self):
        sys: ResourceSystem = ResourceSystem.get()
        self._tag: TagTable = TagTable(oead.byml.from_binary(
            sys.load_file(f"RSDB/Tag.Product.{sys.version}.rstbl.byml.zs")))
        self._actorinfo: ResourceTable = ResourceTable(oead.byml.from_binary(
            sys.load_file(f"RSDB/ActorInfo.Product.{sys.version}.rstbl.byml.zs")), "ActorInfo")
        self._gameactorinfo: ResourceTable = ResourceTable(oead.byml.from_binary(
            sys.load_file(f"RSDB/GameActorInfo.Product.{sys.version}.rstbl.byml.zs")), "GameActorInfo")
        self._pouchactorinfo: ResourceTable = ResourceTable(oead.byml.from_binary(
            sys.load_file(f"RSDB/PouchActorInfo.Product.{sys.version}.rstbl.byml.zs")), "PouchActorInfo")
        self._attachmentactorinfo: ResourceTable = ResourceTable(oead.byml.from_binary(
            sys.load_file(f"RSDB/AttachmentActorInfo.Product.{sys.version}.rstbl.byml.zs")), "AttachmentActorInfo")
        self._xlinkpropertytable: ResourceTable = ResourceTable(oead.byml.from_binary(
            sys.load_file(f"RSDB/XLinkPropertyTable.Product.{sys.version}.rstbl.byml.zs")), "XLinkPropertyTable")
        self._xlinkpropertytablelist: ResourceTable = ResourceTable(oead.byml.from_binary(
            sys.load_file(f"RSDB/XLinkPropertyTableList.Product.{sys.version}.rstbl.byml.zs")), "XLinkPropertyTableList")
        self._enhancementmaterialinfo: ResourceTable = ResourceTable(oead.byml.from_binary(
            sys.load_file(f"RSDB/EnhancementMaterialInfo.Product.{sys.version}.rstbl.byml.zs")), "EnhancementMaterialInfo")
        global GLOBAL_RSDBMGR_INSTANCE
        GLOBAL_RSDBMGR_INSTANCE = self
    
    @property
    def actorinfo(self) -> ResourceTable:
        return self._actorinfo
    
    @property
    def gameactorinfo(self) -> ResourceTable:
        return self._gameactorinfo
    
    @property
    def pouchactorinfo(self) -> ResourceTable:
        return self._pouchactorinfo
    
    @property
    def attachmentactorinfo(self) -> ResourceTable:
        return self._attachmentactorinfo
    
    @property
    def xlinkpropertytable(self) -> ResourceTable:
        return self._xlinkpropertytable
    
    @property
    def xlinkpropertytablelist(self) -> ResourceTable:
        return self._xlinkpropertytablelist
    
    @property
    def enhancementmaterialinfo(self) -> ResourceTable:
        return self._enhancementmaterialinfo
    
    @property
    def tagtable(self) -> TagTable:
        return self._tag
    
    def save(self) -> None:
        sys: ResourceSystem = ResourceSystem.get()
        sys.save_file(f"RSDB/Tag.Product.{sys.version}.rstbl.byml.zs", self.tagtable.serialize(), ZstdContext.DICT_TYPE_DEFAULT)
        sys.save_file(f"RSDB/ActorInfo.Product.{sys.version}.rstbl.byml.zs", self.actorinfo.serialize(), ZstdContext.DICT_TYPE_DEFAULT)
        sys.save_file(f"RSDB/GameActorInfo.Product.{sys.version}.rstbl.byml.zs", self.gameactorinfo.serialize(), ZstdContext.DICT_TYPE_DEFAULT)
        sys.save_file(f"RSDB/PouchActorInfo.Product.{sys.version}.rstbl.byml.zs", self.pouchactorinfo.serialize(), ZstdContext.DICT_TYPE_DEFAULT)
        sys.save_file(f"RSDB/AttachmentActorInfo.Product.{sys.version}.rstbl.byml.zs", self.attachmentactorinfo.serialize(), ZstdContext.DICT_TYPE_DEFAULT)
        sys.save_file(f"RSDB/XLinkPropertyTable.Product.{sys.version}.rstbl.byml.zs", self.xlinkpropertytable.serialize(), ZstdContext.DICT_TYPE_DEFAULT)
        sys.save_file(f"RSDB/XLinkPropertyTableList.Product.{sys.version}.rstbl.byml.zs", self.xlinkpropertytablelist.serialize(), ZstdContext.DICT_TYPE_DEFAULT)
        sys.save_file(f"RSDB/EnhancementMaterialInfo.Product.{sys.version}.rstbl.byml.zs", self.enhancementmaterialinfo.serialize(), ZstdContext.DICT_TYPE_DEFAULT)