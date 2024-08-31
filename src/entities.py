import random
from pydantic import Field
from typing import List
from enum import Enum

from src.utils import BaseModelWithXML

class Trait(Enum):
    AGGRESSIVE = "Aggressive"
    STEALTHY = "Stealthy"
    MAGICAL = "Magical"
    BRAVE = "Brave"
    CUNNING = "Cunning"
    FLYING = "Flying"
    FIRE_BREATHING = "Fire-breathing"

class Ability(Enum):
    ATTACK = "Attack"
    DEFEND = "Defend"
    HEAL = "Heal"
    CAST_SPELL = "Cast Spell"
    SNEAK = "Sneak"
    FLY = "Fly"
    BERSERK = "Berserk"
    BREATH_FIRE = "Breath Fire"

class ActionType(Enum):
    ATTACK = "attack"
    HEAL = "heal"
    DEFEND = "defend"
    MOVE = "move"

class ProposedAction(BaseModelWithXML):
    player_input: str
    source_entity_id: int

class ActionKind(Enum):
    STRENGTH = "Strength"
    DEXTERITY = "Dexterity"
    INTELLIGENCE = "Intelligence"

class Action(BaseModelWithXML):
    type: ActionType = Field(..., description="The type of action to perform")
    ability: Ability | None = Field(None, description="The ability to use for the action. It must be one of the source entity's abilities.")
    source_entity_id: int = Field(..., description="The ID of the entity performing the action")
    target_entity_id: int = Field(..., description="The ID of the target entity for the action")

    action_kind: ActionKind = Field(ActionKind.STRENGTH, description="The kind of action to perform, e.g., strength, dexterity, intelligence")

    description: str = Field("", description="Detailed description of the action taken in past tense for the game history.")

class ActionPhase(BaseModelWithXML):
    actions: List[Action] = Field(..., description="The list of actions to perform in the game scenario")
    is_question: bool = Field(False, description="Indicates if the player asked a question and the AI should respond accordingly and not process an action.")
    question_for_ai: str | None = Field(None, description="""
                                        The question asked by the player for the AI to respond to. 
                                        This is only set if is_question is True and there was no action requested by the player.
                                        """)

TRAIT_BASED_ABILITIES = {
    Trait.AGGRESSIVE: [Ability.BERSERK],
    Trait.STEALTHY: [Ability.SNEAK],
    Trait.MAGICAL: [Ability.CAST_SPELL],
    Trait.FLYING: [Ability.FLY],
    Trait.FIRE_BREATHING: [Ability.BREATH_FIRE],
}

class GameEntity(BaseModelWithXML):
    entity_id: int = Field(..., description="The unique identifier of the character or monster")
    name: str = Field(..., description="The name of the character or monster")
    health: int = Field(
        100, ge=0, le=100, description="The health points of the character or monster"
    )
    strength: int = Field(
        10, ge=0, le=20, description="The strength attribute, affecting physical attacks."
    )
    dexterity: int = Field(
        10, ge=0, le=20, description="The dexterity attribute, affecting agility and defense."
    )
    intelligence: int = Field(
        10, ge=0, le=20, description="The intelligence attribute, affecting magic and strategy"
    )
    traits: List[Trait] = Field(
        default_factory=list,
        description="Special traits or abilities of the character or monster",
    )
    abilities: List[Ability] = Field(
        default_factory=list,
        description="Actions that the character or monster can take, these are derived from traits",
    )

    defensive_bonus: int = Field(
        0, ge=0, le=10, description="The bonus to defense when defending."
    )

    def generate_abilities(self):
        # Add general abilities
        self.abilities.extend([Ability.ATTACK, Ability.DEFEND])

        # Add trait-based abilities
        for trait in self.traits:
            self.abilities.extend(TRAIT_BASED_ABILITIES.get(trait, []))


class ScenarioDescription(BaseModelWithXML):
    story: str = Field(..., description="The detailed description of the current games scenario.")
    possible_actions: List[str] = Field(
        ..., description="The list of possible actions that can be taken in the current scenario. By the current entity."
    )

