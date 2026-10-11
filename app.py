import sys
import random
import os
import math
import wave
import struct
import tempfile
import shutil

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGridLayout, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QUrl
from PySide6.QtGui import QFont, QAction

# Attempt to import QSoundEffect for professional sounds
try:
    from PySide6.QtMultimedia import QSoundEffect
    SOUND_ENABLED = True
except ImportError:
    SOUND_ENABLED = False

# ─── 8-bit Sound Synthesis Helpers ────────────────────────────────────────────

def generate_sweep(start_freq, end_freq, duration, volume=0.5, decay=8, sample_rate=44100, wave_type="square"):
    """Generates a waveform with a pitch sweep (portamento) and exponential decay."""
    num_samples = int(sample_rate * duration)
    samples = []
    phase = 0.0
    
    for i in range(num_samples):
        t = i / sample_rate
        # Exponential volume decay
        env = math.exp(-t * decay)
        
        # Linear frequency sweep interpolation
        freq = start_freq + (end_freq - start_freq) * (i / num_samples)
        
        # Phase accumulator prevents audio clicks/glitches when frequency changes
        phase += 2 * math.pi * freq / sample_rate
        
        # Waveform generation
        if wave_type == "square":
            val = 1.0 if (phase % (2 * math.pi)) < math.pi else -1.0
        elif wave_type == "triangle":
            p = (phase % (2 * math.pi)) / math.pi
            if p < 0.5:
                val = 4 * p - 1
            elif p < 1.5:
                val = 3 - 4 * p
            else:
                val = 4 * p - 5
        else:  # sine
            val = math.sin(phase)
            
        sample = volume * env * val
        samples.append(int(max(min(sample, 1.0), -1.0) * 32767))
    return samples

def generate_noise_sweep(start_freq, end_freq, duration, volume=0.9, decay=5, sample_rate=44100):
    """Generates a noise channel with a pitch sweep (classic 8-bit explosion)."""
    num_samples = int(sample_rate * duration)
    samples = []
    phase = 0.0
    
    for i in range(num_samples):
        t = i / sample_rate
        env = math.exp(-t * decay)
        freq = start_freq + (end_freq - start_freq) * (i / num_samples)
        phase += 2 * math.pi * freq / sample_rate
        
        # Simulate NES noise channel: flip state based on frequency
        if (phase % (2 * math.pi)) < (2 * math.pi * freq / sample_rate):
            noise_state = 1.0 if random.random() > 0.5 else -1.0
            
        sample = volume * env * noise_state
        samples.append(int(max(min(sample, 1.0), -1.0) * 32767))
    return samples

def save_wav(filename, samples, sample_rate=44100):
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        data = struct.pack('<' + ('h' * len(samples)), *samples)
        wav_file.writeframes(data)

# ─── Sound Manager ────────────────────────────────────────────────────────────

if SOUND_ENABLED:
    class SoundManager:
        """Handles generating and playing game sound effects without external files."""
        def __init__(self):
            self.sounds = {}
            self.temp_dir = tempfile.mkdtemp()
            self._create_sound_files()
            self._load_sound("click", "click.wav", 0.8)
            self._load_sound("flag", "flag.wav", 0.8)
            self._load_sound("unflag", "unflag.wav", 0.8)
            self._load_sound("explosion", "explosion.wav", 0.9)
            self._load_sound("win", "win.wav", 0.9)

        def _create_sound_files(self):
            # Click: Snappy descending blip (Square wave)
            click_samples = generate_sweep(1600, 800, 0.06, volume=0.5, decay=30, wave_type="square")
            save_wav(os.path.join(self.temp_dir, "click.wav"), click_samples)
            
            # Flag: Ascending "pling" (Square wave sweep up)
            flag_samples = generate_sweep(400, 1200, 0.1, volume=0.5, decay=20, wave_type="square")
            save_wav(os.path.join(self.temp_dir, "flag.wav"), flag_samples)
            
            # Unflag: Descending "dwop" (Triangle wave sweep down)
            unflag_samples = generate_sweep(1200, 400, 0.1, volume=0.6, decay=20, wave_type="triangle")
            save_wav(os.path.join(self.temp_dir, "unflag.wav"), unflag_samples)
            
            # Explosion: Pitch-dropping noise rumble (Classic NES style)
            explosion_samples = generate_noise_sweep(400, 50, 0.4, volume=0.8, decay=6)
            save_wav(os.path.join(self.temp_dir, "explosion.wav"), explosion_samples)
            
            # Win: Triumphant 8-bit jingle sequence (Square wave)
            # Notes: E5, G5, C6 (quick), then high E6 held
            win_samples = []
            win_samples.extend(generate_sweep(659, 659, 0.08, volume=0.5, decay=15, wave_type="square")) # E5
            win_samples.extend(generate_sweep(784, 784, 0.08, volume=0.5, decay=15, wave_type="square")) # G5
            win_samples.extend(generate_sweep(1047, 1047, 0.15, volume=0.5, decay=10, wave_type="square")) # C6
            win_samples.extend(generate_sweep(1319, 1319, 0.35, volume=0.6, decay=4, wave_type="square")) # E6 (Held)
            save_wav(os.path.join(self.temp_dir, "win.wav"), win_samples)

        def _load_sound(self, name, filename, volume):
            path = os.path.join(self.temp_dir, filename)
            sound = QSoundEffect()
            sound.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            sound.setVolume(volume)
            self.sounds[name] = sound

        def play(self, name: str):
            if name in self.sounds:
                sound = self.sounds[name]
                
                # Handle PySide6 (Qt6) vs older PySide2/Qt5 API differences
                try:
                    # Qt6 uses status() instead of isReady()
                    is_ready = sound.status() == QSoundEffect.Status.Ready
                except AttributeError:
                    # Fallback for Qt5
                    is_ready = sound.isReady()
                
                if is_ready:
                    if sound.isPlaying():
                        sound.stop()
                    sound.play()
                    
        def cleanup(self):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass
else:
    class SoundManager:
        """Dummy SoundManager if QtMultimedia is not available."""
        def play(self, name: str):
            pass
        def cleanup(self):
            pass

# ─── Constants ────────────────────────────────────────────────────────────────

NUM_COLORS = {
    1: "#0000FF",  # Blue
    2: "#008000",  # Green
    3: "#FF0000",  # Red
    4: "#000080",  # Dark Blue
    5: "#800000",  # Maroon
    6: "#008080",  # Teal
    7: "#000000",  # Black
    8: "#808080",  # Gray
}

DIFFICULTIES = {
    "Beginner":     (9,  9,  10),
    "Intermediate": (16, 16, 40),
    "Expert":       (16, 30, 99),
}

# ─── Cell Widget ──────────────────────────────────────────────────────────────

class Cell(QPushButton):
    """A single Minesweeper grid cell."""

    left_clicked  = Signal(int, int)
    right_clicked = Signal(int, int)

    def __init__(self, row: int, col: int, parent=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.is_mine = False
        self.is_revealed = False
        self.is_flagged = False
        self.adjacent_mines = 0

        self.setFixedSize(32, 32)
        self.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setObjectName("cell")
        self._apply_unrevealed_style()

    # ── Style helpers ──────────────────────────────────────────────────────

    def _apply_unrevealed_style(self):
        self.setStyleSheet("""
            QPushButton#cell {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #C0C7CE, stop:1 #A4B0BA);
                border: 1px solid #7F8C8D;
                border-radius: 3px;
            }
            QPushButton#cell:hover {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #AAB7C2, stop:1 #8E9DAA);
            }
            QPushButton#cell:pressed {
                background-color: #7F8C8D;
            }
        """)

    def _apply_flagged_style(self):
        self.setStyleSheet("""
            QPushButton#cell {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5DADE2, stop:1 #2E86C1);
                border: 1px solid #2471A3;
                border-radius: 3px;
            }
        """)

    def _apply_revealed_style(self, color: str | None = None):
        if color:
            self.setStyleSheet(f"""
                QPushButton#cell {{
                    background-color: #ECF0F1;
                    border: 1px solid #D5DBDB;
                    border-radius: 3px;
                    color: {color};
                }}
            """)
        else:
            self.setStyleSheet("""
                QPushButton#cell {
                    background-color: #ECF0F1;
                    border: 1px solid #D5DBDB;
                    border-radius: 3px;
                }
            """)

    def _apply_mine_style(self):
        self.setStyleSheet("""
            QPushButton#cell {
                background-color: #E74C3C;
                border: 1px solid #C0392B;
                border-radius: 3px;
            }
        """)

    def _apply_exploded_style(self):
        self.setStyleSheet("""
            QPushButton#cell {
                background-color: #922B21;
                border: 2px solid #641E16;
                border-radius: 3px;
            }
        """)

    def _apply_wrong_flag_style(self):
        self.setStyleSheet("""
            QPushButton#cell {
                background-color: #F39C12;
                border: 1px solid #E67E22;
                border-radius: 3px;
            }
        """)

    def _apply_win_flag_style(self):
        self.setStyleSheet("""
            QPushButton#cell {
                background-color: #2ECC71;
                border: 1px solid #27AE60;
                border-radius: 3px;
            }
        """)

    # ── Interaction ────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.left_clicked.emit(self.row, self.col)
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit(self.row, self.col)

    def toggle_flag(self):
        if self.is_revealed:
            return
        self.is_flagged = not self.is_flagged
        if self.is_flagged:
            self.setText("🚩")
            self._apply_flagged_style()
        else:
            self.setText("")
            self._apply_unrevealed_style()

    def set_revealed(self):
        self.is_revealed = True
        if self.is_mine:
            self.setText("💣")
            self._apply_mine_style()
        elif self.adjacent_mines > 0:
            self.setText(str(self.adjacent_mines))
            color = NUM_COLORS.get(self.adjacent_mines, "#000000")
            self._apply_revealed_style(color)
        else:
            self.setText("")
            self._apply_revealed_style()

    def reset(self):
        self.is_mine = False
        self.is_revealed = False
        self.is_flagged = False
        self.adjacent_mines = 0
        self.setText("")
        self.setEnabled(True)
        self._apply_unrevealed_style()


# ─── Game Board Widget ────────────────────────────────────────────────────────

class MinesweeperGame(QWidget):
    """Core game widget: board, controls, and logic."""

    game_won  = Signal()
    game_lost = Signal()

    def __init__(self, rows: int = 9, cols: int = 9, mines: int = 10, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.num_mines = mines
        self.flag_mode = False
        self.game_over = False
        self.first_click = True
        self.flags_placed = 0
        self.elapsed_time = 0
        self.cells: list[list[Cell]] = []
        
        # Initialize the sound manager
        self.sound_manager = SoundManager()

        self._setup_ui()
        self._create_board()

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick_timer)

    # ── UI Construction ────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # --- Top bar ---
        top = QFrame()
        top.setObjectName("topBar")
        top.setStyleSheet("QFrame#topBar { background-color: #2C3E50; border-radius: 10px; }")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(16, 10, 16, 10)
        top_layout.setSpacing(12)

        self.mine_label = QLabel(f"💣 {self.num_mines:02d}")
        self.mine_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.mine_label.setStyleSheet("color: #E74C3C; background: transparent;")
        self.mine_label.setAlignment(Qt.AlignCenter)
        self.mine_label.setFixedWidth(90)

        self.timer_label = QLabel("⏱ 000")
        self.timer_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.timer_label.setStyleSheet("color: #2ECC71; background: transparent;")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setFixedWidth(100)

        self.reset_btn = QPushButton("😀")
        self.reset_btn.setFont(QFont("Segoe UI Emoji", 24))
        self.reset_btn.setFixedSize(52, 52)
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.setToolTip("New Game")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495E; border: 2px solid #4A6278; border-radius: 10px;
            }
            QPushButton:hover { background-color: #3D566E; }
            QPushButton:pressed { background-color: #2C3E50; }
        """)
        self.reset_btn.clicked.connect(self.reset_game)

        self.flag_btn = QPushButton("🚩 Flag")
        self.flag_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.flag_btn.setCheckable(True)
        self.flag_btn.setCursor(Qt.PointingHandCursor)
        self.flag_btn.setToolTip("Toggle Flag Mode (F)")
        self.flag_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495E; border: 2px solid #4A6278;
                border-radius: 8px; color: #BDC3C7; padding: 8px 16px;
            }
            QPushButton:hover { background-color: #3D566E; }
            QPushButton:checked {
                background-color: #E74C3C; border-color: #C0392B; color: white;
            }
        """)
        self.flag_btn.clicked.connect(self._toggle_flag_mode)

        top_layout.addWidget(self.mine_label)
        top_layout.addStretch()
        top_layout.addWidget(self.reset_btn)
        top_layout.addStretch()
        top_layout.addWidget(self.flag_btn)
        top_layout.addWidget(self.timer_label)

        # --- Board frame ---
        self.board_frame = QFrame()
        self.board_frame.setObjectName("boardFrame")
        self.board_frame.setStyleSheet(
            "QFrame#boardFrame { background-color: #34495E; border-radius: 10px; }"
        )
        self.board_layout = QGridLayout(self.board_frame)
        self.board_layout.setSpacing(2)
        self.board_layout.setContentsMargins(8, 8, 8, 8)

        layout.addWidget(top)
        layout.addWidget(self.board_frame, 1)

    def _create_board(self):
        # Remove old widgets
        while self.board_layout.count():
            item = self.board_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.cells = [[None] * self.cols for _ in range(self.rows)]
        for r in range(self.rows):
            for c in range(self.cols):
                cell = Cell(r, c)
                cell.left_clicked.connect(self._on_left_click)
                cell.right_clicked.connect(self._on_right_click)
                self.cells[r][c] = cell
                self.board_layout.addWidget(cell, r, c)

    # ── Slot helpers ───────────────────────────────────────────────────────

    def _toggle_flag_mode(self):
        self.flag_mode = self.flag_btn.isChecked()

    def _on_left_click(self, r: int, c: int):
        if self.game_over or self.cells[r][c].is_revealed:
            return
        if self.flag_mode:
            self._toggle_flag_cell(r, c)
        else:
            self.reveal(r, c)

    def _on_right_click(self, r: int, c: int):
        if self.game_over or self.cells[r][c].is_revealed:
            return
        self._toggle_flag_cell(r, c)

    def _toggle_flag_cell(self, r: int, c: int):
        cell = self.cells[r][c]
        if cell.is_revealed:
            return
        was_flagged = cell.is_flagged
        cell.toggle_flag()
        self.flags_placed += -1 if was_flagged else 1
        self._update_counters()
        
        # Play flag/unflag sounds
        if was_flagged:
            self.sound_manager.play("unflag")
        else:
            self.sound_manager.play("flag")

    def _update_counters(self):
        remaining = self.num_mines - self.flags_placed
        self.mine_label.setText(f"💣 {remaining:02d}")

    def _tick_timer(self):
        self.elapsed_time += 1
        self.timer_label.setText(f"⏱ {self.elapsed_time:03d}")

    # ── Core game logic ────────────────────────────────────────────────────

    def place_mines(self, safe_r: int, safe_c: int):
        """Place mines, guaranteeing *safe_r, safe_c* and its neighbours are clear."""
        safe = set()
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = safe_r + dr, safe_c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    safe.add((nr, nc))

        candidates = [
            (r, c) for r in range(self.rows) for c in range(self.cols)
            if (r, c) not in safe
        ]
        random.shuffle(candidates)

        for i in range(min(self.num_mines, len(candidates))):
            r, c = candidates[i]
            self.cells[r][c].is_mine = True

        # Pre‑compute adjacency counts
        for r in range(self.rows):
            for c in range(self.cols):
                if not self.cells[r][c].is_mine:
                    count = 0
                    for dr in (-1, 0, 1):
                        for dc in (-1, 0, 1):
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                                if self.cells[nr][nc].is_mine:
                                    count += 1
                    self.cells[r][c].adjacent_mines = count

    def reveal(self, r: int, c: int):
        """Iterative flood‑fill reveal starting at (r, c)."""
        if self.game_over:
            return

        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            cell = self.cells[cr][cc]

            if cell.is_revealed or cell.is_flagged:
                continue

            # First‑click safety: generate board only after first click
            if self.first_click:
                self.place_mines(cr, cc)
                self.first_click = False
                self.timer.start()

            cell.set_revealed()

            if cell.is_mine:
                self.sound_manager.play("explosion")
                self._trigger_game_over(cr, cc)
                return

            # Only play the click sound for the originally clicked cell, 
            # not for every cell uncovered in the flood fill
            if cr == r and cc == c:
                self.sound_manager.play("click")

            if cell.adjacent_mines == 0:
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            neighbour = self.cells[nr][nc]
                            if not neighbour.is_revealed and not neighbour.is_flagged:
                                stack.append((nr, nc))

        self._check_win()

    def _trigger_game_over(self, click_r: int, click_c: int):
        self.game_over = True
        self.timer.stop()
        self.reset_btn.setText("😵")

        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                if cell.is_mine and not cell.is_flagged:
                    cell.set_revealed()
                    # Highlight the mine the player actually clicked
                    if r == click_r and c == click_c:
                        cell._apply_exploded_style()
                elif not cell.is_mine and cell.is_flagged:
                    cell.setText("❌")
                    cell._apply_wrong_flag_style()

        self.game_lost.emit()

    def _check_win(self):
        if self.game_over:
            return
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                if not cell.is_mine and not cell.is_revealed:
                    return  # still cells to uncover

        # All safe cells revealed → victory
        self.game_over = True
        self.timer.stop()
        self.reset_btn.setText("😎")
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                if cell.is_mine:
                    cell.setText("🚩")
                    cell._apply_win_flag_style()
        
        self.sound_manager.play("win")
        self.game_won.emit()

    # ── Reset / New game ───────────────────────────────────────────────────

    def reset_game(self):
        self.game_over = False
        self.first_click = True
        self.flags_placed = 0
        self.elapsed_time = 0
        self.timer.stop()
        self._update_counters()
        self.timer_label.setText("⏱ 000")
        self.reset_btn.setText("😀")
        self.flag_btn.setChecked(False)
        self.flag_mode = False
        for r in range(self.rows):
            for c in range(self.cols):
                self.cells[r][c].reset()

    def new_game(self, rows: int, cols: int, mines: int):
        self.rows = rows
        self.cols = cols
        self.num_mines = mines
        self.game_over = False
        self.first_click = True
        self.flags_placed = 0
        self.elapsed_time = 0
        self.timer.stop()
        self._update_counters()
        self.timer_label.setText("⏱ 000")
        self.reset_btn.setText("😀")
        self.flag_btn.setChecked(False)
        self.flag_mode = False
        self._create_board()


# ─── Main Window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """Top‑level application window with menus and status bar."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("💣 Minesweeper")
        self.setMinimumSize(350, 450)
        self.resize(420, 520)

        self.game = MinesweeperGame(9, 9, 10)
        self.setCentralWidget(self.game)

        self.game.game_won.connect(self._on_win)
        self.game.game_lost.connect(self._on_loss)

        self._build_menus()
        self.statusBar().showMessage(
            "Left‑click: Reveal  |  Right‑click: Flag  |  First click is always safe!"
        )
        self._apply_global_style()

    # ── Menus ──────────────────────────────────────────────────────────────

    def _build_menus(self):
        menu_bar = self.menuBar()

        # Game menu
        game_menu = menu_bar.addMenu("&Game")

        new_act = QAction("🆕 New Game", self)
        new_act.setShortcut("Ctrl+N")
        new_act.triggered.connect(self.game.reset_game)
        game_menu.addAction(new_act)

        game_menu.addSeparator()

        diff_menu = game_menu.addMenu("📊 Difficulty")
        for name, (r, c, m) in DIFFICULTIES.items():
            act = QAction(name, self)
            act.triggered.connect(
                lambda _, rows=r, cols=c, mines=m: self._set_difficulty(rows, cols, mines)
            )
            diff_menu.addAction(act)

        game_menu.addSeparator()

        quit_act = QAction("❌ Quit", self)
        quit_act.setShortcut("Ctrl+Q")
        quit_act.triggered.connect(self.close)
        game_menu.addAction(quit_act)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        about_act = QAction("About", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _set_difficulty(self, rows: int, cols: int, mines: int):
        self.game.new_game(rows, cols, mines)
        w = max(350, cols * 36 + 60)
        h = max(450, rows * 36 + 200)
        self.resize(w, h)
        self.statusBar().showMessage(f"New game: {rows}×{cols} grid, {mines} mines")

    def _on_win(self):
        self.statusBar().showMessage("🎉 Congratulations — you won!")

    def _on_loss(self):
        self.statusBar().showMessage("💥 Game over! Click 😀 to try again.")

    def _show_about(self):
        QMessageBox.about(
            self,
            "About Minesweeper",
            "<h2>💣 Minesweeper</h2>"
            "<p>A classic Minesweeper built with <b>PySide6</b>.</p><hr>"
            "<p><b>Controls</b></p><ul>"
            "<li>Left‑click — Reveal cell</li>"
            "<li>Right‑click — Toggle flag</li>"
            "<li>Flag Mode button / <b>F</b> — Switch left‑click to flag mode</li>"
            "<li><b>Ctrl+N</b> — New game</li></ul>"
            "<p><b>Tips</b></p><ul>"
            "<li>Your first click is always safe!</li>"
            "<li>Numbers indicate adjacent mine count.</li>"
            "<li>Flag all mines and reveal every safe cell to win.</li></ul>",
        )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F:
            self.game.flag_btn.toggle()
            self.game._toggle_flag_mode()
        super().keyPressEvent(event)
        
    def closeEvent(self, event):
        # Clean up the temporary sound files when closing the app
        self.game.sound_manager.cleanup()
        super().closeEvent(event)

    # ── Global stylesheet ──────────────────────────────────────────────────

    def _apply_global_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2C3E50;
            }
            QMenuBar {
                background-color: #2C3E50;
                color: #ECF0F1;
                border-bottom: 2px solid #34495E;
                padding: 2px;
                font-size: 13px;
            }
            QMenuBar::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #34495E;
            }
            QMenu {
                background-color: #2C3E50;
                color: #ECF0F1;
                border: 1px solid #4A6278;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 28px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3498DB;
            }
            QMenu::separator {
                height: 1px;
                background: #4A6278;
                margin: 4px 12px;
            }
            QStatusBar {
                background-color: #1A252F;
                color: #95A5A6;
                border-top: 1px solid #34495E;
                font-size: 12px;
                padding: 4px;
            }
        """)


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()