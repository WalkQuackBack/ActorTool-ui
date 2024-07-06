from logic import LogicMgr
from res import ResourceSystem
from rsdb import RSDBMgr
from typedparam import TypedParam
from utils import *

import oead

import json
from pathlib import Path
from typing import Callable, Dict, List

GLOBAL_COMPONENT_FACTORY = None

# I should just autogen all of these...
# things I should've done: treat GameParameterTable similarly to ActorParam

class ComponentBase:
    EXT_MAP: Dict[str, str] = json.loads(Path("res/extensions.json").read_text())
    PATH_MAP: Dict[str, str] = json.loads(Path("res/paths.json").read_text())

    def __init__(self):
        self.actor: str = ""
        self._type: str = ""
        self._needs_save: bool = False
    
    @classmethod
    def create(cls, ref_path: str, actor: str, type: str) -> "ComponentBase":
        pass
    
    # should return the new ref path if the component has been edited else None
    def save(self) -> str | None:
        if self._needs_save:
            self._needs_save = False
            return self.ref_path
        return None

    def copy(self) -> None:
        pass

    @property
    def ref_path(self) -> str:
        return f"?{ComponentBase.PATH_MAP[self._type]}/{self.actor}.{ComponentBase.EXT_MAP[self._type]}"
    
    @property
    def name(self) -> str:
        return self._type

class BgymlComponent(ComponentBase):
    def __init__(self):
        super().__init__()
        self._param: oead.byml.Dictionary = to_dict({})

    @classmethod
    def create(cls, ref_path: str, actor: str, type: str) -> "BgymlComponent":
        sys: ResourceSystem = ResourceSystem.get()
        component = cls()
        component.actor = actor
        component._type = type
        if ref_path:
            component._param = TypedParam(oead.byml.from_binary(sys.load_file(ref_path)), cls.EXT_MAP[component._type]).data
        else:
            component._param = TypedParam.load_default(cls.EXT_MAP[component._type])
        return component

    def save(self) -> str | None:
        if self._needs_save:
            sys: ResourceSystem = ResourceSystem.get()
            sys.save_archive_file(self.ref_path[1:], oead.byml.to_binary(self._param, False, 7), ResourceSystem.ARCHIVE_CURRENT)
            self._needs_save = False
            return self.ref_path
        return None

class AIInfoComponent(BgymlComponent):
    def __init__(self):
        super().__init__()

    @staticmethod
    def format_path(path: str) -> str:
        return f"Work/AI/Root/{path}.root.ain"
    
    @property
    def root_ref(self) -> str:
        return self._param["RootAIRef"]
    
    @root_ref.setter
    def root_ref(self, new_ref: str) -> None:
        self._param["RootAIRef"] = self.format_path(new_ref)
        self._needs_save = True
    
    @property
    def post_sensor_ref(self) -> str:
        return self._param["PostSensorAIRef"]
    
    @post_sensor_ref.setter
    def post_sensor_ref(self, new_ref: str) -> None:
        self._param["PostSensorAIRef"] = self.format_path(new_ref)
        self._needs_save = True

    @property
    def post_calc_ref(self) -> str:
        return self._param["PostCalcAIRef"]
    
    @post_calc_ref.setter
    def post_calc_ref(self, new_ref: str) -> None:
        self._param["PostCalcAIRef"] = self.format_path(new_ref)
        self._needs_save = True

    @property
    def post_update_matrix(self) -> str:
        return self._param["PostUpdateMatrix"]
    
    @post_update_matrix.setter
    def post_update_matrix(self, new_ref: str) -> None:
        self._param["PostUpdateMatrix"] = self.format_path(new_ref)
        self._needs_save = True

class AnimationComponent(BgymlComponent):
    def __init__(self):
        super().__init__()

    @property
    def resources(self) -> oead.byml.Array:
        return self._param["AnimationResources"]
    
    def add_resource(self, name: str, retarget: bool = False, ignore_retarget_rate: bool = False, retarget_model: str = "Skeleton") -> None:
        self._param["AnimationResources"].append(to_dict({"ModelProjectName" : name, "IsRetarget" : retarget,
                                                          "IgnoreRetargetRate" : ignore_retarget_rate, "RetargetModel" : retarget_model}))
        self._needs_save = True
    
    def remove_resource(self, name: str) -> bool:
        for i, resource in self._param["AnimationResources"]:
            if resource["ModelProjectName"] == name:
                self._param["AnimationResources"].pop(i)
                self._needs_save = True
                return True
        return False

