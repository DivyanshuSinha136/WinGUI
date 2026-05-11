"""
examples.py — WinGUI Example Gallery
=====================================
Showcases every feature of the wingui wrapper.

Run:
    python examples.py

An interactive console menu lets you pick any example.
Close the window to return to the menu.

Requires wingui32.dll built from wingui32.asm:
    nasm -f win64 wingui32.asm -o wingui32.obj
    gcc  -shared -o wingui32.dll wingui32.obj -luser32 -lkernel32 -lgdi32 -lcomctl32
"""

import ctypes
import sys
import os

# Make sure wingui.py is importable from the same directory as this file
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wingui import WinGUI

# ---------------------------------------------------------------------------
# Win32 helpers used across examples
# ---------------------------------------------------------------------------
_user32 = ctypes.WinDLL("user32")

def _read(hwnd: int) -> str:
    """Read UTF-16 text from any Win32 control (EDIT, STATIC, BUTTON …)."""
    buf = ctypes.create_unicode_buffer(512)
    _user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value

def _write(hwnd: int, text: str) -> None:
    """Write text to any Win32 control via SetWindowTextW."""
    _user32.SetWindowTextW(hwnd, text)

# ===========================================================================
# Example 01 — Minimal blank window
# ===========================================================================

def example_01_minimal_window():
    """Open a 400 × 300 blank window. The simplest possible WinGUI program."""
    gui  = WinGUI()
    hwnd = gui.create_window(400, 300, "Example 01 — Minimal Window")
    gui.run_message_loop()


# ===========================================================================
# Example 02 — Custom size and title
# ===========================================================================

def example_02_custom_size_title():
    """Wide window (900 × 200) with a long descriptive title."""
    gui = WinGUI()
    gui.create_window(900, 200, "Example 02 — Wide Window  (900 × 200 pixels)")
    gui.run_message_loop()


# ===========================================================================
# Example 03 — Single button with message box
# ===========================================================================

def example_03_single_button():
    """One button — clicking it shows a message box."""
    gui  = WinGUI()
    hwnd = gui.create_window(400, 200, "Example 03 — Single Button")

    gui.create_button(hwnd, x=150, y=80, width=100, height=35,
                      text="Click Me", control_id=1)

    @gui.on_command(control_id=1)
    def on_click(hwnd, ctrl_id, notif, ctrl_hwnd):
        gui.show_message_box("You clicked the button!", "Hello")

    gui.run_message_loop()


# ===========================================================================
# Example 04 — Multiple buttons, unique IDs
# ===========================================================================

def example_04_multiple_buttons():
    """Three colour buttons — a catch-all handler dispatches by ctrl_id."""
    gui  = WinGUI()
    hwnd = gui.create_window(420, 200, "Example 04 — Multiple Buttons")

    gui.create_button(hwnd,  20, 80, 110, 35, "Red",   control_id=1)
    gui.create_button(hwnd, 155, 80, 110, 35, "Green", control_id=2)
    gui.create_button(hwnd, 290, 80, 110, 35, "Blue",  control_id=3)

    colours = {1: "Red 🔴", 2: "Green 🟢", 3: "Blue 🔵"}

    @gui.on_command()                    # no control_id → catches ALL buttons
    def on_any(hwnd, ctrl_id, notif, ctrl_hwnd):
        name = colours.get(ctrl_id, f"Unknown (id={ctrl_id})")
        gui.show_message_box(f"You chose: {name}", "Colour Picker")

    gui.run_message_loop()


# ===========================================================================
# Example 05 — Static text labels
# ===========================================================================

def example_05_labels():
    """Six labels at various positions demonstrating STATIC text controls."""
    gui  = WinGUI()
    hwnd = gui.create_window(440, 320, "Example 05 — Labels")

    gui.create_label(hwnd,  20,  20, 400, 22, "This is a label at the top.")
    gui.create_label(hwnd,  20,  60, 400, 22, "Labels use the Win32 STATIC class.")
    gui.create_label(hwnd,  20, 100, 400, 22, "They render with Segoe UI and modern colours.")
    gui.create_label(hwnd,  20, 140, 200, 22, "Left column")
    gui.create_label(hwnd, 230, 140, 190, 22, "Right column")
    gui.create_label(hwnd,  20, 240, 400, 22, "Unicode: 你好 • مرحبا • こんにちは • 🌍")

    gui.run_message_loop()