class Scenario(BaseModelWithXML):
    location_and_story_description: str = Field(
        ..., description="""
        Write a story like description of the current scenario and location that we can use to describe
        the current state of the game to the user.
        """
    )
    player_characters: List[GameEntity] = Field(
        ..., description="The list of player characters in the scenario"
    )
    monsters: List[GameEntity] = Field(
        ..., description="The list of monsters in the scenario"
    )
    turn_order: List[int] = Field(
        default_factory=list, description="The order of turns by entity IDs."
    )
    current_turn: int = Field(0, description="The index of the current turn in the turn order.")

    action_history: List[str] = Field(
        default_factory=list, description="The list of actions taken in the scenario. Do not set this field directly."
    )

    def initialize(self):
        self.set_turn_order()
        self.generate_abilities()
        self.action_history = []

    def set_turn_order(self):
        self.turn_order = [entity.entity_id for entity in self.player_characters + self.monsters]
        self.current_turn = 0

    def generate_abilities(self):
        for character in self.player_characters:
            character.generate_abilities()

        for monster in self.monsters:
            monster.generate_abilities()

    def apply_action(self, action: Action):
        # Find the target entity
        source = self._find_entity_by_id(action.source_entity_id)
        target = self._find_entity_by_id(action.target_entity_id)
        if not target:
            print(f"No entity found with ID {action.target_entity_id}")
            return
        
        if not source:
            print(f"No entity found with ID {action.source_entity_id}")
            return
        
        attack_modifier = 10  # Default attack modifier
        if action.action_kind == ActionKind.STRENGTH:
            attack_modifier = source.strength
        elif action.action_kind == ActionKind.DEXTERITY:
            attack_modifier = source.dexterity
        elif action.action_kind == ActionKind.INTELLIGENCE:
            attack_modifier = source.intelligence

        amount = round((attack_modifier/10) * random.randint(1, 20))  # Roll a 6-sided die for damage calculation
        amount = max(0, min(amount, 20))  # Ensure amount is within the range of 0 to 20

        # Perform the action based on the action type
        if action.type == ActionType.ATTACK:
            message = self._apply_attack(source, target, amount, action.description)
        elif action.type == ActionType.HEAL:
            message = self._apply_heal(source, target, amount, action.description)
        elif action.type == ActionType.DEFEND:
            message = self._apply_defend(source, target, amount, action.description)
        elif action.type == ActionType.MOVE:
            message = self._apply_move(source, target, amount, action.description)
        else:
            print(f"Unknown action type: {action.type}")
        
        if not message:
            return

        self.action_history.append(message)

    def _find_entity_by_id(self, entity_id: int | None) -> GameEntity | None:
        if entity_id is None:
            return None
        for entity in self.player_characters + self.monsters:
            if entity.entity_id == entity_id:
                return entity
        return None

    def _apply_attack(self, source: GameEntity, target: GameEntity, amount: int, description: str):
        target.health -= amount
        return f"{source.name} attacks {target.name} for {amount} damage. New health: {target.health}. Description: {description}"

    def _apply_heal(self, source: GameEntity, target: GameEntity, amount: int, description: str):
        target.health += amount
        return f"{source.name} heals {target.name} for {amount} health. New health: {target.health}. Description: {description}"

    def _apply_defend(self, source: GameEntity, target: GameEntity, amount: int, description: str):
        source.defensive_bonus += amount
        return f"{source.name} gained a defensive bonus against {target.name} of {amount}. Description: {description}"

    def _apply_move(self, source: GameEntity, target: GameEntity, amount: int, description: str):
        # TODO: Implement move logic, e.g., changing position or location in the game scenario
        return f"{target.name} moves to a new position in the amount of {amount}. Description: {description}"

    def next_turn(self):
        self.current_turn = (self.current_turn + 1) % len(self.turn_order)
