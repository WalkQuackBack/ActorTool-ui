from res import ResourceSystem
from utils import *

import oead

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

class TypedParam:
    classes: dict = json.loads(Path("res/pp__TypedParam.json").read_text())

    def __init__(self, data: oead.byml.Dictionary, ext: str):
        self._ext: str = ext.replace(".bgyml", "").replace(".", "")
        self.data: oead.byml.Dictionary = TypedParam.resolve_typed_param(data, self._ext)

    @lru_cache
    @staticmethod
    def load_default(ext: str) -> oead.byml.Dictionary:
        path: str = f"res/TypedParam/{ext}.bgyml"
        if os.path.exists(path):
            return oead.byml.from_binary(Path(path).read_bytes())
        return to_dict({})

    @classmethod
    def resolve_typed_param(cls, data: oead.byml.Dictionary, ext: str) -> oead.byml.Dictionary:
        if "$parent" not in data:
            parent = copy_dict(cls.load_default(ext))
        else:
            parent = cls.resolve_typed_param(oead.byml.from_binary(ResourceSystem.get().load_file(data["$parent"])), ext)
        for prop in cls.classes[ext]["Props"]:
            if prop not in data:
                data[prop] = parent[prop]
        for embed in cls.classes[ext]["Embeds"]:
            if embed not in data:
                data[embed] = cls.resolve_typed_param(parent[embed], cls.classes[ext]["Embeds"][embed]["Type"])
        for composite in cls.classes[ext]["Composites"]:
            if "pp__PropBuffer" in (typename := cls.classes[ext]["Composites"][composite]["Type"]):
                data[composite] = cls.resolve_prop_buffer(data.get(composite, to_array([])), parent[composite])
            elif "pp__TypedParamBuffer" in typename:
                data[composite] = cls.resolve_typed_param_buffer(data.get(composite, to_array([])), parent[composite],
                                                                 typename.replace("pp__TypedParamBuffer<", "").replace(">", ""))
            elif "pp__PropMap" in typename:
                data[composite] = cls.resolve_prop_map(data.get(composite, to_dict({})), parent[composite])
            elif "pp__TypedParamMap" in typename:
                data[composite] = cls.resolve_typed_param_map(data.get(composite, to_dict({})), parent[composite],
                                                              typename.replace("pp__TypedParamMap<", "").replace(">", ""))
            elif "pp__PropEnumMap" in typename:
                data[composite] = cls.resolve_prop_enum_map(data.get(composite, to_dict({})), parent[composite])
            elif "pp__TypedParamEnumMap" in typename:
                data[composite] = cls.resolve_typed_param_enum_map(data.get(composite, to_dict({})), parent[composite],
                                                                   typename.split(",")[1].replace(">", ""))
        return data
        
    @classmethod
    def resolve_prop_buffer(cls, base: oead.byml.Array, parent: oead.byml.Array) -> oead.byml.Array:
        return concat_array(parent, base)
    
    @classmethod
    def resolve_typed_param_buffer(cls, base: oead.byml.Array, parent: oead.byml.Array, ext: str) -> oead.byml.Array:
        return to_array([cls.resolve_typed_param(tp, ext if "$type" not in tp else tp["$type"]) for tp in concat_array(parent, base)])
    
    @classmethod
    def resolve_prop_map(cls, base: oead.byml.Dictionary, parent: oead.byml.Dictionary) -> oead.byml.Dictionary:
        return to_dict({k: (base[k] if k in base else parent[k]) for k in parent}
                                    | {k: base[k] for k in base if k not in parent})
    
    @classmethod
    def resolve_typed_param_map(cls, base: oead.byml.Dictionary, parent: oead.byml.Dictionary, ext: str) -> oead.byml.Dictionary:
        return to_dict({k: (cls.resolve_typed_param(base[k], ext if "$type" not in base[k] else base[k]["$type"]) if k in base
                                      else cls.resolve_typed_param(parent[k], ext if "$type" not in parent[k] else parent[k]["$type"])) for k in parent}
                                      | {k: cls.resolve_typed_param(base[k], ext if "$type" not in base[k] else base[k]["$type"]) for k in base if k not in parent})
    
    # enum maps can be treated the same as parents are all resolved against the default first
    @classmethod
    def resolve_prop_enum_map(cls, base: oead.byml.Dictionary, parent: oead.byml.Dictionary) -> oead.byml.Dictionary:
        return cls.resolve_prop_map(base, parent)
    
    @classmethod
    def resolve_typed_param_enum_map(cls, base: oead.byml.Dictionary, parent: oead.byml.Dictionary, ext: str) -> oead.byml.Dictionary:
        return cls.resolve_typed_param_map(base, parent, ext)

    @property
    def ext(self) -> str:
        return self._ext
    
    def serialize(self) -> bytes:
        return oead.byml.to_binary(self.data, False, 7)