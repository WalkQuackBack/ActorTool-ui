from archive import Archive
from component import *
from res import ResourceSystem
from typedparam import TypedParam
from utils import *
from zstd import ZstdContext

import oead

from typing import List

class ActorPack():
    # These might be completely unused? the files don't exist and there's no references in the executable afaict...
    PREACTOR_ACTORONLY: str = "?ActorSystem/PreActorSetting/ActorOnly.game__actor__PreActorSetting.bgyml"
    PREACTOR_CONSTPASSIVE: str = "?ActorSystem/PreActorSetting/ConstPassive.game__actor__PreActorSetting.bgyml"
    PREACTOR_ANCHOR: str = "?ActorSystem/PreActorSetting/Anchor.game__actor__PreActorSetting.bgyml"
    PREACTOR_USEPREACTORRENDERER: str = "?ActorSystem/PreActorSetting/UsePreActorRenderer.game__actor__PreActorSetting.bgyml"

    def __init__(self, name: str):
        if name != "":
            sys: ResourceSystem = ResourceSystem.get()
            self._name: str = name
            self._pack: Archive
            self._label: str = ""
            self._generate_method: str = ""
            self._category: str = ""
            self._actor_setting: str = ""
            self._preactor_setting: str = ""
            self._name_ref: str = ""
            self._gmd_setting: str = ""
            self._game_life_condition: str = ""
            self._components: List[ComponentBase] = []
            self._orig_refs: Dict[str, str] = {}
            archive: Archive | None = sys.load_archive(f"Pack/Actor/{self._name}.pack.zs")
            if archive is None:
                self._pack = Archive()
                # All actors must have these two components it appears
                self._preactor_setting = ActorPack.PREACTOR_CONSTPASSIVE
                # I guess please don't remove this file?
                self._actor_setting = "?ActorSystem/ActorSystemSetting/GameActorDefault.engine__actor__ActorSystemSetting.bgyml"
                self._orig_refs = {
                    "PreActorSettingRef" : self._preactor_setting,
                    "SystemSetting" : self._actor_setting
                }
            else:
                self._pack = archive
                actor_param: TypedParam = TypedParam(oead.byml.from_binary(self.load_file(self.actor_param_path)), "engine__actor__ActorParam")
                self.parse_actor_param(actor_param.data)
        else:
            raise ValueError("Cannot initialize ActorPack with empty name")
    
    def parse_actor_param(self, actor_param: oead.byml.Dictionary) -> None:
        if "GenerateMethod" in actor_param:
            self._generate_method = actor_param["GenerateMethod"]
        if "Label" in actor_param:
            self._label = actor_param["Label"]
        if "Category" in actor_param:
            self._category = actor_param["Category"]
        # I really should be handling the creation of dependent components if they're missing but lazy :v
        # Ex. ASComponent is dependent on ModelInfoComponent so if ASComponent exists but ModelInfoComponent doesn't, add it
        if "Components" in actor_param:
            factory: ComponentFactory = ComponentFactory.get()
            for component in actor_param["Components"]:
                self._orig_refs[component] = actor_param["Components"][component]
                if (ref := actor_param["Components"][component]) == "":
                    continue
                if component == "ActorNameRef":
                    self._name_ref = ref
                    continue
                if component == "PreActorSettingRef":
                    self._preactor_setting = ref
                    continue
                if component == "SystemSetting":
                    self._actor_setting = ref
                    continue
                if component == "ActorGameDataSetting":
                    self._gmd_setting = ref
                    continue
                if component == "GameLifeConditionRef":
                    self._game_life_condition = ref
                    continue
                self._components.append(factory.create(component, actor_param["Components"][component], self._name))

    def gen_actor_param(self) -> oead.byml.Dictionary:
        actor_param: oead.byml.Dictionary = to_dict({})
        if self._label:
            actor_param["Label"] = self._label
        if self._category:
            actor_param["Category"] = self._category
        if self._generate_method:
            actor_param["GenerateMethod"] = self._generate_method
        if self._components:
            actor_param["Components"] = to_dict({})
            if self._preactor_setting:
                actor_param["Components"]["PreActorSettingRef"] = self._preactor_setting
            if self._name_ref:
                actor_param["Components"]["ActorNameRef"] = self._name_ref
            if self._actor_setting:
                actor_param["Components"]["SystemSetting"] = self._actor_setting
            if self._gmd_setting:
                actor_param["Components"]["ActorGameDataSetting"] = self._gmd_setting
            if self._game_life_condition:
                actor_param["Components"]["GameLifeConditionRef"] = self._game_life_condition
            for component in self._components:
                path: str | None = component.save()
                if path is None:
                    actor_param["Components"][component.name] = self._orig_refs[component.name]
                else:
                    actor_param["Components"][component.name] = path
        return actor_param

    def save(self) -> None:
        if self.is_changed:
            self._pack.update_file(self.actor_param_path, oead.byml.to_binary(self.gen_actor_param(), False, 7))
        sys: ResourceSystem = ResourceSystem.get()
        sys.save_file(self._pack.path, self._pack.serialize(), ZstdContext.DICT_TYPE_PACK)
        return
        
    def load_file(self, filepath: str) -> bytes | None:
        if (sys := ResourceSystem.get()).archive != self._pack:
            sys.archive = self._pack
        return sys.load_file(filepath)
    
    def get_component(self, name: str) -> ComponentBase | None:
        for component in self._components:
            if component.name == name:
                return component
        return None
    
    def add_component(self, type: str) -> ComponentBase | None:
        if self.get_component(type) is not None:
            return None
        factory: ComponentFactory = ComponentFactory.get()
        self._components.append(component := factory.create(type, "", self._name))
        return component
    
    def remove_component(self, type: str) -> bool:
        for i, component in enumerate(self._components):
            if component.name == type:
                self._components.pop(i)
                return True
        return False
    
    @property
    def name(self) -> str:
        return self._name
    
    @name.setter
    def name(self, new_name: str) -> None:
        if new_name == self._name:
            return
        old_actor_param: str = self.actor_param_path
        self._name = new_name
        self._pack.path = f"Pack/Actor/{new_name}.pack.zs"
        self._pack.rename_file(old_actor_param, self.actor_param_path)
    
    @property
    def actor_param_path(self) -> str:
        return f"Actor/{self._name}.engine__actor__ActorParam.bgyml"

    @property
    def path(self) -> str:
        return self._pack.path
    
    @property
    def is_changed(self) -> str:
        if self._pack.is_changed:
            return True
        for component in self._components:
            if component._needs_save:
                return True
        return False