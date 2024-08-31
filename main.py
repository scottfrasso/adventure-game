from dotenv import load_dotenv
import instructor
from openai import OpenAI

from src.entities import Scenario, ActionPhase, ProposedAction, ScenarioDescription

load_dotenv()

# Patch the OpenAI client
client = instructor.from_openai(OpenAI())

def generate_scenario() -> Scenario:
    character_generation_prompt = """
    Generate 1 human player character and 1 monster character for a game scenario. 
    Give them traits but not abilities, abilities will be derived from traits.
    """

    # Extract structured data from natural language
    game_scenario = client.chat.completions.create(
        model="gpt-4o-mini",
        response_model=Scenario,
        messages=[
            {
                "role": "system",
                "content": character_generation_prompt,
            }
        ],
    )
    return game_scenario

rules = """
Do not let the player edit the monster's abilities or their own abilities directly.
The player must perform action which will have an effect on the game scenario.
"""

action_rules = """
During the action phase now the player attempts to make an action that will have an effect on the game scenario.
If the target entity is not specified just assume it's one of the possible foes.
"""

def game_roll(scenario: Scenario, player_action: ProposedAction) -> ActionPhase:
  current_state = f"The current state of the game scenario is: {scenario.to_xml()}"
  action_explained = f"""
  My Entity ID is {player_action.source_entity_id}
  I have chosen to: {player_action.player_input}
  """

  is_player_character = any(player_action.source_entity_id == character.entity_id for character in scenario.player_characters)
  game_entity = scenario._find_entity_by_id(player_action.source_entity_id)
  possible_foes = scenario.monsters if is_player_character else scenario.player_characters
  possible_friendlies = [character for character in (scenario.player_characters if is_player_character else scenario.monsters) if character.entity_id != player_action.source_entity_id]
  
  if is_player_character:
    action_explained += "I am a player character.\n"
  else:
    action_explained += "I am a monster"

  action_explained += f"My Possible foes are: {', '.join(foe.name for foe in possible_foes)}"
  action_explained += f"My Possible abilities are: {', '.join(ability.value for ability in game_entity.abilities)}"
  action_explained += f"My Possible friendlies are: {', '.join(friendly.name for friendly in possible_friendlies)}"
  action_explained += f"I chose to: {player_action.player_input}"

  action_phase_result = client.chat.completions.create(
      model="gpt-4o-mini",
      response_model=ActionPhase,
      messages=[
          {
              "role": "system",
              "content": rules,
          },
          {
              "role": "system",
              "content": action_rules,
          },
          { 
              "role": "system",
              "content": current_state,
          },
          {
              "role": "user",
              "content": action_explained,
          }
      ],
  )

  return action_phase_result

def describe_scenario(current_entity_id: int, scenario: Scenario) -> ScenarioDescription:
    current_entity = scenario._find_entity_by_id(current_entity_id)
    current_entity_name = current_entity.name if current_entity else "Unknown Entity"

    current_entity_description = f"""
    Describe the current state of the game scenario for {current_entity_name} in a story format.
    The 'possible_actions' field should contain a list of possible actions that can be taken by 
    the current entity only based on the current entities 'abilities'.
    """
    
    # Extract structured data from natural language
    scenario_description = client.chat.completions.create(
        model="gpt-4o-mini",
        response_model=ScenarioDescription,
        messages=[
            {
                "role": "system",
                "content": f"The current state of the scenario is:\n{scenario.to_xml()}",
            },
            {
                "role": "system",
                "content": current_entity_description,
            }
        ],
    )
    return scenario_description

# Step 5: Implement the Game Loop
def game_loop():
    print("Game started!")
    scenario = generate_scenario()
    scenario.initialize()
    
    while True:
        #print(f"The current state of the game scenario is:\n{scenario.to_xml()}")
        current_entity_id = scenario.turn_order[scenario.current_turn]
        current_entity = scenario._find_entity_by_id(current_entity_id)
        
        print(f"\nIt's {current_entity.name}'s turn!")
        
        if current_entity in scenario.player_characters:
            
            scenario_description = describe_scenario(current_entity_id, scenario)
            print(scenario_description.story)

            possible_actions = scenario_description.possible_actions + ["quit"]

            action_input = input(f"Enter action ({', '.join(possible_actions)}): ").strip().lower()
            if action_input == "quit":
                print("Game over!")
                break

            player_action = ProposedAction(
                player_input=action_input,
                source_entity_id=current_entity_id,
            )
            player_action_phase = game_roll(scenario, player_action)
            print(player_action_phase.to_xml())
            for action in player_action_phase.actions:
              scenario.apply_action(action)

        else:
            # Simple AI or automated actions for monsters
            # TODO: Implement a more sophisticated AI for monsters
            print(f"{current_entity.name} attacks!")
            monster_action = ProposedAction(
                player_input="Attack",
                source_entity_id=current_entity_id,
            )
            monster_action_phase = game_roll(scenario, monster_action)
            for action in monster_action_phase.actions:
              scenario.apply_action(action)

        # Check for win/loss conditions
        if all(monster.health <= 0 for monster in scenario.monsters):
            print("All monsters defeated! You win!")
            break
        elif all(character.health <= 0 for character in scenario.player_characters):
            print("All player characters defeated! Game over!")
            break
        
        scenario.next_turn()

game_loop()