class ArmorComponent(BgymlComponent):
    def __init__(self):
        super().__init__()
        self._enhancement_material_info: oead.byml.Dictionary | None = None

    @classmethod
    def create(cls, ref_path: str, actor: str, type: str) -> "BgymlComponent":
        sys: ResourceSystem = ResourceSystem.get()
        component = cls()
        component.actor = actor
        component._type = type
        if ref_path:
            component._param = TypedParam(oead.byml.from_binary(sys.load_file(ref_path)), cls.EXT_MAP[component._type]).data
        else:
            component._param = TypedParam.load_default(cls.EXT_MAP[component._type])
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        component._enhancement_material_info = rsdb_mgr.enhancementmaterialinfo.find_row(component.row_id)
        return component
    
    def copy(self, old: str, new: str) -> None:
        if self._enhancement_material_info is not None:
            rsdb_mgr: RSDBMgr = RSDBMgr.get()
            rsdb_mgr.enhancementmaterialinfo.copy_row_to(old, new)
            self._enhancement_material_info = rsdb_mgr.enhancementmaterialinfo.find_row(new)

    @property
    def row_id(self) -> str:
        return f"Work/Actor/{self.actor}.engine__actor__ActorParam.gyml"

    @property
    def next_rank_actor(self) -> str:
        return self._param["NextRankActor"]
    
    @next_rank_actor.setter
    def next_rank_actor(self, actor: str) -> None:
        self._param["NextRankActor"] = actor
        self._needs_save = True
    
    @property
    def series_name(self) -> str:
        return self._param["SeriesName"]
    
    @series_name.setter
    def series_name(self, series: str) -> None:
        self._param["SeriesName"] = series
        self._needs_save = True
    
    @property
    def defense(self) -> oead.S32:
        return self._param["BaseDefense"]
    
    @defense.setter
    def defense(self, defense: oead.S32) -> None:
        self._param["BaseDefense"] = defense
        self._needs_save = True
    
    @property
    def rank(self) -> oead.S32:
        return self._param["Rank"]
    
    @property
    def upgrade_price(self) -> oead.S32 | None:
        if self._enhancement_material_info is None:
            return None
        return self._enhancement_material_info["Price"]

    @upgrade_price.setter
    def upgrade_price(self, price: oead.S32):
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        if self._enhancement_material_info is None:
            self._enhancement_material_info = rsdb_mgr.enhancementmaterialinfo.add_row_by_id(self.row_id)
        self._enhancement_material_info["Price"] = price
        rsdb_mgr.enhancementmaterialinfo._is_changed = True

    def add_effect(self, effect: str, level: oead.S32 | None = None) -> None:
        self._param["ArmorEffect"].append(to_dict({
            "ArmorEffectLevel" : oead.U32(1) if level is None else level, "ArmorEffectType" : effect
        }))
        self._needs_save = True

    # needs to add the group + the group name to the group name list
    def add_hide_group(self, group_name: str, materials: List[str]) -> bool:
        self._param["HiddenMaterialGroupList"].append(to_dict({
            "GroupName" : group_name, "MaterialNameList" : to_array(materials)
        }))
        self._param["HideMaterialGroupNameList"].append(group_name)
        self._needs_save = True

    def add_upgrade_material(self, material: str, count: oead.S32) -> bool:
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        if self._enhancement_material_info is None:
            self._enhancement_material_info = rsdb_mgr.enhancementmaterialinfo.add_row_by_id(self.row_id)
        self._enhancement_material_info["Items"].append(to_dict({
            "Actor" : material, "Number" : count
        }))
        rsdb_mgr.enhancementmaterialinfo._is_changed = True

