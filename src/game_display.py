from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Static, Input, Footer
from textual.screen import Screen
from textual import events
from textual.reactive import Reactive
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.entities import GameEntity, Scenario, Trait

# Assuming the classes like Trait, Ability, GameEntity, Scenario, etc., are already defined.

class GameScreen(Screen):
    scenario: Scenario
    story_text: str

    def __init__(self, scenario: Scenario, story_text: str, **kwargs):
        super().__init__(**kwargs)
        self.scenario = scenario
        self.story_text = story_text

    def compose(self) -> ComposeResult:
        # Create widgets and layout
        yield Static(self.story_text, id="story")
        yield Static(self.render_game_state(), id="game_state")
        yield Input(placeholder="Enter action here...", id="action_input")
        yield Footer()

    def render_game_state(self) -> Panel:
        """Create a Rich Panel with the current game state."""
        game_table = Table(title="Current Game State")

        game_table.add_column("Entity Name", justify="center")
        game_table.add_column("Health", justify="center")
        game_table.add_column("Strength", justify="center")
        game_table.add_column("Dexterity", justify="center")
        game_table.add_column("Intelligence", justify="center")
        game_table.add_column("Traits", justify="center")
        game_table.add_column("Abilities", justify="center")

        # Populate the table with player characters
        for entity in self.scenario.player_characters:
            game_table.add_row(
                entity.name,
                str(entity.health),
                str(entity.strength),
                str(entity.dexterity),
                str(entity.intelligence),
                ", ".join(trait.value for trait in entity.traits),
                ", ".join(ability.value for ability in entity.abilities)
            )

        # Populate the table with monsters
        for entity in self.scenario.monsters:
            game_table.add_row(
                entity.name,
                str(entity.health),
                str(entity.strength),
                str(entity.dexterity),
                str(entity.intelligence),
                ", ".join(trait.value for trait in entity.traits),
                ", ".join(ability.value for ability in entity.abilities)
            )

        return Panel(game_table, title="Game Entities", subtitle=f"Turn: {self.scenario.current_turn}")

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        """Handle user input from the Input widget."""
        action_text = message.value.strip()
        if action_text.lower() == "quit":
            await self.app.action_quit()
            return

        # Process the action based on input (You would implement action parsing here)
        print(f"User action: {action_text}")

        # Move to the next turn
        self.scenario.next_turn()

        # Refresh the game state display
        game_state_widget = self.query_one("#game_state", Static)
        game_state_widget.update(self.render_game_state())

class GameDisplayApp(App):
    def __init__(self, scenario: Scenario, story_text: str, **kwargs):
        super().__init__(**kwargs)
        self.scenario = scenario
        self.story_text = story_text

    async def on_mount(self) -> None:
        # Mount the game screen
        await self.push_screen(GameScreen(self.scenario, self.story_text))


# Example Scenario Setup
player1 = GameEntity(entity_id=1, name="Thorn", health=100, strength=15, dexterity=12, intelligence=10, traits=[Trait.BRAVE, Trait.CUNNING], abilities=[])
player1.generate_abilities()

monster1 = GameEntity(entity_id=2, name="Dreadwing", health=80, strength=18, dexterity=8, intelligence=6, traits=[Trait.AGGRESSIVE, Trait.FLYING], abilities=[])
monster1.generate_abilities()

scenario = Scenario(
    player_characters=[player1],
    monsters=[monster1],
    turn_order=[1, 2],
    current_turn=0
)
scenario.initialize()

story_text = """
It's Thorn's turn!
In a dimly lit forest clearing, Thorn stands with the tension of battle hanging in the air. The sweet scent of damp earth surrounds him, but his senses are heightened, focused on the formidable creature before him...
"""

# Run the Textual App
app = GameDisplayApp(scenario=scenario, story_text=story_text)
app.run()