# ===========================================================================
# Example 06 — Text input (EDIT control)
# ===========================================================================

def example_06_textbox():
    """Read text from an EDIT control when Submit is clicked."""
    gui  = WinGUI()
    hwnd = gui.create_window(440, 220, "Example 06 — Text Input")

    gui.create_label  (hwnd,  20,  20, 400, 22, "Type something and press Submit:")
    txt = gui.create_textbox(hwnd, 20, 50, 400, 28)
    gui.create_button (hwnd, 160, 96, 110, 35, "Submit", control_id=1)

    @gui.on_command(control_id=1)
    def on_submit(hwnd, ctrl_id, notif, ctrl_hwnd):
        text = _read(txt)
        if text:
            gui.show_message_box(f'You typed:\n\n"{text}"', "Input Received")
        else:
            gui.show_message_box("The text box is empty!", "Notice")

    gui.run_message_loop()


# ===========================================================================
# Example 07 — Multi-field form
# ===========================================================================

def example_07_form():
    """Name / Last Name / Email form — Submit prints all values."""
    gui  = WinGUI()
    hwnd = gui.create_window(480, 320, "Example 07 — Simple Form")

    fields = [
        ("First Name:",  30),
        ("Last Name:",   90),
        ("Email:",      150),
    ]
    textboxes = []

    for label_text, y in fields:
        gui.create_label  (hwnd,  20, y,      130, 22, label_text)
        tb = gui.create_textbox(hwnd, 160, y+2, 300, 26)
        textboxes.append(tb)

    gui.create_button(hwnd, 180, 230, 120, 35, "Submit", control_id=1)

    @gui.on_command(control_id=1)
    def on_submit(hwnd, ctrl_id, notif, ctrl_hwnd):
        first, last, email = [_read(tb) for tb in textboxes]
        msg = (
            f"First Name : {first  or '(empty)'}\n"
            f"Last Name  : {last   or '(empty)'}\n"
            f"Email      : {email  or '(empty)'}"
        )
        gui.show_message_box(msg, "Form Data")

    gui.run_message_loop()


# ===========================================================================
# Example 08 — Dynamic window title
# ===========================================================================

def example_08_dynamic_title():
    """Each click appends the click count to the title bar."""
    gui   = WinGUI()
    hwnd  = gui.create_window(420, 200, "Example 08 — Click to update title")
    count = [0]

    gui.create_label (hwnd, 20, 20, 380, 22,
                      "Each click updates the title bar counter.")
    gui.create_button(hwnd, 155, 80, 110, 35, "Click", control_id=1)

    @gui.on_command(control_id=1)
    def on_click(hwnd, ctrl_id, notif, ctrl_hwnd):
        count[0] += 1
        gui.set_window_title(hwnd, f"Example 08 — Clicked {count[0]} time(s)")

    gui.run_message_loop()


# ===========================================================================
# Example 09 — Message box variations
# ===========================================================================

def example_09_message_boxes():
    """Three buttons — greeting, warning, and long multi-line message box."""
    gui  = WinGUI()
    hwnd = gui.create_window(440, 220, "Example 09 — Message Box Variations")

    gui.create_label (hwnd, 20, 20, 400, 22, "Choose a message box style:")
    gui.create_button(hwnd,  20, 60, 120, 35, "Greeting",  control_id=1)
    gui.create_button(hwnd, 160, 60, 120, 35, "Warning",   control_id=2)
    gui.create_button(hwnd, 300, 60, 120, 35, "Long Text", control_id=3)

    messages = {
        1: ("Hello! Welcome to WinGUI.", "Greeting"),
        2: ("Something might be wrong.\nProceed with caution.", "Warning"),
        3: ("This is a longer message.\n\n"
            "It spans multiple lines.\n\n"
            "Message boxes resize to fit content.\n\n"
            "Full Unicode: 🎉 你好 مرحبا\n\n"
            "Click OK to close.", "Information"),
    }

    @gui.on_command()
    def on_btn(hwnd, ctrl_id, notif, ctrl_hwnd):
        if ctrl_id in messages:
            text, caption = messages[ctrl_id]
            gui.show_message_box(text, caption)

    gui.run_message_loop()


# ===========================================================================
# Example 10 — Counter app (increment / decrement / reset)
# ===========================================================================