class ASInfoComponent(BgymlComponent):
    def __init__(self):
        super().__init__()

    def add_autoplay_anim(self, type: str, name: str, is_random: bool = False) -> bool:
        if type not in ["Materials", "BoneVisibilities", "Skeletals", "Shapes"]:
            return False
        self._param[f"AutoPlay{type}"].append(to_dict({
            "FileName" : name, "IsRandom" : is_random
        }))
        self._needs_save = True
        return True

    def remove_autoplay_anim(self, type: str, name: str) -> bool:
        if type not in ["Materials", "BoneVisibilities", "Skeletals", "Shapes"]:
            return False
        for i, anim in enumerate(self._param[f"AutoPlay{type}"]):
            if anim["FileName"] == name:
                self._param[f"AutoPlay{type}"].pop(i)
                self._needs_save = True
                return True
        return False
    
    def add_command(self, command: str, partial: str) -> None:
        self._param["AutoPlayASCommands"].append(to_dict({
            "PartialName" : partial, "Command" : command
        }))
        self._needs_save = True

    def remove_command(self, command: str) -> None:
        for i, cmd in enumerate(self._param["AutoPlayASCommands"]):
            if cmd["Command"] == command:
                self._param["AutoPlayASCommands"].pop(i)
                self._needs_save = True
                return True
        return False

class AttachmentComponent(BgymlComponent):
    def __init__(self):
        super().__init__()
        self._attachment_info: oead.byml.Dictionary = to_dict({})

    @classmethod
    def create(cls, ref_path: str, actor: str, type: str) -> "BgymlComponent":
        sys: ResourceSystem = ResourceSystem.get()
        component = cls()
        component.actor = actor
        component._type = type
        if ref_path:
            component._param = TypedParam(oead.byml.from_binary(sys.load_file(ref_path)), cls.EXT_MAP[component._type]).data
        else:
            component._param = TypedParam.load_default(cls.EXT_MAP[component._type])
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        info: oead.byml.Dictionary | None = rsdb_mgr.attachmentactorinfo.find_row(component.actor)
        if info is not None:
            component._attachment_info = info
        else:
            component._attachment_info = copy_dict(rsdb_mgr.attachmentactorinfo.get_default_row())
            component.sync_attachment_info()
        return component
    
    def sync_attachment_info(self) -> None:
        self._attachment_info["RowId"] = self.actor
        self._attachment_info["AttachmentAdditionalSubType"] = ",".join(self._param["AdditionalSubType"])
        self._attachment_info["AttachmentBindBoneLargeSword"] = self._param["AttachParamLSword_"]["BoneName"]
        self._attachment_info["AttachmentBindBoneSpear"] = self._param["AttachParamSpear_"]["BoneName"]
        self._attachment_info["AttachmentBindBoneSword"] = self._param["AttachParamSword_"]["BoneName"]
        self._attachment_info["AttachmentCommonName"] = self._param["CommonName"]
        self._attachment_info["DetachReplacementActorName"] = self._param["DetachReplacementActorName"]
        self._attachment_info["PushToPouchSpecialParts"] = self._param["PushToPouchSpecialParts"]
        self._attachment_info["AttachmentAdditionalDamage"] = self._param["AdditionalDamage"]
        self._attachment_info["AttachmentMulValueArrow"] = self._param["AdditionalDamageRateArrow"]
        self._attachment_info["AttachmentShieldBashDamage"] = self._param["ShieldBashDamage"]
        # the other ones are from other components and I'm too lazy to sync those

    def copy(self, old: str, new: str) -> None:
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        rsdb_mgr.attachmentactorinfo.copy_row_to(old, new)
        self._attachment_info = rsdb_mgr.attachmentactorinfo.find_row(new)

    @property
    def attachment_info(self) -> oead.byml.Dictionary | None:
        return self._attachment_info

    @property
    def use_common_name(self) -> bool:
        return self._param["IsUseCommonName"]
    
    @use_common_name.setter
    def use_common_name(self, use: bool) -> None:
        self._param["IsUseCommonName"] = use
        self._needs_save = True

    @property
    def common_name(self) -> str:
        return self._param["CommonName"]
    
    @common_name.setter
    def common_name(self, name: str) -> None:
        self._param["CommonName"] = name
        self._attachment_info["AttachmentCommonName"] = name
        self._needs_save = True
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        rsdb_mgr.attachmentactorinfo._is_changed = True

    @property
    def damage(self) -> oead.S32:
        return self._param["AdditionalDamage"]

    @damage.setter
    def damage(self, dmg: oead.S32) -> None:
        self._param["AdditionalDamage"] = dmg
        self._attachment_info["AttachmentAdditionalDamage"] = dmg
        self._needs_save = True
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        rsdb_mgr.attachmentactorinfo._is_changed = True
    
    @property
    def shield_base_damage(self) -> oead.S32:
        return self._param["ShieldBashDamage"]

    @shield_base_damage.setter
    def shield_base_damage(self, dmg: oead.S32) -> None:
        self._param["ShieldBashDamage"] = dmg
        self._attachment_info["AttachmentShieldBashDamage"] = dmg
        self._needs_save = True
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        rsdb_mgr.attachmentactorinfo._is_changed = True
    
    @property
    def arrow_dmg_rate(self) -> oead.F32:
        return self._param["AdditionalDamageRateArrow"]

    @arrow_dmg_rate.setter
    def arrow_dmg_rate(self, dmg: oead.F32) -> None:
        self._param["AdditionalDamageRateArrow"] = dmg
        self._attachment_info["AttachmentMulValueArrow"] = dmg
        self._needs_save = True
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        rsdb_mgr.attachmentactorinfo._is_changed = True

    @property
    def subtypes(self) -> List[str]:
        return list(self._param["AdditionalSubType"])

    def add_subtype(self, subtype: List[str] | oead.byml.Array | str) -> None:
        if type(subtype) in (list, oead.byml.Array):
            for t in subtype:
                if isinstance(t, str) and t not in self._param["AdditionalSubType"]:
                    self._param["AdditionalSubType"].append(t)
        else:
            if isinstance(subtype, str) and subtype not in self._param["AdditionalSubType"]:
                self._param["AdditionalSubType"].append(subtype)
        self._attachment_info["AttachmentAdditionalSubType"] = ",".join(self._param["AdditionalSubType"])
        self._needs_save = True
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        rsdb_mgr.attachmentactorinfo._is_changed = True

    def update_subtypes(self, subtypes: List[str]) -> None:
        subtypes = [t for t in subtypes if isinstance(t, str)]
        self._param["AdditionalSubType"] = to_array(subtypes)
        self._attachment_info["AttachmentAdditionalSubType"] = ",".join(self._param["AdditionalSubType"])
        self._needs_save = True
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        rsdb_mgr.attachmentactorinfo._is_changed = True

