import oead

import os
from typing import Any

def to_dict(d: dict) -> oead.byml.Dictionary:
    return oead.byml.Dictionary(d)

def copy_dict(d: oead.byml.Dictionary) -> oead.byml.Dictionary:
    return oead.byml.Dictionary(dict(d)) # casting to a pydict here is necessary

def to_array(a: list) -> oead.byml.Array:
    return oead.byml.Array(a)

def copy_array(a: oead.byml.Array) -> oead.byml.Array:
    return oead.byml.Array(a)

def concat_array(a: oead.byml.Array, b: oead.byml.Array) -> oead.byml.Array:
    return oead.byml.Array(list(a) + list(b))

# for things with double extensions (like .pack.zs or .engine__actor__ActorParam.bgyml)
def name_no_ext(path: str) -> str:
    return os.path.splitext(os.path.splitext(os.path.basename(path))[0])[0]

# returns the .engine__actor__ActorParam part of whatever.engine__actor__ActorParam.bgyml
def class_ext(path: str) -> str:
    return os.path.splitext(os.path.splitext(path)[0])[1]

def to_oead(object: Any) -> oead.byml.Dictionary | oead.byml.Array | oead.byml.Hash64 | \
                            oead.S32 | oead.U32 | oead.F32 | oead.S64 | oead.U64 | oead.Bytes:
    t = type(object)
    if t not in [int, float, dict, list]:
        return t
    if t == int:
        try:
            return oead.S32(object)
        except:
            return oead.U32(object)
    if t == float:
        return oead.F32(object)
    if t == bytes:
        return oead.Bytes(object)
    if t == list:
        return to_array([
            to_oead(e) for e in object
        ])
    if t == dict:
        out: oead.byml.Dictionary | oead.byml.Hash32 | oead.byml.Hash64
        for key, value in object:
            if type(key) == str:
                out = oead.byml.Dictionary()
                break
            elif type(key) == int:
                out = oead.byml.Hash64()
                break
            else:
                out = oead.byml.Dictionary()
                break
        for key, value in object:
            out[key] = to_oead(value)
        return out