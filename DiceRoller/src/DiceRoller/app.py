import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, BOLD
import random
import re
import json
from pathlib import Path

class DiceRollerApp(toga.App):

    def startup(self):
        # --- State Management ---
        self.roll_history = []
        self.last_roll_expression = ""
        self.favorites = []
        self.active_panel = None
        self.expression_to_name = ""
        self.favorites_file_path = self.paths.data / 'favorites.json'
        self._load_favorites()

        # --- Main container ---
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        self.input_display = toga.TextInput(
            style=Pack(font_size=18, text_align='right', padding_bottom=10)
        )
        self.input_display.focus()

        # --- Panels (not yet visible) ---
        self._create_history_panel()
        self._create_favorites_panel()
        self._create_name_favorite_panel()

        # --- Main Button Layout ---
        button_rows = [toga.Box(style=Pack(direction=ROW)) for _ in range(4)]
        buttons_config = {
            0: ['7', '8', '9', 'Bksp'],
            1: ['4', '5', '6', ''],
            2: ['1', '2', '3', 'd'],
            3: ['C', '0', '-', '+']
        }
        for idx, box in enumerate(button_rows):
            for text in buttons_config[idx]:
                if text == '':
                    # Add an empty flexible space to preserve layout
                    spacer = toga.Box(style=Pack(flex=1, padding=2))
                    box.add(spacer)
                else:
                    style = Pack(flex=1, padding=2)
                    if text in ['C', 'Bksp']:
                        style.font_weight = BOLD
                    button = toga.Button(text, on_press=self.handle_button_press, style=style)
                    box.add(button)

        control_row = toga.Box(style=Pack(direction=ROW, padding_top=5))
        for text in ['History', 'Favorites']:
            button = toga.Button(
                text, on_press=self.handle_panel_toggle,
                style=Pack(flex=1, padding=2, font_weight=BOLD)
            )
            control_row.add(button)

        roll_button_row = toga.Box(style=Pack(direction=ROW, padding_top=5))
        roll_button = toga.Button(
            'Roll', on_press=self.handle_button_press,
            style=Pack(flex=1, padding=2, font_weight=BOLD, height=45)
        )
        roll_button_row.add(roll_button)

        # --- Collapsible Panel Container ---
        self.collapsible_panel = toga.Box(style=Pack(direction=COLUMN, padding_top=5))
        self.collapsible_panel.style.visibility = 'hidden'

        # --- Output display ---
        self.output_display = toga.MultilineTextInput(
            readonly=True,
            style=Pack(flex=1, font_size=14, padding_top=10)
        )

        # --- Add all components to the main container ---
        main_box.add(self.input_display)
        for row in button_rows:
            main_box.add(row)
        main_box.add(control_row)
        main_box.add(roll_button_row)
        main_box.add(self.collapsible_panel)
        main_box.add(self.output_display)

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

    def _create_history_panel(self):
        self.history_panel = toga.Box(style=Pack(direction=COLUMN))
        self.history_table = toga.Table(
            headings=['Expression', 'Total'],
            accessors=['expression', 'total'],
            on_select=self.handle_history_select,
            style=Pack(flex=1, height=150)
        )
        clear_history_button = toga.Button("Clear History", on_press=self.handle_clear_history, style=Pack(padding_top=5))
        self.history_panel.add(self.history_table)
        self.history_panel.add(clear_history_button)

    def _create_favorites_panel(self):
        self.favorites_panel = toga.Box(style=Pack(direction=COLUMN))
        self.favorites_table = toga.Table(
            headings=['Name', 'Roll'],
            accessors=['name', 'expression'],
            on_select=self.handle_favorite_select,
            style=Pack(flex=1, height=150)
        )
        fav_button_box = toga.Box(style=Pack(direction=ROW, padding_top=5))
        add_fav_button = toga.Button("Add Current as Favorite", on_press=self.show_name_favorite_panel, style=Pack(flex=1))
        remove_fav_button = toga.Button("Remove Selected", on_press=self.handle_remove_favorite, style=Pack(flex=1))
        fav_button_box.add(add_fav_button)
        fav_button_box.add(remove_fav_button)
        self.favorites_panel.add(self.favorites_table)
        self.favorites_panel.add(fav_button_box)

    def _create_name_favorite_panel(self):
        self.name_favorite_panel = toga.Box(style=Pack(direction=COLUMN))
        self.favorite_name_input = toga.TextInput(placeholder="Enter a name")
        button_box = toga.Box(style=Pack(direction=ROW, padding_top=10))
        save_button = toga.Button("Save", on_press=self.handle_save_named_favorite, style=Pack(flex=1))
        cancel_button = toga.Button("Cancel", on_press=self.handle_cancel_naming, style=Pack(flex=1))
        button_box.add(save_button)
        button_box.add(cancel_button)
        self.name_favorite_panel.add(toga.Label("Enter a name for this roll:"))
        self.name_favorite_panel.add(self.favorite_name_input)
        self.name_favorite_panel.add(button_box)

    # --- Persistence ---
    def _load_favorites(self):
        try:
            if self.favorites_file_path.exists():
                with self.favorites_file_path.open('r') as f:
                    data = json.load(f)
                    if data and isinstance(data[0], str):
                        self.favorites = [{'name': fav, 'expression': fav} for fav in data]
                        self._save_favorites()
                    else:
                        self.favorites = data
        except Exception:
            self.favorites = []

    def _save_favorites(self):
        try:
            self.paths.data.mkdir(parents=True, exist_ok=True)
            with self.favorites_file_path.open('w') as f:
                json.dump(self.favorites, f, indent=4)
        except Exception as e:
            print(f"Could not save favorites: {e}")

    # --- UI and State Handlers ---
    def handle_panel_toggle(self, widget):
        panel_map = {'History': self.history_panel, 'Favorites': self.favorites_panel}
        target_panel = panel_map.get(widget.text)
        for child in list(self.collapsible_panel.children):
            self.collapsible_panel.remove(child)
        if self.active_panel is target_panel:
            self.collapsible_panel.style.visibility = 'hidden'
            self.active_panel = None
        else:
            if widget.text == 'History':
                self.history_table.data = self.roll_history
            elif widget.text == 'Favorites':
                self.favorites_table.data = self.favorites
            self.collapsible_panel.add(target_panel)
            self.collapsible_panel.style.visibility = 'visible'
            self.active_panel = target_panel

    def handle_history_select(self, widget):
        if widget.selection:
            self.input_display.value = widget.selection.expression
        self.input_display.focus()

    def handle_favorite_select(self, widget):
        if widget.selection:
            self.input_display.value = widget.selection.expression
        self.input_display.focus()

    def handle_clear_history(self, widget):
        self.roll_history.clear()
        self.last_roll_expression = ""
        self.history_table.data = []
        self.output_display.value = "History has been cleared."
        self.input_display.focus()

    def show_name_favorite_panel(self, widget):
        expression = self.input_display.value.strip()
        if not expression:
            self.output_display.value = "Cannot save an empty favorite."
            return
        self.expression_to_name = expression
        self.favorite_name_input.value = ""
        for child in list(self.collapsible_panel.children):
            self.collapsible_panel.remove(child)
        self.collapsible_panel.add(self.name_favorite_panel)
        self.collapsible_panel.style.visibility = 'visible'
        self.active_panel = self.name_favorite_panel
        self.favorite_name_input.focus()

    def handle_save_named_favorite(self, widget):
        name = self.favorite_name_input.value.strip()
        if not name:
            self.output_display.value = "Favorite name cannot be empty."
            return
        if any(fav['name'].lower() == name.lower() for fav in self.favorites):
            self.output_display.value = f'A favorite named "{name}" already exists.'
            return
        new_favorite = {'name': name, 'expression': self.expression_to_name}
        self.favorites.append(new_favorite)
        self.favorites.sort(key=lambda x: x['name'].lower())
        self._save_favorites()
        self.output_display.value = f'Saved "{name}" to favorites.'
        # Switch back to the favorites panel
        dummy_favorites_button = toga.Button(text='Favorites')
        self.handle_panel_toggle(dummy_favorites_button)

    def handle_cancel_naming(self, widget):
        dummy_favorites_button = toga.Button(text='Favorites')
        self.handle_panel_toggle(dummy_favorites_button)

    def handle_remove_favorite(self, widget):
        if self.favorites_table.selection is None:
            self.output_display.value = "Select a favorite to remove first."
            return
        selection_name = self.favorites_table.selection.name
        self.favorites = [fav for fav in self.favorites if fav['name'] != selection_name]
        self._save_favorites()
        self.favorites_table.data = self.favorites
        self.output_display.value = f'Removed "{selection_name}" from favorites.'
        self.input_display.focus()

    def handle_button_press(self, widget):
        button_text = widget.text
        if button_text == 'C':
            self.input_display.value = ''
            self.output_display.value = ''
        elif button_text == 'Bksp':
            self.input_display.value = self.input_display.value[:-1]
        elif button_text == 'Roll':
            self.perform_roll_logic()
        else:
            self.input_display.value += button_text
        self.input_display.focus()

    # --- Core Logic ---
    def perform_roll_logic(self):
        expression = self.input_display.value.strip()
        self.output_display.value = ""
        if not expression:
            self.output_display.value = "Please enter a dice expression."
            return
        self.last_roll_expression = expression
        self.output_display.value = f"Rolling: {expression}\n"
        term_finder = re.compile(r'([+-])?\s*(\d*d\d+|\d+)')
        expression_to_parse = expression.lower().replace(" ", "")
        if not expression_to_parse.startswith(('+', '-')):
            expression_to_parse = '+' + expression_to_parse
        matches = term_finder.finditer(expression_to_parse)
        grand_total = 0
        try:
            full_breakdown_str = ""
            for i, match in enumerate(matches):
                sign_str, term_str = match.groups()
                sign = -1 if sign_str == '-' else 1
                term_sum, details_str = 0, ""
                if 'd' in term_str:
                    dice_pattern = re.compile(r"(\d*)d(\d+)")
                    dice_match = dice_pattern.fullmatch(term_str)
                    if not dice_match:
                        raise ValueError("Invalid dice term")
                    num_dice_str, sides_str = dice_match.groups()
                    num_dice = int(num_dice_str) if num_dice_str else 1
                    sides = int(sides_str)
                    if not (0 < num_dice <= 1000000000000 and 0 < sides <= 1000000000000):
                        raise ValueError("Dice count/sides out of range")
                    rolls = [random.randint(1, sides) for _ in range(num_dice)]
                    term_sum = sum(rolls)
                    details_str = f"{num_dice}d{sides} ({', '.join(map(str, rolls))}) = {term_sum}"
                else:
                    term_sum = int(term_str)
                    details_str = str(term_sum)
                grand_total += term_sum * sign
                if i > 0:
                    full_breakdown_str += f" {'-' if sign < 0 else '+'} "
                elif sign < 0:
                    full_breakdown_str += "- "
                full_breakdown_str += details_str
            new_history_entry = {'expression': expression, 'total': grand_total}
            if not self.roll_history or self.roll_history[0]['expression'] != expression:
                self.roll_history.insert(0, new_history_entry)
                self.roll_history = self.roll_history[:20]
                if self.active_panel is self.history_panel:
                    self.history_table.data = self.roll_history
            grand_total_string = f"Grand Total: {grand_total}"
            breakdown_header = "Breakdown:"
            self.output_display.value += f"{grand_total_string}\n\n{breakdown_header}\n{full_breakdown_str}"
        except (ValueError, TypeError) as e:
            self.output_display.value += f"\nError: Could not parse expression. ({e})"
        except Exception as e:
            self.output_display.value += f"\nAn unexpected error occurred: {e}"

def main():
    return DiceRollerApp('DiceRoller', 'org.example.diceroller')