# Some blackboards are done through BSA and I can't be bothered to do all that 😭
class BlackboardComponent(BgymlComponent):
    def __init__(self):
        super().__init__()

    def add_blackboard(self, blackboard_name: str) -> bool:
        blackboard_name = self.format_path(blackboard_name)
        if blackboard_name in self._param["BlackboardParamTables"]:
            return False
        self._param["BlackboardParamTables"].append(blackboard_name)
        self._needs_save = True
        return True

    @staticmethod
    def format_path(blackboard_name: str) -> str:
        return f"Work/Component/Blackboard/BlackboardParamTable/{blackboard_name}.engine__component__BlackboardParamTable.gyml"

class BowComponent(BgymlComponent):
    def __init__(self):
        super().__init__()

    def add_hide_group(self, group_name: str, materials: List[str]) -> bool:
        self._param["HiddenMaterialGroupList"].append(to_dict({
            "GroupName" : group_name, "MaterialNameList" : to_array(materials)
        }))
        self._param["HideMaterialGroupNameList"].append(group_name)
        self._needs_save = True

    def add_subtype(self, subtype: List[str] | oead.byml.Array | str) -> None:
        if type(subtype) in (list, oead.byml.Array):
            for t in subtype:
                if isinstance(t, str) and t not in self._param["SubType"]:
                    self._param["SubType"].append(t)
        else:
            if isinstance(subtype, str) and subtype not in self._param["SubType"]:
                self._param["SubType"].append(subtype)
        self._needs_save = True

    def update_subtypes(self, subtypes: List[str]) -> None:
        subtypes = [t for t in subtypes if isinstance(t, str)]
        self._param["SubType"] = to_array(subtypes)
        self._needs_save = True

    @property
    def subtypes(self) -> List[str]:
        return list(self._param["SubType"])

    @property
    def damage(self) -> oead.S32:
        return self._param["BaseAttack"]
    
    @damage.setter
    def damage(self, dmg: oead.S32) -> None:
        self._param["BaseAttack"] = dmg
        self._needs_save = True