def example_10_counter():
    """Live counter displayed in the title bar — three control buttons."""
    gui     = WinGUI()
    hwnd    = gui.create_window(420, 200, "Counter: 0")
    counter = [0]

    gui.create_label (hwnd,  20, 20, 380, 22,
                      "Use the buttons to change the counter (shown in title bar).")
    gui.create_button(hwnd,  20, 80, 110, 35, "− Decrement", control_id=1)
    gui.create_button(hwnd, 155, 80, 110, 35, "Reset",       control_id=2)
    gui.create_button(hwnd, 290, 80, 110, 35, "+ Increment", control_id=3)

    def refresh():
        gui.set_window_title(hwnd, f"Counter: {counter[0]}")

    @gui.on_command(control_id=1)
    def on_dec(hwnd, ctrl_id, notif, ctrl_hwnd):
        counter[0] -= 1;  refresh()

    @gui.on_command(control_id=2)
    def on_reset(hwnd, ctrl_id, notif, ctrl_hwnd):
        counter[0] = 0;   refresh()

    @gui.on_command(control_id=3)
    def on_inc(hwnd, ctrl_id, notif, ctrl_hwnd):
        counter[0] += 1;  refresh()

    gui.run_message_loop()


# ===========================================================================
# Example 11 — Simple calculator
# ===========================================================================

def example_11_calculator():
    """Two number inputs and four operator buttons — result shown in a textbox."""
    gui  = WinGUI()
    hwnd = gui.create_window(480, 260, "Example 11 — Calculator")

    gui.create_label(hwnd,  20, 20,  70, 22, "Number A:")
    tb_a = gui.create_textbox(hwnd,  95, 20, 120, 26)

    gui.create_label(hwnd, 250, 20,  70, 22, "Number B:")
    tb_b = gui.create_textbox(hwnd, 325, 20, 120, 26)

    ops = [("+", 1), ("−", 2), ("×", 3), ("÷", 4)]
    for i, (sym, cid) in enumerate(ops):
        gui.create_button(hwnd, 20 + i * 110, 68, 95, 35, sym, control_id=cid)

    gui.create_label(hwnd,  20, 130, 70, 22, "Result:")
    tb_result = gui.create_textbox(hwnd, 95, 130, 350, 26)

    @gui.on_command()
    def on_op(hwnd, ctrl_id, notif, ctrl_hwnd):
        if ctrl_id not in (1, 2, 3, 4):
            return
        try:
            a = float(_read(tb_a))
            b = float(_read(tb_b))
        except ValueError:
            _write(tb_result, "Error: enter valid numbers")
            return

        if   ctrl_id == 1: result = a + b
        elif ctrl_id == 2: result = a - b
        elif ctrl_id == 3: result = a * b
        elif ctrl_id == 4:
            if b == 0:
                _write(tb_result, "Error: division by zero")
                return
            result = a / b

        text = str(int(result)) if result == int(result) else f"{result:.6g}"
        _write(tb_result, text)

    gui.run_message_loop()


# ===========================================================================
# Example 12 — Programmatic window close
# ===========================================================================

def example_12_close_programmatically():
    """A Quit button calls gui.close_window() — exits the message loop cleanly."""
    gui  = WinGUI()
    hwnd = gui.create_window(400, 180, "Example 12 — Programmatic Close")

    gui.create_label (hwnd, 20, 20, 360, 22,
                      "Press Quit to close the window from code.")
    gui.create_button(hwnd, 150, 80, 100, 35, "Quit", control_id=1)

    @gui.on_command(control_id=1)
    def on_quit(hwnd, ctrl_id, notif, ctrl_hwnd):
        gui.close_window(hwnd)

    gui.run_message_loop()
    print("  [example 12] Window closed by Quit button.")


# ===========================================================================
# Example 13 — Multiple callbacks on one button
# ===========================================================================

def example_13_multiple_callbacks():
    """Two @on_command handlers registered for the same control_id — both fire."""
    gui  = WinGUI()
    hwnd = gui.create_window(440, 200, "Example 13 — Multiple Callbacks")
    log  = []

    gui.create_label (hwnd, 20, 20, 400, 22,
                      "Two handlers are registered for button 1.")
    gui.create_button(hwnd, 165, 80, 110, 35, "Click", control_id=1)

    @gui.on_command(control_id=1)
    def handler_a(hwnd, ctrl_id, notif, ctrl_hwnd):
        log.append("Handler A fired")

    @gui.on_command(control_id=1)
    def handler_b(hwnd, ctrl_id, notif, ctrl_hwnd):
        log.append("Handler B fired")
        gui.show_message_box("\n".join(log), "Event Log")

    gui.run_message_loop()


