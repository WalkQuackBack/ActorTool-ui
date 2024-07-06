from res import ResourceSystem
from utils import *

import oead

GLOBAL_COMPENDIUMMGR_INSTANCE = None

class CompendiumMgr:
    @classmethod
    def get(cls):
        global GLOBAL_COMPENDIUMMGR_INSTANCE
        if GLOBAL_COMPENDIUMMGR_INSTANCE is None:
            raise ValueError("CompendiumMgr has not yet been initialized")
        return GLOBAL_COMPENDIUMMGR_INSTANCE

    def __init__(self):
        sys: ResourceSystem = ResourceSystem.get()
        self.animals: oead.byml.Dictionary = oead.byml.from_binary(
            sys.load_archive_file(sys.resident_common, "Game/PictureBookInfo/Animal.game__ui__PictureBookInfo.bgyml"))
        self.enemies: oead.byml.Dictionary = oead.byml.from_binary(
            sys.load_archive_file(sys.resident_common, "Game/PictureBookInfo/Enemy.game__ui__PictureBookInfo.bgyml"))
        self.materials: oead.byml.Dictionary = oead.byml.from_binary(
            sys.load_archive_file(sys.resident_common, "Game/PictureBookInfo/Material.game__ui__PictureBookInfo.bgyml"))
        self.treasure: oead.byml.Dictionary = oead.byml.from_binary(
            sys.load_archive_file(sys.resident_common, "Game/PictureBookInfo/Treasure.game__ui__PictureBookInfo.bgyml"))
        self.weapons: oead.byml.Dictionary = oead.byml.from_binary(
            sys.load_archive_file(sys.resident_common, "Game/PictureBookInfo/Weapon.game__ui__PictureBookInfo.bgyml"))
        self.animals_is_changed = False
        self.enemies_is_changed = False
        self.materials_is_changed = False
        self.treasure_is_changed = False
        self.weapons_is_changed = False
        global GLOBAL_COMPENDIUMMGR_INSTANCE
        GLOBAL_COMPENDIUMMGR_INSTANCE = self

    def exists(self, actor: str) -> bool:
        for entry in self.animals["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return True
        for entry in self.enemies["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return True
        for entry in self.materials["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return True
        for entry in self.treasure["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return True
        for entry in self.weapons["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return True
        return False
    
    def get_category(self, actor: str) -> str:
        for entry in self.animals["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return "Animal"
        for entry in self.enemies["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return "Enemy"
        for entry in self.materials["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return "Material"
        for entry in self.treasure["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return "Treasure"
        for entry in self.weapons["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return "Weapon"
        return ""
    
    def get_compendium_data(self, actor: str) -> oead.byml.Dictionary | None:
        for entry in self.animals["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return entry
        for entry in self.enemies["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return entry
        for entry in self.materials["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return entry
        for entry in self.treasure["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return entry
        for entry in self.weapons["PictureBookParamArray"]:
            if entry["ActorNameShort"] == actor:
                return entry
        return None
    
    def copy_compendium_data(self, old: str, new: str) -> bool:
        data: oead.byml.Dictionary | None = self.get_compendium_data(old)
        category: str = self.get_category(old)
        if data is None:
            return False
        else:
            data = copy_dict(data)
        data["ActorNameShort"] = new
        match category:
            case "Animal":
                self.animals["PictureBookParamArray"].append(data)
                self.animals_is_changed = True
            case "Enemy":
                self.enemies["PictureBookParamArray"].append(data)
                self.enemies_is_changed = True
            case "Material":
                self.materials["PictureBookParamArray"].append(data)
                self.materials_is_changed = True
            case "Treasure":
                self.treasure["PictureBookParamArray"].append(data)
                self.treasure_is_changed = True
            case "Weapon":
                self.weapons["PictureBookParamArray"].append(data)
                self.weapons_is_changed = True
            case _:
                return False
        return True
    
    def save(self) -> None:
        sys: ResourceSystem = ResourceSystem.get()
        if self.animals_is_changed:
            sys.save_archive_file("Game/PictureBookInfo/Animal.game__ui__PictureBookInfo.bgyml",
                                      oead.byml.to_binary(self.animals, False, 7), ResourceSystem.ARCHIVE_RESIDENT)
        if self.enemies_is_changed:
            sys.save_archive_file("Game/PictureBookInfo/Enemy.game__ui__PictureBookInfo.bgyml",
                                      oead.byml.to_binary(self.enemies, False, 7), ResourceSystem.ARCHIVE_RESIDENT)
        if self.materials_is_changed:
            sys.save_archive_file("Game/PictureBookInfo/Material.game__ui__PictureBookInfo.bgyml",
                                      oead.byml.to_binary(self.materials, False, 7), ResourceSystem.ARCHIVE_RESIDENT)
        if self.treasure_is_changed:
            sys.save_archive_file("Game/PictureBookInfo/Treasure.game__ui__PictureBookInfo.bgyml",
                                      oead.byml.to_binary(self.treasure, False, 7), ResourceSystem.ARCHIVE_RESIDENT)
        if self.weapons_is_changed:
            sys.save_archive_file("Game/PictureBookInfo/Weapon.game__ui__PictureBookInfo.bgyml",
                                      oead.byml.to_binary(self.weapons, False, 7), ResourceSystem.ARCHIVE_RESIDENT)
        sys.save_archive(sys.resident_common)