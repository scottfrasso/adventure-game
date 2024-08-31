from dotenv import load_dotenv
import instructor
from openai import OpenAI
from rich import print

from src.entities import Scenario, ActionPhase, ProposedAction, ScenarioDescription

load_dotenv()

# Patch the OpenAI client
client = instructor.from_openai(OpenAI())
MODEL = "gpt-4o"

def generate_scenario() -> Scenario:
    character_generation_prompt = """
    Generate 1 human player character and 1 monster character for a game scenario. 
    Give them traits but not abilities, abilities will be derived from traits.
    """

    # Extract structured data from natural language
    game_scenario = client.chat.completions.create(
        model=MODEL,
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
      model=MODEL,
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

def describe_effectiveness_of_action(scenario: Scenario, action: ActionPhase) -> str:
    action_description = f"""
    Describe the effectiveness of the last action taken by the player character.
    The 'action' field should contain the action taken by the player character.
    The 'scenario' field should contain the current state of the game scenario.
    """

    # Extract structured data from natural language
    action_effectiveness = client.chat.completions.create(
        model=MODEL,
        response_model=str,
        messages=[
            {
                "role": "system",
                "content": action_description,
            },
            {
                "role": "system",
                "content": f"The current state of the scenario is:\n{scenario.to_xml()}",
            },
            {
                "role": "system",
                "content": f"The action taken by the player character is: {action.to_xml()}",
            }
        ],
    )
    return action_effectiveness

def describe_scenario(current_entity_id: int, scenario: Scenario, be_brief=True) -> ScenarioDescription:
    current_entity = scenario._find_entity_by_id(current_entity_id)
    current_entity_name = current_entity.name if current_entity else "Unknown Entity"

    is_monster_entity = any(current_entity_id == monster.entity_id for monster in scenario.monsters)

    player_character_description = f"""
    Describe the current state of the game scenario for {current_entity_name} in a story format.
    Make sure to include history of the actions taken so far, especially describing the most previous actions.
    The 'possible_actions' field should contain a list of possible actions that can be taken by 
    the current entity only based on the current entities 'abilities'.
    Make sure to describe the current foes and friendlies of the entity.
    """

    monster_description = f"""
    Describe the current state of the game scenario in past tense explaining what {current_entity_name} just did.
    Make sure to include history of the actions taken so far, especially describing the most previous actions.
    Make sure to describe the current foes and friendlies of the entity.
    """

    messages=[
        {
            "role": "system",
            "content": f"The current state of the scenario is:\n{scenario.to_xml()}",
        },
        {
            "role": "system",
            "content": player_character_description if not is_monster_entity else monster_description,
        }
    ]
    if be_brief or is_monster_entity:
        messages.append(
            {
                "role": "system",
                "content": "Be as brief as possible. You do not need to describe the entire setting again as it has already been explained previously.",
            }
        )

    if is_monster_entity:
        last_action = scenario.action_history[-1] if scenario.action_history else "No actions taken yet."
        messages.append(
            {
                "role": "system",
                "content": f"Focus on describing last action taken by the monster and its effects on the game: `{last_action}`.\n",
            }
        )
    
    # Extract structured data from natural language
    scenario_description = client.chat.completions.create(
        model=MODEL,
        response_model=ScenarioDescription,
        messages=messages,
    )
    return scenario_description

def answer_question(scenario: Scenario, question: str) -> str:
    question_prompt = f"""
    Answer the following question based on the current game scenario:
    {question}
    """

    # Extract structured data from natural language
    answer = client.chat.completions.create(
        model="gpt-4o-mini",
        response_model=str,
        messages=[
            {
               "role": "system",
                "content": f"The current state of the scenario is:\n{scenario.to_xml()}",
            },
            {
                "role": "system",
                "content": question_prompt,
            }
        ],
    )
    return answer

# Step 5: Implement the Game Loop
def game_loop():
    print("[bold red]Game started![/bold red]")
    scenario = generate_scenario()
    scenario.initialize()

    turn_number = 0    
    while True:
        current_entity_id = scenario.turn_order[scenario.current_turn]
        current_entity = scenario._find_entity_by_id(current_entity_id)
        
        print(f"🎲 It's {current_entity.name}'s turn!")
        
        if current_entity in scenario.player_characters:
            scenario_description = describe_scenario(current_entity_id, scenario, be_brief=turn_number == 0)
            print(f"{scenario_description.story}\n")
            while True:
              action_input = input("What would you like to do? ")
              if action_input == "quit":
                  print("[bold red]Game over![/bold red]")
                  break

              player_action = ProposedAction(
                  player_input=action_input,
                  source_entity_id=current_entity_id,
              )
              # Figure out what the player wants to do
              player_action_phase = game_roll(scenario, player_action)
              #print(f"[blue]{player_action_phase.to_xml()}[/blue]\n\n")

              if player_action_phase.is_question and player_action_phase.question_for_ai:
                  question = player_action_phase.question_for_ai
                  answer = answer_question(scenario, question)
                  print(f"[green]{answer}[/green]\n\n")
                  continue

              for action in player_action_phase.actions:
                scenario.apply_action(action)

              action_effectiveness = describe_effectiveness_of_action(scenario, player_action_phase)
              print(f"[green]{action_effectiveness}[/green]\n\n")
              break

        else:
            # Simple AI or automated actions for monsters
            # TODO: Implement a more sophisticated AI for monsters
            monster_action = ProposedAction(
                player_input="Attack",
                source_entity_id=current_entity_id,
            )
            monster_action_phase = game_roll(scenario, monster_action)
            for action in monster_action_phase.actions:
              scenario.apply_action(action)

            monsters_scenario_description = describe_scenario(current_entity_id, scenario)
            print(f"[red]{monsters_scenario_description.story}[/red]\n\n")

        # Check for win/loss conditions
        if all(monster.health <= 0 for monster in scenario.monsters):
            print("All monsters defeated! You win!")
            break
        elif all(character.health <= 0 for character in scenario.player_characters):
            print("All player characters defeated! Game over!")
            break
        
        turn_number += 1
        scenario.next_turn()

game_loop()