class ELinkComponent(BgymlComponent):
    def __init__(self):
        super().__init__()
    
    @property
    def user(self) -> str:
        return self._param["UserName"]
    
    @user.setter
    def user(self, username: str) -> None:
        self._param["UserName"] = username
        self._needs_save = True

# TODO
class GameParameterTable(BgymlComponent):
    def __init__(self):
        super().__init__()

class LifeComponent(BgymlComponent):
    def __init__(self):
        super().__init__()
        self._damage_param: oead.byml.Dictionary | None = None
        self._heal_param: oead.byml.Dictionary | None = None
        self._life_param: oead.byml.Dictionary | None = None
        self._edited_life: bool = False
    
    @classmethod
    def create(cls, ref_path: str, actor: str, type: str) -> "BgymlComponent":
        sys: ResourceSystem = ResourceSystem.get()
        component = cls()
        component.actor = actor
        component._type = type
        if ref_path:
            component._param = TypedParam(oead.byml.from_binary(sys.load_file(ref_path)), cls.EXT_MAP[component._type]).data
        else:
            component._param = copy_dict(TypedParam.load_default(cls.EXT_MAP[component._type]))
        if component._param["DamageParameters"]:
            component._damage_param = oead.byml.from_binary(sys.load_file(component._param["DamageParameters"]))
        if component._param["HealParameters"]:
            component._heal_param = oead.byml.from_binary(sys.load_file(component._param["HealParameters"]))
        if component._param["LifeParameters"]:
            component._life_param = oead.byml.from_binary(sys.load_file(component._param["LifeParameters"]))
        return component
    
    @property
    def damage_param_path(self) -> str:
        return f"Work/Life/DamageParameters/{self.actor}.game__life__DamageParameters.gyml"
    
    @property
    def heal_param_path(self) -> str:
        return f"Work/Life/HealParameters/{self.actor}.game__life__HealParameters.gyml"

    @property
    def life_param_path(self) -> str:
        return f"Work/Life/LifeParameters/{self.actor}.game__life__LifeParameters.gyml"
    
    @property
    def life(self) -> oead.S32 | None:
        if self._life_param == None:
            return None
        return self._life_param["MaxLife"]
    
    @life.setter
    def life(self, value: oead.S32) -> None:
        if self._life_param == None:
            self._life_param = copy_dict(TypedParam.load_default("game__life__LifeParameters"))
        self._life_param["MaxLife"] = value
        self._needs_save = True
        self._edited_life = True
    
    def save(self) -> str | None:
        if self._needs_save:
            sys: ResourceSystem = ResourceSystem.get()
            if self._edited_life:
                self._param["LifeParameters"] = self.life_param_path
                sys.save_archive_file(f"Life/LifeParameters/{self.actor}.game__life__LifeParameters.bgyml",
                                      oead.byml.to_binary(self._life_param, False, 7), ResourceSystem.ARCHIVE_CURRENT)
            sys.save_archive_file(self.ref_path[1:], oead.byml.to_binary(self._param, False, 7), ResourceSystem.ARCHIVE_CURRENT)
            self._needs_save = False
            self._edited_life = False
            return self.ref_path
        return None

class ModelInfoComponent(BgymlComponent):
    def __init__(self):
        super().__init__()
    
    @property
    def fmdb(self) -> str:
        return self._param["FmdbName"]
    
    @fmdb.setter
    def fmdb(self, model_name: str) -> None:
        self._param["FmdbName"] = model_name
        self._needs_save = True

    @property
    def model_project(self) -> str:
        return self._param["ModelProjectName"]
    
    @model_project.setter
    def model_project(self, project_name: str) -> None:
        self._param["ModelProjectName"] = project_name
        self._needs_save = True

# TODO (mostly bc lazy)
class PhysicsComponent(BgymlComponent):
    def __init__(self):
        super().__init__()

class PouchContentComponent(BgymlComponent):
    def __init__(self):
        super().__init__()

    @property
    def category(self) -> str:
        return self._param["Category"]

    @category.setter
    def category(self, category: str) -> None:
        self._param["Category"] = category
        self._needs_save = True

    @property
    def special_deal(self) -> str:
        return self._param["SpecialDeal"]
    
    @special_deal.setter
    def special_deal(self, special_deal: str) -> None:
        self._param["SpecialDeal"] = special_deal
        self._needs_save = True

