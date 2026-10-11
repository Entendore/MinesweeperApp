import random
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

# Color dictionary for numbers 1-8
NUM_COLORS = {
    1: get_color_from_hex('#0000FF'), # Blue
    2: get_color_from_hex('#008000'), # Green
    3: get_color_from_hex('#FF0000'), # Red
    4: get_color_from_hex('#000080'), # Dark Blue
    5: get_color_from_hex('#800000'), # Maroon
    6: get_color_from_hex('#008080'), # Teal
    7: get_color_from_hex('#000000'), # Black
    8: get_color_from_hex('#808080'), # Gray
}

class Cell(Button):
    def __init__(self, row, col, **kwargs):
        super(Cell, self).__init__(**kwargs)
        self.row = row
        self.col = col
        self.font_size = '20sp'
        self.is_mine = False
        self.is_revealed = False
        self.is_flagged = False
        self.adjacent_mines = 0
        
    def on_touch_down(self, touch):
        # Prevent actions if game is over
        if self.parent and self.parent.parent.game_over:
            return
        
        if self.collide_point(*touch.pos):
            if self.is_revealed:
                return
                
            # Right click for flagging (Desktop)
            if touch.button == 'right':
                self.toggle_flag()
            # Left click
            elif touch.button == 'left':
                board = App.get_running_app().root
                if board.flag_mode:
                    self.toggle_flag()
                else:
                    board.reveal(self.row, self.col)
            return True # Consume the touch

    def toggle_flag(self):
        if not self.is_flagged:
            self.is_flagged = True
            self.text = "🚩"
            self.color = get_color_from_hex('#FF0000')
        else:
            self.is_flagged = False
            self.text = ""
            
    def reset(self):
        self.is_mine = False
        self.is_revealed = False
        self.is_flagged = False
        self.adjacent_mines = 0
        self.text = ""
        self.disabled = False
        self.background_color = get_color_from_hex('#B0B0B0')
        self.color = (1, 1, 1, 1)

class MinesweeperGame(BoxLayout):
    def __init__(self, rows=10, cols=10, mines=15, **kwargs):
        super(MinesweeperGame, self).__init__(**kwargs)
        self.rows = rows
        self.cols = cols
        self.num_mines = mines
        self.flag_mode = False
        self.game_over = False
        self.first_click = True
        self.flags_placed = 0
        
        self.orientation = 'vertical'
        self.spacing = 5
        self.padding = [10, 10, 10, 10]
        
        # --- Top Bar ---
        top_bar = BoxLayout(size_hint_y=0.1, spacing=10)
        
        self.mine_counter = Label(text=f"Mines: {self.num_mines}", font_size='20sp', size_hint_x=0.4)
        self.reset_btn = Button(text="😀", font_size='30sp', on_press=self.reset_game, size_hint_x=0.2)
        self.flag_btn = ToggleButton(text="🚩 Flag", font_size='16sp', on_press=self.toggle_flag_mode, size_hint_x=0.4)
        
        top_bar.add_widget(self.mine_counter)
        top_bar.add_widget(self.reset_btn)
        top_bar.add_widget(self.flag_btn)
        
        # --- Grid ---
        self.grid = GridLayout(cols=self.cols, rows=self.rows, spacing=2)
        self.cells = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        
        for r in range(self.rows):
            for c in range(self.cols):
                cell = Cell(r, c)
                self.cells[r][c] = cell
                self.grid.add_widget(cell)
                
        self.add_widget(top_bar)
        self.add_widget(self.grid)
        
    def toggle_flag_mode(self, instance):
        self.flag_mode = not self.flag_mode
        instance.state = 'down' if self.flag_mode else 'normal'
        
    def place_mines(self, safe_r, safe_c):
        """Place mines, ensuring the first clicked cell and its neighbors are safe."""
        safe_cells = set()
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr, nc = safe_r + dr, safe_c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    safe_cells.add((nr, nc))
                    
        possible_cells = [(r, c) for r in range(self.rows) for c in range(self.cols) if (r, c) not in safe_cells]
        random.shuffle(possible_cells)
        
        mines_to_place = min(self.num_mines, len(possible_cells))
        for i in range(mines_to_place):
            r, c = possible_cells[i]
            self.cells[r][c].is_mine = True
            
        # Calculate adjacent mines for all cells
        for r in range(self.rows):
            for c in range(self.cols):
                if not self.cells[r][c].is_mine:
                    count = 0
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                                if self.cells[nr][nc].is_mine:
                                    count += 1
                    self.cells[r][c].adjacent_mines = count

    def reveal(self, r, c):
        if self.game_over or self.cells[r][c].is_revealed or self.cells[r][c].is_flagged:
            return
            
        # First click logic: generate board after first click to guarantee safety
        if self.first_click:
            self.place_mines(r, c)
            self.first_click = False
            
        cell = self.cells[r][c]
        cell.is_revealed = True
        cell.background_color = get_color_from_hex('#E0E0E0') # Light grey for revealed
        
        if cell.is_mine:
            self.trigger_game_over()
            return
            
        if cell.adjacent_mines > 0:
            cell.text = str(cell.adjacent_mines)
            cell.color = NUM_COLORS.get(cell.adjacent_mines, (1,1,1,1))
        else:
            # Flood fill (recursive reveal for empty cells)
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        self.reveal(nr, nc)
                        
        self.check_win()

    def trigger_game_over(self):
        self.game_over = True
        self.reset_btn.text = "😵"
        # Reveal all mines
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                if cell.is_mine and not cell.is_flagged:
                    cell.text = "💣"
                    cell.color = get_color_from_hex('#000000')
                    if cell.is_revealed: # The mine we clicked
                        cell.background_color = get_color_from_hex('#FF0000')
                elif not cell.is_mine and cell.is_flagged:
                    cell.text = "❌" # Wrong flag
                    cell.color = get_color_from_hex('#000000')

    def check_win(self):
        if self.game_over:
            return
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                if not cell.is_mine and not cell.is_revealed:
                    return # Game not won yet
                    
        # If we reach here, all non-mine cells are revealed
        self.game_over = True
        self.reset_btn.text = "😎"
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                if cell.is_mine:
                    cell.text = "🚩" # Auto-flag remaining mines on win
                    cell.color = get_color_from_hex('#FF0000')
                    
    def reset_game(self, instance=None):
        self.game_over = False
        self.first_click = True
        self.flags_placed = 0
        self.mine_counter.text = f"Mines: {self.num_mines}"
        self.reset_btn.text = "😀"
        self.flag_btn.state = 'normal'
        self.flag_mode = False
        
        for r in range(self.rows):
            for c in range(self.cols):
                self.cells[r][c].reset()

class MinesweeperApp(App):
    def build(self):
        Window.clearcolor = get_color_from_hex('#F0F0F0')
        return MinesweeperGame(rows=10, cols=10, mines=15)

if __name__ == '__main__':
    MinesweeperApp().run()