# ===========================================================================
# Example 14 — Notification-code filtering
# ===========================================================================

def example_14_notif_filtering():
    """Handler fires ONLY for BN_CLICKED (notif=0) — focus events ignored."""
    BN_CLICKED = 0

    gui  = WinGUI()
    hwnd = gui.create_window(440, 200, "Example 14 — Notification Filtering")

    gui.create_label (hwnd, 20, 20, 400, 44,
                      "Handler fires ONLY for BN_CLICKED (notif=0).\n"
                      "Other notification codes are silently ignored.")
    gui.create_button(hwnd, 160, 100, 120, 35, "Click Me", control_id=1)

    @gui.on_command(control_id=1, notif=BN_CLICKED)
    def on_clicked(hwnd, ctrl_id, notif, ctrl_hwnd):
        gui.show_message_box(
            f"Button clicked!\nctrl_id={ctrl_id}  notif={notif}",
            "Filtered Handler"
        )

    gui.run_message_loop()


# ===========================================================================
# Example 15 — Flat module API (no class instance)
# ===========================================================================

def example_15_flat_api():
    """Uses module-level wingui functions instead of the WinGUI class."""
    import wingui   # flat API

    hwnd = wingui.create_window(420, 180, "Example 15 — Flat Module API")

    wingui.create_label (hwnd, 20, 20, 380, 22,
                         "This example uses wingui.create_window() directly.")
    wingui.create_button(hwnd, 155, 80, 110, 35, "OK", control_id=1)

    @wingui.on_command(control_id=1)
    def on_ok(hwnd, ctrl_id, notif, ctrl_hwnd):
        wingui.show_message_box("Flat API works!", "Success")

    wingui.run_message_loop()

    # Reset the singleton so subsequent examples work independently
    import wingui as _w
    _w._instance = None


# ===========================================================================
# Example 16 — Shared Python state across callbacks
# ===========================================================================

def example_16_shared_state():
    """Type words into a textbox, accumulate in a list, display history."""
    gui     = WinGUI()
    hwnd    = gui.create_window(480, 220, "Example 16 — Shared State")
    history = []

    gui.create_label  (hwnd,  20,  20, 440, 22,
                       "Type a word and press Add. Then press Show History.")
    txt = gui.create_textbox(hwnd, 20,  50, 320, 28)
    gui.create_button (hwnd, 350,  48, 110, 30, "Add",          control_id=1)
    gui.create_button (hwnd, 165, 110, 150, 35, "Show History", control_id=2)

    @gui.on_command(control_id=1)
    def on_add(hwnd, ctrl_id, notif, ctrl_hwnd):
        word = _read(txt).strip()
        if word:
            history.append(word)
            _write(txt, "")        # clear after adding

    @gui.on_command(control_id=2)
    def on_show(hwnd, ctrl_id, notif, ctrl_hwnd):
        if history:
            gui.show_message_box(
                "\n".join(f"{i+1}. {w}" for i, w in enumerate(history)),
                f"History ({len(history)} item(s))"
            )
        else:
            gui.show_message_box("No items added yet.", "History")

    gui.run_message_loop()


# ===========================================================================
# Example 17 — Toggle button (stateful UI)
# ===========================================================================

def example_17_toggle():
    """Button label flips OFF ↔ ON ✓ on each click; title bar syncs."""
    gui   = WinGUI()
    hwnd  = gui.create_window(320, 180, "Example 17 — Toggle")
    state = [False]

    gui.create_label(hwnd, 20, 20, 280, 22, "Toggle the button on and off:")
    btn = gui.create_button(hwnd, 95, 80, 130, 35, "OFF", control_id=1)

    @gui.on_command(control_id=1)
    def on_toggle(hwnd, ctrl_id, notif, ctrl_hwnd):
        state[0] = not state[0]
        label = "ON  ✓" if state[0] else "OFF"
        _write(btn, label)
        gui.set_window_title(hwnd, f"Example 17 — Toggle ({label.strip()})")

    gui.run_message_loop()


# ===========================================================================
# Example 18 — Unicode input and display
# ===========================================================================