class ShieldComponent(BgymlComponent):
    def __init__(self):
        super().__init__()

    def add_hide_group(self, group_name: str, materials: List[str]) -> bool:
        self._param["HiddenMaterialGroupList"].append(to_dict({
            "GroupName" : group_name, "MaterialNameList" : to_array(materials)
        }))
        self._param["HideMaterialGroupNameList"].append(group_name)
        self._needs_save = True

    def add_subtype(self, subtype: List[str] | oead.byml.Array | str) -> None:
        if type(subtype) in (list, oead.byml.Array):
            for t in subtype:
                if isinstance(t, str) and t not in self._param["SubType"]:
                    self._param["SubType"].append(t)
        else:
            if isinstance(subtype, str) and subtype not in self._param["SubType"]:
                self._param["SubType"].append(subtype)
        self._needs_save = True

    def update_subtypes(self, subtypes: List[str]) -> None:
        subtypes = [t for t in subtypes if isinstance(t, str)]
        self._param["SubType"] = to_array(subtypes)
        self._needs_save = True

    @property
    def subtypes(self) -> List[str]:
        return list(self._param["SubType"])

    @property
    def damage(self) -> oead.S32:
        return self._param["BaseAttack"]
    
    @damage.setter
    def damage(self, dmg: oead.S32) -> None:
        self._param["BaseAttack"] = dmg
        self._needs_save = True  

    @property
    def guard_power(self) -> oead.S32:
        return self._param["GuardPower"]
    
    @guard_power.setter
    def guard_power(self, type: oead.S32) -> None:
        self._param["GuardPower"] = type
        self._needs_save = True    

class SLinkComponent(BgymlComponent):
    def __init__(self):
        super().__init__()
    
    @property
    def user(self) -> str:
        return self._param["UserName"]
    
    @user.setter
    def user(self, username: str) -> None:
        self._param["UserName"] = username
        self._needs_save = True

class WeaponComponent(BgymlComponent):
    def __init__(self):
        super().__init__()

    def add_hide_group(self, group_name: str, materials: List[str]) -> bool:
        self._param["HiddenMaterialGroupList"].append(to_dict({
            "GroupName" : group_name, "MaterialNameList" : to_array(materials)
        }))
        self._param["HideMaterialGroupNameList"].append(group_name)
        self._needs_save = True

    def add_subtype(self, subtype: List[str] | oead.byml.Array | str) -> None:
        if type(subtype) in (list, oead.byml.Array):
            for t in subtype:
                if isinstance(t, str) and t not in self._param["SubType"]:
                    self._param["SubType"].append(t)
        else:
            if isinstance(subtype, str) and subtype not in self._param["SubType"]:
                self._param["SubType"].append(subtype)
        self._needs_save = True

    def update_subtypes(self, subtypes: List[str]) -> None:
        subtypes = [t for t in subtypes if isinstance(t, str)]
        self._param["SubType"] = to_array(subtypes)
        self._needs_save = True

    @property
    def subtypes(self) -> List[str]:
        return list(self._param["SubType"])

    @property
    def damage(self) -> oead.S32:
        return self._param["BaseAttack"]
    
    @damage.setter
    def damage(self, dmg: oead.S32) -> None:
        self._param["BaseAttack"] = dmg
        self._needs_save = True  

    @property
    def weapon_type(self) -> str:
        return self._param["WeaponType"]
    
    @weapon_type.setter
    def weapon_type(self, type: str) -> None:
        self._param["WeaponType"] = type
        self._needs_save = True

class XLinkComponent(BgymlComponent):
    def __init__(self):
        super().__init__()
    
    @property
    def row(self) -> oead.byml.Dictionary | None:
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        return rsdb_mgr.xlinkpropertytablelist.find_row(self._param["PropertyTableListRef"])
    
    @row.setter
    def row(self, new_row: str) -> None:
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        if rsdb_mgr.xlinkpropertytablelist.find_row(new_row) is None:
            rsdb_mgr.xlinkpropertytablelist.copy_row(self._param["PropertyTableListRef"], new_row)
        self._param["PropertyTableListRef"] = new_row
        self._needs_save = True

# The non-bgyml components

