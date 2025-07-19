import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, BOLD
import random
import re
import json
from pathlib import Path


class DiceRollerApp(toga.App):

    def startup(self):
        """
        Construct and show the Toga-based application with a responsive layout.
        """
        # --- State Management ---
        self.roll_history = []
        self.last_roll_expression = ""
        self.roll_counter = 0
        self.favorites = []
        self.active_panel = None  # Tracks which collapsible panel is open
        self.favorites_file_path = self.paths.data / 'favorites.json'
        self._load_favorites()

        # --- Main container ---
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        self.input_display = toga.TextInput(
            style=Pack(font_size=18, text_align='right', padding_bottom=10)
        )
        self.input_display.focus()

        # --- Create Panel Content (but don't add them to the layout directly) ---
        self._create_advanced_panel()
        self._create_history_panel()
        self._create_favorites_panel()

        # --- Main Button Layout (Condensed) ---
        button_rows = [toga.Box(style=Pack(direction=ROW)) for _ in range(4)]
        buttons_config = {
            button_rows[0]: ['7', '8', '9', 'DEL'],
            button_rows[1]: ['4', '5', '6', 'd'],
            button_rows[2]: ['1', '2', '3', '+'],
            button_rows[3]: ['(', '0', ')', '-']
        }
        for box, texts in buttons_config.items():
            for text in texts:
                style = Pack(flex=1, padding=2)
                if text == 'DEL':
                    style.font_weight = BOLD
                button = toga.Button(text, on_press=self.handle_button_press, style=style)
                box.add(button)

        # --- Control and Action Rows ---
        control_row = toga.Box(style=Pack(direction=ROW, padding_top=5))
        action_row = toga.Box(style=Pack(direction=ROW, padding_top=5))

        control_buttons = ['C', 'Advanced', 'History', 'Favorites']
        for text in control_buttons:
            button = toga.Button(text, on_press=self.handle_panel_toggle,
                                 style=Pack(flex=1, padding=2, font_weight=BOLD))
            control_row.add(button)

        reroll_last_button = toga.Button('Reroll Last', on_press=self.handle_reroll_last,
                                         style=Pack(flex=1, padding=2, font_weight=BOLD))
        roll_button = toga.Button('Roll', on_press=self.handle_button_press,
                                  style=Pack(flex=2, padding=2, font_weight=BOLD, height=45))
        action_row.add(reroll_last_button)
        action_row.add(roll_button)

        # --- Collapsible Panel Container ---
        self.collapsible_panel = toga.Box(style=Pack(direction=COLUMN, padding_top=5))
        self.collapsible_panel.style.visibility = 'hidden'

        # --- Output display (Now flexible) ---
        self.output_display = toga.MultilineTextInput(
            readonly=True,
            style=Pack(flex=1, font_size=14, padding_top=10)  # flex=1 makes it resize
        )

        # --- Add all components to the main container ---
        main_box.add(self.input_display)
        for row in button_rows:
            main_box.add(row)
        main_box.add(control_row)
        main_box.add(action_row)
        main_box.add(self.collapsible_panel)
        main_box.add(self.output_display)

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

    def _create_advanced_panel(self):
        self.advanced_box = toga.Box(style=Pack(direction=COLUMN))
        adv_buttons_data = [
            ('Drop Lowest', 'Drop the lowest # of dice'), ('Drop Highest', 'Drop the highest # of dice'),
            ('Reroll <', 'Reroll dice with values less than #'), ('Reroll >', 'Reroll dice with values greater than #'),
            ('Min Val', 'Set a minimum value for any die'), ('Max Val', 'Set a maximum value for any die')
        ]
        adv_rows = [toga.Box(style=Pack(direction=ROW)) for _ in range(3)]
        button_style_adv = Pack(flex=1, padding=2, background_color='#E0E0E0')
        for i, (text, tooltip) in enumerate(adv_buttons_data):
            btn = toga.Button(text, on_press=self.handle_adv_button_press, style=button_style_adv)
            btn.tooltip = tooltip
            adv_rows[i // 2].add(btn)
        for row in adv_rows:
            self.advanced_box.add(row)

    def _create_history_panel(self):
        self.history_panel = toga.Box(style=Pack(direction=COLUMN))
        self.history_table = toga.Table(
            headings=['Expression', 'Total'],
            accessors=['expression', 'total'],
            on_select=self.handle_history_select,
            style=Pack(flex=1, height=150)
        )
        clear_history_button = toga.Button("Clear History", on_press=self.handle_clear_history,
                                           style=Pack(padding_top=5))
        self.history_panel.add(self.history_table)
        self.history_panel.add(clear_history_button)

    def _create_favorites_panel(self):
        self.favorites_panel = toga.Box(style=Pack(direction=COLUMN))
        self.favorites_table = toga.Table(
            headings=['Favorite Rolls'],
            accessors=['expression'],
            on_select=self.handle_favorite_select,
            style=Pack(flex=1, height=150)
        )
        fav_button_box = toga.Box(style=Pack(direction=ROW, padding_top=5))
        add_fav_button = toga.Button("Add Current", on_press=self.handle_add_favorite, style=Pack(flex=1))
        remove_fav_button = toga.Button("Remove", on_press=self.handle_remove_favorite, style=Pack(flex=1))
        fav_button_box.add(add_fav_button)
        fav_button_box.add(remove_fav_button)
        self.favorites_panel.add(self.favorites_table)
        self.favorites_panel.add(fav_button_box)

    # --- Persistence ---
    def _load_favorites(self):
        try:
            if self.favorites_file_path.exists():
                with self.favorites_file_path.open('r') as f:
                    self.favorites = json.load(f)
        except Exception as e:
            print(f"Could not load favorites: {e}")
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
        panel_map = {
            'Advanced': self.advanced_box,
            'History': self.history_panel,
            'Favorites': self.favorites_panel
        }
        button_text = widget.text
        # The 'C' button is a special case handled by handle_button_press
        if button_text == 'C':
            self.handle_button_press(widget)
            return

        target_panel = panel_map.get(button_text)

        for child in list(self.collapsible_panel.children):
            self.collapsible_panel.remove(child)

        if self.active_panel is target_panel:
            self.collapsible_panel.style.visibility = 'hidden'
            self.active_panel = None
        else:
            if button_text == 'History':
                self.history_table.data = self.roll_history
            elif button_text == 'Favorites':
                self.favorites_table.data = [{'expression': fav} for fav in self.favorites]

            self.collapsible_panel.add(target_panel)
            self.collapsible_panel.style.visibility = 'visible'
            self.active_panel = target_panel

    def handle_reroll_last(self, widget):
        if self.last_roll_expression:
            self.input_display.value = self.last_roll_expression
        self.input_display.focus()

    def handle_history_select(self, widget):
        if widget.selection is not None:
            self.input_display.value = widget.selection.expression
            self.input_display.focus()

    def handle_favorite_select(self, widget):
        if widget.selection is not None:
            self.input_display.value = widget.selection.expression
            self.input_display.focus()

    def handle_clear_history(self, widget):
        self.roll_history.clear()
        self.last_roll_expression = ""
        self.history_table.data = []
        self.output_display.value = "History has been cleared."
        self.input_display.focus()

    def handle_add_favorite(self, widget):
        expression = self.input_display.value.strip()
        if not expression:
            self.output_display.value = "Cannot save an empty favorite."
            return
        if expression not in self.favorites:
            self.favorites.append(expression)
            self.favorites.sort()
            self._save_favorites()
            if self.active_panel is self.favorites_panel:
                self.favorites_table.data = [{'expression': fav} for fav in self.favorites]
            self.output_display.value = f'Saved "{expression}" to favorites.'
        else:
            self.output_display.value = f'"{expression}" is already in favorites.'
        self.input_display.focus()

    def handle_remove_favorite(self, widget):
        if self.favorites_table.selection is None:
            self.output_display.value = "Select a favorite to remove first."
            return
        expression_to_remove = self.favorites_table.selection.expression
        if expression_to_remove in self.favorites:
            self.favorites.remove(expression_to_remove)
            self._save_favorites()
            self.favorites_table.data = [{'expression': fav} for fav in self.favorites]
            self.output_display.value = f'Removed "{expression_to_remove}" from favorites.'
        self.input_display.focus()

    def handle_button_press(self, widget):
        button_text = widget.text
        if button_text == 'C':
            self.input_display.value = ''
            self.output_display.value = ''
        elif button_text == 'DEL':
            self.input_display.value = self.input_display.value[:-1]
        elif button_text == 'Roll':
            self.perform_roll_logic()
        else:
            self.input_display.value += button_text
        self.input_display.focus()

    def handle_adv_button_press(self, widget):
        template = widget.text
        current_text = self.input_display.value
        command_map = {
            "Drop Lowest": "Drop Lowest ", "Drop Highest": "Drop Highest ",
            "Reroll <": "Reroll Less than ", "Reroll >": "Reroll Greater than ",
            "Min Val": "Minimum Value ", "Max Val": "Maximum Value "
        }
        command_text = command_map.get(template, "")
        if current_text.strip() and not current_text.endswith((',', ' ')):
            self.input_display.value += f", {command_text}"
        else:
            self.input_display.value += command_text
        self.input_display.focus()

    # --- Core Logic Functions ---
    def _parse_and_roll_term(self, term):
        term = term.strip()
        complex_pattern = re.compile(r"\((.+)\)")
        dice_pattern = re.compile(r"(\d*)d(\d+)")
        dice_expr, commands = term, []
        complex_match = complex_pattern.fullmatch(term)
        if complex_match:
            parts = complex_match.group(1).split(',')
            dice_expr = parts[0].strip()
            commands = [p.strip().lower() for p in parts[1:] if p.strip()]
        dice_match = dice_pattern.fullmatch(dice_expr)
        if not dice_match: return int(term), term
        num_dice_str, sides_str = dice_match.groups()
        num_dice = int(num_dice_str) if num_dice_str else 1
        sides = int(sides_str)
        if not (0 < num_dice <= 100 and 0 < sides <= 1000): raise ValueError("Dice count/sides out of range")
        rolls = [random.randint(1, sides) for _ in range(num_dice)]
        details = [f"{num_dice}d{sides} ({', '.join(map(str, rolls))})"]
        if not complex_match: return sum(rolls), " ".join(details) + f" = {sum(rolls)}"
        indexed_rolls = list(enumerate(rolls))
        reroll_lowest = sum([int(c.split()[-1]) for c in commands if c.startswith('reroll lowest')])
        reroll_highest = sum([int(c.split()[-1]) for c in commands if c.startswith('reroll highest')])
        if reroll_lowest > 0:
            indexed_rolls.sort(key=lambda x: x[1])
            for i in range(min(reroll_lowest, len(indexed_rolls))):
                original_index = indexed_rolls[i][0]
                new_roll = random.randint(1, sides)
                details.append(f"Reroll Lowest: {rolls[original_index]}→{new_roll}")
                rolls[original_index] = new_roll
            indexed_rolls = list(enumerate(rolls));
            details.append(f"→ ({','.join(map(str, rolls))})")
        if reroll_highest > 0:
            indexed_rolls.sort(key=lambda x: x[1], reverse=True)
            for i in range(min(reroll_highest, len(indexed_rolls))):
                original_index = indexed_rolls[i][0]
                new_roll = random.randint(1, sides)
                details.append(f"Reroll Highest: {rolls[original_index]}→{new_roll}")
                rolls[original_index] = new_roll
            details.append(f"→ ({','.join(map(str, rolls))})")
        for cmd in [c for c in commands if "less than" in c or "greater than" in c]:
            value = int(cmd.split()[-1]);
            reroll_made = False
            for i in range(len(rolls)):
                should_reroll = ("less than" in cmd and rolls[i] < value) or (
                            "greater than" in cmd and rolls[i] > value)
                if should_reroll:
                    reroll_made = True;
                    original_val = rolls[i];
                    rolls[i] = random.randint(1, sides)
                    details.append(f"Reroll Val: {original_val}→{rolls[i]}")
            if reroll_made: details.append(f"→ ({','.join(map(str, rolls))})")
        min_value_cmds = [c for c in commands if c.startswith('minimum value')]
        max_value_cmds = [c for c in commands if c.startswith('maximum value')]
        if min_value_cmds:
            min_val = int(min_value_cmds[0].split()[-1]);
            modified_rolls = [max(r, min_val) for r in rolls]
            if rolls != modified_rolls: rolls = modified_rolls; details.append(
                f"Min Val {min_val}: → ({','.join(map(str, rolls))})")
        if max_value_cmds:
            max_val = int(max_value_cmds[0].split()[-1]);
            modified_rolls = [min(r, max_val) for r in rolls]
            if rolls != modified_rolls: rolls = modified_rolls; details.append(
                f"Max Val {max_val}: → ({','.join(map(str, rolls))})")
        drop_lowest = sum([int(c.split()[-1]) for c in commands if c.startswith('drop lowest')])
        drop_highest = sum([int(c.split()[-1]) for c in commands if c.startswith('drop highest')])
        if drop_lowest > 0:
            sorted_for_drop = sorted(rolls)
            for i in range(min(drop_lowest, len(rolls))): val_to_drop = sorted_for_drop[i]; rolls.remove(val_to_drop)
            details.append(f"Drop L{drop_lowest}: → ({','.join(map(str, rolls))})")
        if drop_highest > 0:
            sorted_for_drop = sorted(rolls)
            for i in range(min(drop_highest, len(rolls))): val_to_drop = sorted_for_drop[-(i + 1)]; rolls.remove(
                val_to_drop)
            details.append(f"Drop H{drop_highest}: → ({','.join(map(str, rolls))})")
        final_sum = sum(rolls);
        details.append(f"= {final_sum}")
        return final_sum, "\n    ".join(details)

    def perform_roll_logic(self):
        expression = self.input_display.value.strip()
        self.output_display.value = ""
        if not expression: self.output_display.value = "Please enter a dice expression."; return
        if expression.count('(') != expression.count(
            ')'): self.output_display.value = "Error: Mismatched parentheses.\nPlease check your input."; return
        notification = ""
        if self.roll_counter >= 1000:
            self.roll_counter = 0;
            self.roll_history.clear();
            self.last_roll_expression = ""
            notification = "* Roll history cleared after 1000 rolls. *\n\n"
        self.output_display.value = notification + f"Rolling: {expression}\n"
        term_finder = re.compile(r'([+-])?\s*(\([^)]+\)|\d+d\d+|\d+)')
        expression_to_parse = expression
        if not expression.startswith(('+', '-')): expression_to_parse = '+' + expression
        matches = term_finder.finditer(expression_to_parse)
        grand_total = 0
        try:
            full_breakdown_str = ""
            for i, match in enumerate(matches):
                sign_str, term_str = match.groups();
                sign = -1 if sign_str == '-' else 1
                term_sum, details_str = self._parse_and_roll_term(term_str)
                grand_total += term_sum * sign
                if i > 0:
                    full_breakdown_str += f" {'-' if sign < 0 else '+'} "
                elif sign < 0:
                    full_breakdown_str += "- "
                full_breakdown_str += details_str
            self.roll_counter += 1;
            self.last_roll_expression = expression
            new_history_entry = {'expression': expression, 'total': grand_total}
            if not self.roll_history or self.roll_history[0]['expression'] != expression:
                self.roll_history.insert(0, new_history_entry)
                self.roll_history = self.roll_history[:20]
                if self.active_panel is self.history_panel: self.history_table.data = self.roll_history
            grand_total_string = f"Grand Total: {grand_total}"
            breakdown_header = "Breakdown:"
            self.output_display.value += f"\n\n{grand_total_string}\n\n{breakdown_header}\n{full_breakdown_str}"
        except ValueError as e:
            self.output_display.value += f"\nError: Could not parse expression. ({e})"
        except Exception as e:
            self.output_display.value += f"\nAn unexpected error occurred: {e}"


def main():
    return DiceRollerApp('DiceRoller', 'org.example.diceroller')