def example_18_unicode():
    """Demonstrates full Unicode: CJK, Arabic, emoji in labels and textboxes."""
    gui  = WinGUI()
    hwnd = gui.create_window(520, 320, "Example 18 — Unicode  🌍")

    gui.create_label(hwnd, 20,  20, 480, 22, "Chinese:    你好，世界！")
    gui.create_label(hwnd, 20,  52, 480, 22, "Arabic:     مرحبا بالعالم")
    gui.create_label(hwnd, 20,  84, 480, 22, "Japanese:   こんにちは世界")
    gui.create_label(hwnd, 20, 116, 480, 22, "Emoji:      🎉 🚀 🌟 🎨 🏆")
    gui.create_label(hwnd, 20, 160, 480, 22, "Type any Unicode text below:")

    txt = gui.create_textbox(hwnd, 20, 188, 480, 28)
    gui.create_button(hwnd, 195, 232, 130, 35, "Show Text", control_id=1)

    @gui.on_command(control_id=1)
    def on_show(hwnd, ctrl_id, notif, ctrl_hwnd):
        text = _read(txt) or "(empty)"
        gui.show_message_box(text, "Your Input")

    gui.run_message_loop()


# ===========================================================================
# Example 19 — Context manager (with WinGUI as gui)
# ===========================================================================

def example_19_context_manager():
    """Demonstrates automatic cleanup via the context manager protocol."""
    with WinGUI() as gui:
        hwnd = gui.create_window(440, 200,
                                 "Example 19 — Context Manager")

        gui.create_label (hwnd, 20, 20, 400, 44,
                          "This window uses 'with WinGUI() as gui:'.\n"
                          "GDI resources are freed automatically on exit.")
        gui.create_button(hwnd, 155, 110, 130, 35, "Close Cleanly",
                          control_id=1)

        @gui.on_command(control_id=1)
        def on_close(hwnd, ctrl_id, notif, ctrl_hwnd):
            gui.close_window(hwnd)

        gui.run_message_loop()
    # __exit__ runs here — font + brush handles freed automatically


# ===========================================================================
# Example 20 — Live label update
# ===========================================================================

def example_20_live_label():
    """Textbox + button that rewrites a label's text at runtime."""
    gui  = WinGUI()
    hwnd = gui.create_window(480, 240, "Example 20 — Live Label Update")

    gui.create_label(hwnd, 20, 20, 440, 22, "Type text and press Update:")
    txt = gui.create_textbox(hwnd, 20, 50, 440, 28)

    gui.create_label(hwnd, 20, 100, 100, 22, "Live:")
    lbl = gui.create_label(hwnd, 130, 100, 330, 22, "(nothing yet)")

    gui.create_button(hwnd, 175, 148, 130, 35, "Update Label", control_id=1)

    @gui.on_command(control_id=1)
    def on_update(hwnd, ctrl_id, notif, ctrl_hwnd):
        text = _read(txt) or "(empty)"
        _write(lbl, text)

    gui.run_message_loop()


# ===========================================================================
# Example 21 — Simple note-taking app
# ===========================================================================

def example_21_notepad():
    """Minimal note-taking app: Add / Clear / Count lines."""
    gui   = WinGUI()
    hwnd  = gui.create_window(500, 300, "Example 21 — Note Taker")
    notes = []

    gui.create_label  (hwnd,  20,  20, 460, 22, "Enter a note:")
    txt = gui.create_textbox(hwnd, 20,  48, 460, 28)

    gui.create_button (hwnd,  20,  92, 110, 32, "Add Note",   control_id=1)
    gui.create_button (hwnd, 145,  92, 110, 32, "Show Notes", control_id=2)
    gui.create_button (hwnd, 270,  92, 110, 32, "Clear All",  control_id=3)
    gui.create_button (hwnd, 395,  92, 85,  32, "Count",      control_id=4)

    gui.create_label(hwnd, 20, 148, 460, 22, "Status:")
    status = gui.create_label(hwnd, 20, 174, 460, 22, "No notes yet.")

    @gui.on_command(control_id=1)
    def on_add(hwnd, ctrl_id, notif, ctrl_hwnd):
        note = _read(txt).strip()
        if note:
            notes.append(note)
            _write(txt, "")
            _write(status, f"{len(notes)} note(s) saved.")

    @gui.on_command(control_id=2)
    def on_show(hwnd, ctrl_id, notif, ctrl_hwnd):
        if notes:
            gui.show_message_box(
                "\n".join(f"{i+1}. {n}" for i, n in enumerate(notes)),
                f"Notes ({len(notes)})"
            )
        else:
            gui.show_message_box("No notes added yet.", "Notes")

    @gui.on_command(control_id=3)
    def on_clear(hwnd, ctrl_id, notif, ctrl_hwnd):
        notes.clear()
        _write(status, "All notes cleared.")

    @gui.on_command(control_id=4)
    def on_count(hwnd, ctrl_id, notif, ctrl_hwnd):
        gui.show_message_box(f"You have {len(notes)} note(s).", "Count")

    gui.run_message_loop()


