# Minesweeper

A Minesweeper implementation built with Python and PySide6. The application features a custom dark UI, procedurally synthesized 8-bit audio, and three standard difficulty levels.

---

## Features

- **Difficulty Presets**: Beginner (9x9, 10 mines), Intermediate (16x16, 40 mines), Expert (16x30, 99 mines).
- **First-Click Safety**: Mine generation is deferred until the first cell is revealed, ensuring the selected cell and its 8 neighbors are always mine-free.
- **Procedural 8-bit Audio**: Sound effects are synthesized programmatically at runtime using math and wave generation. No external audio files are required.
- **Flag Mode**: A toggleable mode (via keyboard `F` or UI button) that converts the left mouse button into a flag placement tool.
- **Iterative Flood-Fill**: Empty cells automatically reveal adjacent empty cells using a stack-based algorithm, preventing recursion limit errors on large boards.
- **State-Driven Styling**: Cells have distinct visual states (unrevealed, hovered, flagged, revealed, exploded, wrong flag, win flag) managed via Qt Style Sheets.

---

## Controls

| Action | Input |
|---|---|
| Reveal cell | Left-click |
| Toggle flag | Right-click |
| Toggle flag mode | `F` key or Flag button |
| New game | `Ctrl+N` or Reset button |
| Quit | `Ctrl+Q` |

---

## Installation

### Prerequisites

- Python 3.10 or higher
- PySide6

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Entendore/Minesweeper.git
   cd minesweeper
   ```

2. Install the required package:
   ```bash
   pip install PySide6
   ```

3. Run the application:
   ```bash
   python app.py
   ```

---

## Architecture

The application is contained within a single file (`app.py`) and relies on four core classes:

| Class | Inherits | Description |
|---|---|---|
| `Cell` | `QPushButton` | UI component for a single grid cell. Emits `left_clicked` and `right_clicked` signals. Contains logic for toggling flags, setting revealed states, and applying corresponding Qt Style Sheets. |
| `MinesweeperGame` | `QWidget` | Core game logic widget. Manages board creation, mine placement, stack-based flood-fill reveal, timer, win/loss detection, and UI counters. |
| `SoundManager` | N/A | Generates `.wav` files in a temporary directory on initialization. Loads them into `QSoundEffect` instances for playback. Handles cleanup of the temporary directory on application exit. |
| `MainWindow` | `QMainWindow` | Top-level window. Configures menus, status bar, global styling, and keyboard shortcuts. |

---

## Audio Synthesis Details

Audio is generated using Python's `wave` and `struct` modules to write 16-bit mono PCM WAV files. Phase accumulators are used during waveform generation to prevent audio glitches during frequency sweeps.

| Sound | Waveform | Sweep Range | Duration | Description |
|---|---|---|---|---|
| Click | Square | 1600 Hz -> 800 Hz | 60 ms | Snappy descending blip |
| Flag | Square | 400 Hz -> 1200 Hz | 100 ms | Ascending pling |
| Unflag | Triangle | 1200 Hz -> 400 Hz | 100 ms | Descending dwop |
| Explosion | Noise | 400 Hz -> 50 Hz | 400 ms | Pitch-dropping noise rumble |
| Victory | Square | Static pitches | 660 ms | Sequential tones: E5, G5, C6, E6 |

If `PySide6.QtMultimedia` is unavailable (e.g., missing OS-level multimedia libraries), the `SoundManager` gracefully degrades into a silent dummy class, allowing the game to run without audio.

---

## Game Rules

1. Left-click a cell to reveal it.
2. A revealed cell displays a number indicating the count of mines in its 8 adjacent cells.
3. A revealed cell displaying a 0 automatically reveals its adjacent cells (flood-fill).
4. Right-click a cell to place a flag if you suspect it contains a mine.
5. The game is won when all non-mine cells are revealed.
6. The game is lost if a mine is revealed. Upon loss, all unflagged mines are revealed, and incorrectly placed flags are highlighted.

---

## Difficulty Presets

| Difficulty | Rows | Columns | Mines |
|---|---|---|---|
| Beginner | 9 | 9 | 10 |
| Intermediate | 16 | 16 | 40 |
| Expert | 16 | 30 | 99 |

---

## Technical Notes

- **Audio Fallback**: The `SoundManager.play()` method includes a fallback to check `isReady()` for Qt5 compatibility, though PySide6 utilizes `status() == QSoundEffect.Status.Ready`.
- **Memory Management**: Generated WAV files are stored in a temporary directory created by `tempfile.mkdtemp()`. The `MainWindow.closeEvent` triggers `SoundManager.cleanup()` to delete this directory via `shutil.rmtree()`.
- **First-Click Algorithm**: During `place_mines()`, all coordinates within a 1-cell radius of the clicked cell are excluded from the candidate pool before random selection.