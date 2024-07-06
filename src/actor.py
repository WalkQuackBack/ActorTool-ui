from app import App
from compendium import CompendiumMgr
from component import *
from gmd import GameDataMgr, FlagHandle
from pack import ActorPack
from res import ResourceSystem
from rsdb import RSDBMgr
from utils import *

import oead

from math import ceil, floor
from typing import List

class Actor:
    # GameData flag presets -> list of lists (list of flags)
    # For each flag: index 0 is the type, index 1 is the parent struct name, index 2 is the list of struct members for structs
    GENERIC_POUCH = [["Bool", "IsGet", []],
                     ["Bool", "IsGetAnyway", []]]
    GENERIC_COMPENDIUM = [["Struct", "PictureBookData", [("IsNew", "Bool"), ("State", "Enum")]]]
    GENERIC_THROWABLE_MATERIAL = [["UInt", "MaterialShortCutCounter", []]]
    GENERIC_ENEMY = [["Struct", "EnemyBattleData",
                      [("GuardJustCount", "Int"), ("JustAvoidCount", "Int"), ("DefeatedNoDamageCount", "Int"), ("HeadShotCount", "Int")]],
                      ["Int", "DefeatedEnemyNum", []]]
    
    def __init__(self, name: str):
        self._name: str = name.replace("Pack/Actor/", "").replace(".pack.zs", "")
        self.load_resource_table_rows()
        self.load_actor_pack()
        comp_mgr: CompendiumMgr = CompendiumMgr.get()
        self._has_compendium_entry: bool = comp_mgr.exists(self._name)
    
    # probably should rework this, storing a direct reference might not be smart bc it makes editing annoying
    # you have to manually tell the table that it's been changed rather than having a setter that handles that for you
    def load_resource_table_rows(self) -> None:
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        self._tags: List[str] = rsdb_mgr.tagtable.get_actor_tags(self._name)
        self._actor_info: oead.byml.Dictionary | None = rsdb_mgr.actorinfo.find_row(self._name)
        self._game_info: oead.byml.Dictionary | None = rsdb_mgr.gameactorinfo.find_row(self._name)
        if self._actor_info is None:
            rsdb_mgr.actorinfo.add_row_by_id(self._name)
            self._actor_info = rsdb_mgr.actorinfo.find_row(self._name)
        if self._game_info is None:
            rsdb_mgr.gameactorinfo.add_row_by_id(self._name)
            self._game_info = rsdb_mgr.gameactorinfo.find_row(self._name)
        self._pouch_info: oead.byml.Dictionary | None = rsdb_mgr.pouchactorinfo.find_row(self._name)

    def load_actor_pack(self) -> None:
        sys: ResourceSystem = ResourceSystem.get()
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        self._pack: ActorPack | None
        if sys.exists_in_project(f"Pack/Actor/{self._name}.pack.zs") or sys.exists_in_romfs(f"Pack/Actor/{self._name}.pack.zs"):
            self._pack = ActorPack(self._name)
            # ActorPack-dependent Resource Tables
            self._attachment_info: oead.byml.Dictionary | None = rsdb_mgr.attachmentactorinfo.find_row(self._name)
            self._enhancement_info: oead.byml.Dictionary | None = rsdb_mgr.enhancementmaterialinfo.find_row(
                self._pack.actor_param_path.replace(".bgyml", ".gyml")
            )
        else:
            self._pack = None

    @property
    def components(self) -> oead.byml.Dictionary:
        return self._pack.components
    
    @property
    def actor_info(self) -> oead.byml.Dictionary:
        return self._actor_info
    
    @property
    def tags(self) -> List[str]:
        return self._tags
    
    @property
    def name(self) -> str:
        return self._name
    
    @name.setter
    def name(self, name: str) -> None:
        self._name = name
        if self._pack is not None:
            self._pack.name = name
    
    @staticmethod
    def copy(name: str, base_actor_name: str) -> "Actor":
        if name == base_actor_name:
            return Actor(name)
        sys = ResourceSystem.get()
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        actor: Actor
        if sys.exists_in_project(path := f"Pack/Actor/{name}.pack.zs") or sys.exists_in_romfs(path):
            actor = Actor(name)
        else:
            actor = Actor(base_actor_name)
            actor.name = name
        rsdb_mgr.actorinfo.copy_row_to(base_actor_name, name)
        actor._actor_info = rsdb_mgr.actorinfo.find_row(name)
        rsdb_mgr.gameactorinfo.copy_row_to(base_actor_name, name)
        actor._game_info = rsdb_mgr.gameactorinfo.find_row(name)
        rsdb_mgr.tagtable.copy_actor(name, base_actor_name)
        actor._tags = rsdb_mgr.tagtable.get_actor_tags(name)
        if actor._pouch_info is not None:
            rsdb_mgr.pouchactorinfo.copy_row(base_actor_name, name)
        if actor._has_compendium_entry:
            comp_mgr: CompendiumMgr = CompendiumMgr.get()
            comp_mgr.copy_compendium_data(base_actor_name, name)
            actor.copy_flags(base_actor_name, Actor.GENERIC_COMPENDIUM)
        if actor._pack is not None:
            actor._pack.name = name
            for component in actor._pack._components:
                component.actor = name
            if (attachment_component := actor._pack.get_component("AttachmentRef")) is not None:
                attachment_component.copy(base_actor_name, name)
            if (pouch_content_component := actor._pack.get_component("PouchContentRef")) is not None:
                actor.copy_flags(base_actor_name, Actor.GENERIC_POUCH)
                if attachment_component is not None and pouch_content_component.category in ["Material", "SpecialParts"]:
                    actor.copy_flags(base_actor_name, Actor.GENERIC_THROWABLE_MATERIAL)
            if (armor_component := actor._pack.get_component("ArmorRef")) is not None:
                armor_component.copy(base_actor_name, name)
            if (gp_tbl_component := actor._pack.get_component("GameParameterTableRef")) is not None:
                if (path:= gp_tbl_component._param["Components"]["EnemyCommonParam"]) != "":
                    actor.copy_flags(base_actor_name, Actor.GENERIC_ENEMY)
                    # scuffed saving bc I don't feel like implementing GameParameterTable
                    gmd_mgr: GameDataMgr = GameDataMgr.get()
                    enemy_common: oead.byml.Dictionary = TypedParam(oead.byml.from_binary(sys.load_file(path)), "game__enemy__EnemyCommonParam").data
                    enemy_common["DefeatedNumGameDataHash"] = gmd_mgr.hash(f"DefeatedEnemyNum.{actor._name}")
                    enemy_common["DefeatedNoDamageCountHash"] = gmd_mgr.hash(f"EnemyBattleData.{actor._name}.DefeatedNoDamageCount")
                    enemy_common["GuardJustCountHash"] = gmd_mgr.hash(f"EnemyBattleData.{actor._name}.GuardJustCount")
                    enemy_common["HeadShotCountHash"] = gmd_mgr.hash(f"EnemyBattleData.{actor._name}.HeadShotCount")
                    enemy_common["JustAvoidCountHash"] = gmd_mgr.hash(f"EnemyBattleData.{actor._name}.JustAvoidCount")
                    gp_tbl_component._param["Components"]["EnemyCommonParam"] = f"?GameParameter/EnemyCommonParam/{actor._name}.game__enemy__EnemyCommonParam.bgyml"
                    gp_tbl_component._needs_save = True
                    sys.save_archive_file(f"GameParameter/EnemyCommonParam/{actor._name}.game__enemy__EnemyCommonParam.bgyml",
                                          oead.byml.to_binary(enemy_common, False, 7), ResourceSystem.ARCHIVE_CURRENT)
        return actor
    
    # move the mgr save calls to the app class
    def save(self) -> None:
        if self._pack is not None:
            self._pack.save()
        app: App = App.get()
        app.save()

    def copy_flags(self, old: str, preset: List[List[str | List[tuple[str, str]]]]) -> bool:
        gmd_mgr: GameDataMgr = GameDataMgr.get()
        handles: List[FlagHandle] = self.preset_to_handles(old, preset)
        for handle in handles:
            if not gmd_mgr.add_flag_handle(handle):
                print(f"{handle.parent} failed to be added")
                return False
        return True

    def preset_to_handles(self, to_copy: str, preset: List[List[str | List[tuple[str, str]]]]) -> List[FlagHandle]:
        handles: List[FlagHandle] = []
        for flag in preset:
            handles.append(FlagHandle(self._name, flag[0], to_copy, flag[1], flag[2]))
        return handles
    
    def get_or_add_component(self, name: str) -> ComponentBase:
        component: ComponentBase | None = self._pack.get_component(name)
        if component is not None:
            return component
        return self._pack.add_component(name)
    
    def add_anim_resource(self, name: str, retarget: bool = False, ignore_retarget_rate: bool = False, retarget_model: str = "Skeleton") -> None:
        if "AnimationResources" not in self._actor_info:
            self._actor_info["AnimationResources"] = to_array([])
        self._actor_info["AnimationResources"].append(to_dict({"ModelProjectName" : name, "IsRetarget" : retarget,
                                                          "IgnoreRetargetRate" : ignore_retarget_rate, "RetargetModel" : retarget_model}))
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        # I don't like having to set this manually but not sure how to avoid that without manually creating settings for every param
        rsdb_mgr.actorinfo._is_changed = True
        if self._pack is None:
            return
        anim_component: AnimationComponent | None = self.get_or_add_component("AnimationRef")
        anim_component.add_resource(name, retarget, ignore_retarget_rate, retarget_model)

    def remove_anim_resource(self, name: str) -> None:
        if "AnimationResources" not in self._actor_info:
            pass
        for i, resource in enumerate(self._actor_info["AnimationResources"]):
            if resource["ModelProjectName"] == name:
                self._actor_info["AnimationResources"].pop(i)
                rsdb_mgr: RSDBMgr = RSDBMgr.get()
                rsdb_mgr.actorinfo._is_changed = True
                if self._pack is None:
                    return
                else:
                    break
        anim_component: AnimationComponent | None = self.get_or_add_component("AnimationRef")
        anim_component.remove_resource(name)

    def set_model(self, fmdb_name: str, project_name: str) -> None:
        self._actor_info["FmdbName"] = fmdb_name
        self._actor_info["ModelProjectName"] = project_name
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        rsdb_mgr.actorinfo._is_changed = True
        if self._pack is None:
            return
        model_component: ModelInfoComponent | None = self.get_or_add_component("ModelInfoRef")
        model_component.fmdb = fmdb_name
        model_component.model_project = project_name

    def set_slink_user(self, username: str) -> None:
        self._actor_info["SLinkUserName"] = username
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        rsdb_mgr.actorinfo._is_changed = True
        if self._pack is None:
            return
        slink_component: SLinkComponent | None = self.get_or_add_component("SLinkRef")
        slink_component.user = username
    
    def set_elink_user(self, username: str) -> None:
        self._actor_info["ELinkUserName"] = username
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        rsdb_mgr.actorinfo._is_changed = True
        if self._pack is None:
            return
        elink_component: ELinkComponent | None = self.get_or_add_component("ELinkRef")
        elink_component.user = username

    # ActorInfo doesn't actually support shape anims but ASInfo does
    def add_autoplay_anim(self, type: str, anim: str, is_random: bool = False) -> bool:
        if type not in ["Materials", "BoneVisibilities", "Skeletals", "Shapes"]:
            return False
        if (key := f"AutoPlay{type}") not in self.actor_info:
            self.actor_info[key] = to_array([])
        self.actor_info[key].append(to_dict({
            "FileName" : anim, "IsRandom" : is_random
        }))
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        rsdb_mgr.actorinfo._is_changed = True
        if self._pack is None:
            return True
        as_info_component: ASInfoComponent = self.get_or_add_component("ASInfoRef")
        return as_info_component.add_autoplay_anim(type, anim, is_random)

    def remove_autoplay_anim(self, type: str, anim: str) -> bool:
        if type not in ["Materials", "BoneVisibilities", "Skeletals", "Shapes"]:
            return False
        if (key := f"AutoPlay{type}") not in self.actor_info:
            return False
        for i, a in enumerate(self.actor_info[key]):
            if a["FileName"] == anim:
                self.actor_info[key].pop(i)
                rsdb_mgr: RSDBMgr = RSDBMgr.get()
                rsdb_mgr.actorinfo._is_changed = True
                if self._pack is None:
                    return True
                else:
                    break
        as_info_component: ASInfoComponent = self.get_or_add_component("ASInfoRef")
        return as_info_component.remove_autoplay_anim(type, anim)
    
    # botw_actor_tool has this so might as well add it ig, simple enough to implement
    def set_create_priority(self, priority: str) -> bool:
        if priority not in ["Auto", "Highest", "High", "Normal", "Low", "NormalForce", "LowForce", "HighIfSingle"]:
            return False
        self._game_info["CreatePriority"] = priority
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        rsdb_mgr.gameactorinfo._is_changed = True
        return True
    
    def set_use_common_name(self, use: bool) -> None:
        attachment_component: AttachmentComponent = self.get_or_add_component("AttachmentRef")
        attachment_component.use_common_name = use

    def set_common_name(self, name: str) -> None:
        attachment_component: AttachmentComponent = self.get_or_add_component("AttachmentRef")
        attachment_component.common_name = name

    def set_attach_dmg(self, dmg: oead.S32) -> None:
        attachment_component: AttachmentComponent = self.get_or_add_component("AttachmentRef")
        attachment_component.damage = dmg
    
    def set_attach_arrow_mult(self, mult: oead.F32) -> None:
        attachment_component: AttachmentComponent = self.get_or_add_component("AttachmentRef")
        attachment_component.arrow_dmg_rate = mult

    def set_attach_shield_dmg(self, dmg: oead.S32) -> None:
        attachment_component: AttachmentComponent = self.get_or_add_component("AttachmentRef")
        attachment_component.shield_base_damage = dmg
    
    def set_attach_subtypes(self, subtypes: List[str]) -> None:
        attachment_component: AttachmentComponent = self.get_or_add_component("AttachmentRef")
        attachment_component.update_subtypes(subtypes)

    def set_next_rank_actor(self, actor: str) -> None:
        armor_component: ArmorComponent = self.get_or_add_component("ArmorRef")
        armor_component.next_rank_actor = actor
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        if self._pouch_info is None:
            self._pouch_info = rsdb_mgr.pouchactorinfo.add_row_by_id(self._name)
        self._pouch_info["ArmorNextRankActor"] = actor
        rsdb_mgr.pouchactorinfo._is_changed = True
    
    def set_armor_series_name(self, name: str) -> None:
        armor_component: ArmorComponent = self.get_or_add_component("ArmorRef")
        armor_component.series_name = name
    
    def set_armor_defense(self, defense: oead.S32) -> None:
        armor_component: ArmorComponent = self.get_or_add_component("ArmorRef")
        armor_component.defense = defense
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        if self._pouch_info is None:
            self._pouch_info = rsdb_mgr.pouchactorinfo.add_row_by_id(self._name)
        self._pouch_info["EquipmentPerformance"] = defense
        rsdb_mgr.pouchactorinfo._is_changed = True

    def set_armor_rank(self, rank: oead.S32) -> None:
        armor_component: ArmorComponent = self.get_or_add_component("ArmorRef")
        armor_component.rank = rank
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        if self._pouch_info is None:
            self._pouch_info = rsdb_mgr.pouchactorinfo.add_row_by_id(self._name)
        self._pouch_info["ArmorRank"] = rank
        rsdb_mgr.pouchactorinfo._is_changed = True
    
    def set_upgrade_price(self, price: oead.S32) -> None:
        armor_component: ArmorComponent = self.get_or_add_component("ArmorRef")
        armor_component.upgrade_price = price
        gp_tbl_component: GameParameterTable = self.get_or_add_component("GameParameterTableRef")
        enhance_info: oead.byml.Dictionary
        sys: ResourceSystem = ResourceSystem.get()
        if (path := gp_tbl_component._param["Component"]["EnhancementMaterial"]) != "":
            enhance_info = TypedParam(oead.byml.from_binary(sys.load_file(path)), "game__pouchcontent__EnhancementMaterial").data
        else:
            enhance_info = copy_dict(TypedParam.load_default("game__pouchcontent__EnhancementMaterial"))
        enhance_info["Price"] = price
        gp_tbl_component._param["Components"]["EnhancementMaterial"] = f"?GameParameter/EnhancementMaterial/{self._name}.game__pouchcontent__EnhancementMaterial.bgyml"
        gp_tbl_component._needs_save = True
        sys.save_archive_file(f"GameParameter/EnhancementMaterial/{self._name}.game__pouchcontent__EnhancementMaterial.bgyml",
                                oead.byml.to_binary(enhance_info, False, 7), ResourceSystem.ARCHIVE_CURRENT)
    
    def add_armor_effect(self, effect: str, level: oead.S32 = 1) -> None:
        armor_component: ArmorComponent = self.get_or_add_component("ArmorRef")
        armor_component.add_effect(effect, level)

    def set_primary_armor_effect(self, effect: str) -> None:
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        if self._pouch_info is None:
            self._pouch_info = rsdb_mgr.pouchactorinfo.add_row_by_id(self._name)
        self._pouch_info["ArmorEffectType"] = effect
        rsdb_mgr.pouchactorinfo._is_changed = True

    def add_armor_hide_group(self, group_name: str, materials: List[str]) -> None:
        armor_component: ArmorComponent = self.get_or_add_component("ArmorRef")
        armor_component.add_hide_group(group_name, materials)

    # didn't realize there was an EnhancementMaterial component...
    # too lazy to change how this works though so have this
    def add_armor_upgrade_material(self, material: str, count: oead.S32) -> None:
        armor_component: ArmorComponent = self.get_or_add_component("ArmorRef")
        armor_component.add_upgrade_material(material, count)
        gp_tbl_component: GameParameterTable = self.get_or_add_component("GameParameterTableRef")
        enhance_info: oead.byml.Dictionary
        sys: ResourceSystem = ResourceSystem.get()
        if (path := gp_tbl_component._param["Component"]["EnhancementMaterial"]) != "":
            enhance_info = TypedParam(oead.byml.from_binary(sys.load_file(path)), "game__pouchcontent__EnhancementMaterial").data
        else:
            enhance_info = copy_dict(TypedParam.load_default("game__pouchcontent__EnhancementMaterial"))
        enhance_info["Items"].append(to_dict({"Actor" : material, "Number" : count}))
        gp_tbl_component._param["Components"]["EnhancementMaterial"] = f"?GameParameter/EnhancementMaterial/{self._name}.game__pouchcontent__EnhancementMaterial.bgyml"
        gp_tbl_component._needs_save = True
        sys.save_archive_file(f"GameParameter/EnhancementMaterial/{self._name}.game__pouchcontent__EnhancementMaterial.bgyml",
                                oead.byml.to_binary(enhance_info, False, 7), ResourceSystem.ARCHIVE_CURRENT)

    def add_shield_hide_group(self, group_name: str, materials: List[str]) -> None:
        shield_component: ShieldComponent = self.get_or_add_component("ShieldRef")
        shield_component.add_hide_group(group_name, materials)

    def add_weapon_hide_group(self, group_name: str, materials: List[str]) -> None:
        weapon_component: WeaponComponent = self.get_or_add_component("WeaponRef")
        weapon_component.add_hide_group(group_name, materials)
    
    def add_bow_hide_group(self, group_name: str, materials: List[str]) -> None:
        bow_component: BowComponent = self.get_or_add_component("BowRef")
        bow_component.add_hide_group(group_name, materials)

    def set_bow_dmg(self, dmg: oead.S32) -> None:
        bow_component: BowComponent = self.get_or_add_component("BowRef")
        bow_component.damage = dmg
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        if self._pouch_info is None:
            self._pouch_info = rsdb_mgr.pouchactorinfo.add_row_by_id(self._name)
        self._pouch_info["EquipmentPerformance"] = dmg
        rsdb_mgr.pouchactorinfo._is_changed = True
    
    def set_shield_dmg(self, dmg: oead.S32) -> None:
        shield_component: ShieldComponent = self.get_or_add_component("ShieldRef")
        shield_component.damage = dmg

    def set_shield_guard(self, guard: oead.S32) -> None:
        shield_component: ShieldComponent = self.get_or_add_component("ShieldRef")
        shield_component.guard_power = guard

    def set_shield_subtypes(self, subtypes: List[str]) -> None:
        shield_component: ShieldComponent = self.get_or_add_component("ShieldRef")
        shield_component.update_subtypes(subtypes)
    
    def set_weapon_dmg(self, dmg: oead.S32) -> None:
        weapon_component: WeaponComponent = self.get_or_add_component("WeaponRef")
        weapon_component.damage = dmg
        rsdb_mgr: RSDBMgr = RSDBMgr.get()
        if self._pouch_info is None:
            self._pouch_info = rsdb_mgr.pouchactorinfo.add_row_by_id(self._name)
        if weapon_component.weapon_type == "SmallSword":
            self._pouch_info["EquipmentPerformance"] = dmg
        elif weapon_component.weapon_type == "Spear":
            self._pouch_info["EquipmentPerformance"] = oead.S32(int(ceil(int(dmg) * 1.326856)))
        else:
            self._pouch_info["EquipmentPerformance"] = oead.S32(int(floor(int(dmg) * 0.95)))
        rsdb_mgr.pouchactorinfo._is_changed = True

    def set_weapon_subtypes(self, subtypes: List[str]) -> None:
        weapon_component: WeaponComponent = self.get_or_add_component("WeaponRef")
        weapon_component.update_subtypes(subtypes)

    def set_bow_subtypes(self, subtypes: List[str]) -> None:
        bow_component: BowComponent = self.get_or_add_component("BowRef")
        bow_component.update_subtypes(subtypes)

    def set_weapon_type(self, type: str) -> None:
        weapon_component: WeaponComponent = self.get_or_add_component("WeaponRef")
        weapon_component.weapon_type = type

    def set_pouch_special_deal(self, special_deal: str) -> None:
        pouch_content_component: PouchContentComponent = self.get_or_add_component("PouchContentRef")
        pouch_content_component.special_deal = special_deal

    def set_pouch_category(self, category: str) -> None:
        pouch_content_component: PouchContentComponent = self.get_or_add_component("PouchContentRef")
        pouch_content_component.category = category