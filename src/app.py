from compendium import CompendiumMgr
from component import ComponentFactory
from gmd import GameDataMgr
from logic import LogicMgr
from res import ResourceSystem
from rsdb import RSDBMgr

GLOBAL_APP_INSTANCE = None

class App:
    @classmethod
    def get(cls) -> "App":
        global GLOBAL_APP_INSTANCE
        if GLOBAL_APP_INSTANCE is None:
            raise ValueError("App backend has not yet been initialized")
        return GLOBAL_APP_INSTANCE

    def __init__(self, project_path: str, romfs_path: str, enable_logs: bool = True):
        self.sys = ResourceSystem(project_path, romfs_path, enable_logs) # initialize ResourceSystem
        self.rsdb_mgr: RSDBMgr = RSDBMgr()
        self.gmd_mgr: GameDataMgr = GameDataMgr()
        self.comp_mgr: CompendiumMgr = CompendiumMgr()
        self.logic_mgr: LogicMgr = LogicMgr()
        self.component_factory: ComponentFactory = ComponentFactory()

        global GLOBAL_APP_INSTANCE
        GLOBAL_APP_INSTANCE = self
    
    def save(self) -> None:
        self.rsdb_mgr.save()
        self.gmd_mgr.save()
        self.comp_mgr.save()
        self.logic_mgr.save()
        self.sys.save()