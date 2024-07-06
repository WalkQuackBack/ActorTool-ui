from res import ResourceSystem
from utils import *
from zstd import ZstdContext

import oead

from typing import Dict

GLOBAL_LOGICMGR_INSTANCE = None

# was this class even worth creating lol

class LogicMgr:
    VER_MAP: Dict[int, int] = {
        100 : 100,
        110 : 110,
        111 : 110,
        112 : 110,
        120 : 120,
        121 : 120
    }

    @classmethod
    def get(cls) -> "LogicMgr":
        global GLOBAL_LOGICMGR_INSTANCE
        if GLOBAL_LOGICMGR_INSTANCE is None:
            raise ValueError("LogicMgr has not yet been initialized")
        return GLOBAL_LOGICMGR_INSTANCE

    def __init__(self):
        sys: ResourceSystem = ResourceSystem.get()
        self._nodes: oead.byml.Dictionary = oead.byml.from_binary(sys.load_file(self.path))
        self._is_changed: bool = False
        global GLOBAL_LOGICMGR_INSTANCE
        GLOBAL_LOGICMGR_INSTANCE = self
    
    def get_node(self, name: str) -> oead.byml.Dictionary | None:
        for node in self._nodes:
            if node == name:
                return self._nodes[node]
        return None
    
    def exists(self, name: str) -> bool:
        for node in self._nodes:
            if node == name:
                return True
        return False
    
    def copy_node(self, old: str, new: str) -> bool:
        if new == old:
            return False
        if self.exists(new):
            return False
        node: oead.byml.Dictionary | None = self.get_node(old)
        if node is None:
            return False
        node = copy_dict(node)
        self._nodes[new] = node
        self._is_changed = True
        return True
    
    def save(self) -> None:
        if self._is_changed:
            sys: ResourceSystem = ResourceSystem.get()
            sys.save_file(self.path, oead.byml.to_binary(self._nodes, False, 7), ZstdContext.DICT_TYPE_DEFAULT)

    @property
    def path(self) -> str:
        sys: ResourceSystem = ResourceSystem.get()
        return f"Logic/NodeDefinition/Node.Product.{LogicMgr.VER_MAP[sys.version]}.aidefn.byml.zs"