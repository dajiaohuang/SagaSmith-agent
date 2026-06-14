from __future__ import annotations

import copy

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Campaign, Character, NapCatCharacterBinding
from app.services import uid


def character_qq_user_ids(character: Character) -> list[str]:
    integrations = (character.data or {}).get("integrations") or {}
    return sorted({str(item).strip() for item in integrations.get("qq_user_ids", []) if str(item).strip()})


def _write_character_qq_user_ids(character: Character, qq_user_ids: list[str]) -> None:
    data = copy.deepcopy(character.data or {})
    integrations = copy.deepcopy(data.get("integrations") or {})
    integrations["qq_user_ids"] = sorted(set(qq_user_ids))
    data["integrations"] = integrations
    if data != character.data:
        character.data = data
        character.version += 1


def set_dice_dm_actor_bindings(db: Session, campaign: Campaign, dm_qq_user_id: str | None) -> list[Character]:
    updated = []
    characters = db.scalars(select(Character).where(Character.campaign_id == campaign.id)).all()
    for character in characters:
        actor_type = ((character.data or {}).get("basic") or {}).get("actor_type", "player")
        if actor_type not in {"npc", "monster"}:
            continue
        data = copy.deepcopy(character.data or {})
        integrations = copy.deepcopy(data.get("integrations") or {})
        if dm_qq_user_id:
            integrations["dice_dm_qq_user_id"] = dm_qq_user_id
        else:
            integrations.pop("dice_dm_qq_user_id", None)
        data["integrations"] = integrations
        if data != character.data:
            character.data = data
            character.version += 1
            updated.append(character)
    db.commit()
    return updated


def find_binding(db: Session, campaign_id: str, qq_user_id: str) -> NapCatCharacterBinding | None:
    return db.scalar(select(NapCatCharacterBinding).where(
        NapCatCharacterBinding.campaign_id == campaign_id,
        NapCatCharacterBinding.qq_user_id == qq_user_id.strip(),
    ))


def bind_qq(
    db: Session,
    campaign_id: str,
    qq_user_id: str,
    character: Character,
    display_name: str = "",
    note: str = "",
) -> NapCatCharacterBinding:
    qq_user_id = qq_user_id.strip()
    if not qq_user_id.isdigit():
        raise ValueError("QQ user ID must contain digits only")
    if character.campaign_id != campaign_id:
        raise ValueError("Character does not belong to the requested campaign")
    binding = find_binding(db, campaign_id, qq_user_id)
    if binding and binding.character_id != character.id:
        previous = db.get(Character, binding.character_id)
        if previous:
            _write_character_qq_user_ids(previous, [
                item for item in character_qq_user_ids(previous) if item != qq_user_id
            ])
    if not binding:
        binding = NapCatCharacterBinding(
            id=uid("napcat_binding"), campaign_id=campaign_id,
            qq_user_id=qq_user_id, character_id=character.id,
        )
        db.add(binding)
    binding.character_id = character.id
    binding.display_name = display_name.strip() or None
    binding.note = note.strip() or None
    _write_character_qq_user_ids(character, [*character_qq_user_ids(character), qq_user_id])
    db.commit()
    return binding


def unbind_qq(db: Session, campaign_id: str, qq_user_id: str) -> NapCatCharacterBinding | None:
    binding = find_binding(db, campaign_id, qq_user_id)
    if not binding:
        return None
    character = db.get(Character, binding.character_id)
    if character:
        _write_character_qq_user_ids(character, [
            item for item in character_qq_user_ids(character) if item != binding.qq_user_id
        ])
    db.delete(binding)
    db.commit()
    return binding


def sync_character_bindings(db: Session, character: Character, qq_user_ids: list[str]) -> list[NapCatCharacterBinding]:
    desired = sorted({str(item).strip() for item in qq_user_ids if str(item).strip()})
    if any(not item.isdigit() for item in desired):
        raise ValueError("QQ user ID must contain digits only")
    current = db.scalars(select(NapCatCharacterBinding).where(
        NapCatCharacterBinding.campaign_id == character.campaign_id,
        NapCatCharacterBinding.character_id == character.id,
    )).all()
    for binding in current:
        if binding.qq_user_id not in desired:
            db.delete(binding)
    db.commit()
    for qq_user_id in desired:
        bind_qq(db, character.campaign_id, qq_user_id, character)
    _write_character_qq_user_ids(character, desired)
    db.commit()
    return db.scalars(select(NapCatCharacterBinding).where(
        NapCatCharacterBinding.campaign_id == character.campaign_id,
        NapCatCharacterBinding.character_id == character.id,
    )).all()


def delete_character_and_bindings(db: Session, character: Character) -> None:
    bindings = db.scalars(select(NapCatCharacterBinding).where(
        NapCatCharacterBinding.character_id == character.id,
    )).all()
    for binding in bindings:
        db.delete(binding)
    db.delete(character)
    db.commit()


def backfill_character_binding_mirrors(db: Session) -> None:
    characters = db.scalars(select(Character)).all()
    bindings = db.scalars(select(NapCatCharacterBinding)).all()
    by_character: dict[str, list[str]] = {}
    for binding in bindings:
        by_character.setdefault(binding.character_id, []).append(binding.qq_user_id)
    for character in characters:
        _write_character_qq_user_ids(character, by_character.get(character.id, []))
    db.commit()


def active_napcat_campaign(db: Session) -> Campaign | None:
    campaigns = db.scalars(select(Campaign).order_by(Campaign.updated_at.desc())).all()
    return next((item for item in campaigns if (item.config or {}).get("napcat_active")), None)


def active_napcat_campaign_id(db: Session, fallback: str) -> str:
    campaign = active_napcat_campaign(db)
    return campaign.id if campaign else fallback


def set_active_napcat_campaign(db: Session, campaign: Campaign) -> Campaign:
    for item in db.scalars(select(Campaign)).all():
        config = copy.deepcopy(item.config or {})
        active = item.id == campaign.id
        if bool(config.get("napcat_active")) != active:
            if active:
                config["napcat_active"] = True
            else:
                config.pop("napcat_active", None)
            item.config = config
    db.commit()
    return campaign