# ===========================================================================
# Example 22 — set_callback (raw WM_COMMAND hook)
# ===========================================================================

def example_22_raw_callback():
    """Uses gui.set_callback() instead of the @on_command decorator."""
    gui  = WinGUI()
    hwnd = gui.create_window(440, 200, "Example 22 — Raw set_callback")

    gui.create_label (hwnd, 20, 20, 400, 44,
                      "This example uses gui.set_callback() directly.\n"
                      "Every WM_COMMAND event is routed to one function.")
    gui.create_button(hwnd,  20, 110, 110, 35, "Button A", control_id=1)
    gui.create_button(hwnd, 155, 110, 110, 35, "Button B", control_id=2)
    gui.create_button(hwnd, 290, 110, 110, 35, "Button C", control_id=3)

    names = {1: "A", 2: "B", 3: "C"}

    def raw_handler(hwnd, ctrl_id, notif, ctrl_hwnd):
        name = names.get(ctrl_id)
        if name:
            gui.show_message_box(f"Button {name} pressed\n"
                                 f"ctrl_id={ctrl_id}  notif={notif}",
                                 "Raw Callback")

    gui.set_callback(raw_handler)
    gui.run_message_loop()


# ===========================================================================
# Interactive menu
# ===========================================================================

EXAMPLES = [
    ( 1, "Minimal blank window",                    example_01_minimal_window),
    ( 2, "Custom size and title",                   example_02_custom_size_title),
    ( 3, "Single button + message box",             example_03_single_button),
    ( 4, "Multiple buttons with unique IDs",        example_04_multiple_buttons),
    ( 5, "Static text labels",                      example_05_labels),
    ( 6, "Text input (EDIT control)",               example_06_textbox),
    ( 7, "Multi-field form",                        example_07_form),
    ( 8, "Dynamic window title",                    example_08_dynamic_title),
    ( 9, "Message box variations",                  example_09_message_boxes),
    (10, "Counter app (inc / dec / reset)",         example_10_counter),
    (11, "Simple calculator",                       example_11_calculator),
    (12, "Programmatic window close",               example_12_close_programmatically),
    (13, "Multiple callbacks on one button",        example_13_multiple_callbacks),
    (14, "Notification-code filtering",             example_14_notif_filtering),
    (15, "Flat module API (no class)",              example_15_flat_api),
    (16, "Shared Python state in callbacks",        example_16_shared_state),
    (17, "Toggle button (stateful UI)",             example_17_toggle),
    (18, "Unicode input and display",               example_18_unicode),
    (19, "Context manager (with WinGUI as gui:)",   example_19_context_manager),
    (20, "Live label update at runtime",            example_20_live_label),
    (21, "Simple note-taking app",                  example_21_notepad),
    (22, "Raw set_callback hook",                   example_22_raw_callback),
]


def _print_menu() -> None:
    print()
    print("=" * 62)
    print("  WinGUI v3  —  Example Gallery")
    print("=" * 62)
    print()
    for num, title, _ in EXAMPLES:
        print(f"  {num:>2}.  {title}")
    print()
    print("   0.  Exit")
    print()


def main() -> None:
    while True:
        _print_menu()
        try:
            raw = input("  Choose an example (0 to quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if raw == "0":
            print("  Goodbye!")
            break

        try:
            choice = int(raw)
        except ValueError:
            print(f"  '{raw}' is not a number — try again.")
            continue

        entry = next((e for e in EXAMPLES if e[0] == choice), None)
        if entry is None:
            print(f"  No example {choice} — choose 1–{len(EXAMPLES)} or 0.")
            continue

        num, title, fn = entry
        print(f"\n  Running example {num}: {title}")
        print("  (Close the window to return to the menu)\n")
        try:
            fn()
        except Exception as exc:
            print(f"\n  Example {num} raised an exception: {exc}")
            import traceback
            traceback.print_exc()

        print(f"\n  Example {num} finished.")


if __name__ == "__main__":
    main()