# User is expected to provide the edited the ASB file themselves
class ASComponent(ComponentBase):
    def __init__(self):
        super().__init__()
        self._original_path: str = ""
    
    @classmethod
    def create(cls, ref_path: str, actor: str, type: str) -> "ASComponent":
        component = cls()
        component.actor = actor
        component._type = type
        component._original_path = ref_path
        return component
    
    @property
    def baev_path(self) -> str:
        return self.ref_path[1:].replace(".root.asb", ".root.baev").replace("AS/", "AnimationEvent/AsNode")

# these two are just placeholders for now
class EffectBlurComponent(ComponentBase):
    def __init__(self):
        super().__init__()
    
    @classmethod
    def create(cls, ref_path: str, actor: str, type: str) -> "EffectBlurComponent":
        component = cls()
        component.actor = actor
        component._type = type
        return component
    
class DestructiblePieceComponent(ComponentBase):
    def __init__(self):
        super().__init__()
    
    @classmethod
    def create(cls, ref_path: str, actor: str, type: str) -> "DestructiblePieceComponent":
        component = cls()
        component.actor = actor
        component._type = type
        return component

class ActorLogicNodeComponent(ComponentBase):
    def __init__(self):
        super().__init__()
        self._node: oead.byml.Dictionary | None = to_dict({})

    @classmethod
    def create(cls, ref_path: str, actor: str, type: str) -> "ActorLogicNodeComponent":
        component = cls()
        component.actor = actor
        component._type = type
        node_name: str = os.path.basename(ref_path).split(".")[0]
        logic_mgr: LogicMgr = LogicMgr.get()
        component._node = logic_mgr.get_node(node_name)
        return component

    @ComponentBase.ref_path.getter
    def ref_path(self) -> str:
        return f"Work/{ComponentBase.PATH_MAP[self._type]}/ActorLogic{self.actor}.{ComponentBase.EXT_MAP[self._type]}"

class ComponentFactory:
    @classmethod
    def get(cls) -> "ComponentFactory":
        global GLOBAL_COMPONENT_FACTORY
        if GLOBAL_COMPONENT_FACTORY is None:
            raise ValueError("ComponentFactory has not yet been initialized")
        return GLOBAL_COMPONENT_FACTORY

    def __init__(self):
        self._factories: Dict[str, Callable[[str, str, str], ComponentBase]] = {}

        self.register_all()

        global GLOBAL_COMPONENT_FACTORY
        GLOBAL_COMPONENT_FACTORY = self

    def register_all(self) -> None:
        self.register_component("Default", BgymlComponent.create)
        self.register_component("ActorLogicNodeRef", ActorLogicNodeComponent.create)
        self.register_component("AIInfoRef", AIInfoComponent.create)
        self.register_component("AnimationRef", AnimationComponent.create)
        self.register_component("ASInfoRef", ASInfoComponent.create)
        self.register_component("ASRef", ASComponent.create)
        self.register_component("AttachmentRef", AttachmentComponent.create)
        self.register_component("ArmorRef", ArmorComponent.create)
        self.register_component("BlackboardRef", BlackboardComponent.create)
        self.register_component("BowRef", BowComponent.create)
        self.register_component("DestructiblePiece", DestructiblePieceComponent.create)
        self.register_component("ELinkRef", ELinkComponent.create)
        self.register_component("EffectBlur", EffectBlurComponent.create)
        self.register_component("LifeRef", LifeComponent.create)
        self.register_component("ModelInfoRef", ModelInfoComponent.create)
        self.register_component("PouchContentRef", PouchContentComponent.create)
        self.register_component("ShieldRef", ShieldComponent.create)
        self.register_component("SLinkRef", SLinkComponent.create)
        self.register_component("WeaponRef", WeaponComponent.create)
        self.register_component("XLinkRef", XLinkComponent.create)

    def register_component(self, name: str, callback: Callable[[str, str, str], ComponentBase]) -> None:
        self._factories[name] = callback
    
    def create(self, name: str, ref_path: str, actor: str) -> ComponentBase:
        if name not in ComponentBase.EXT_MAP:
            print(f"Unknown component reference type: {name}")
            return ComponentBase()
        if name not in self._factories:
            return self._factories["Default"](ref_path, actor, name)
        return self._factories[name](ref_path, actor, name)