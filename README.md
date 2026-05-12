# WinGUI

**Native Win32 GUI for Python — powered by NASM x86-64 Assembly**

[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Platform: Windows x64](https://img.shields.io/badge/Platform-Windows%20x64-0078D4?logo=windows)](https://www.microsoft.com/windows)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Assembly: NASM](https://img.shields.io/badge/Assembly-NASM%20x86--64-red)](https://nasm.us)

WinGUI is a zero-dependency Python GUI framework that drives the Win32 API directly from hand-written NASM x86-64 Assembly. There is no Tkinter, no Qt, no Electron — just a thin `ctypes` shim over a compiled DLL.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
  - [Build the DLL](#build-the-dll)
  - [Install the package](#install-the-package)
  - [Verify the installation](#verify-the-installation)
- [Quick Start](#quick-start)
  - [OOP Style](#oop-style)
  - [Flat Module API](#flat-module-api)
  - [Context Manager](#context-manager)
- [API Reference](#api-reference)
  - [WinGUI class](#wingui-class)
  - [Flat API](#flat-api)
  - [Callback signature](#callback-signature)
- [Examples](#examples)
  - [01 — Minimal window](#01--minimal-window)
  - [02 — Single button](#02--single-button)
  - [03 — Multiple buttons](#03--multiple-buttons)
  - [04 — Labels](#04--labels)
  - [05 — Text input](#05--text-input)
  - [06 — Multi-field form](#06--multi-field-form)
  - [07 — Dynamic title](#07--dynamic-title)
  - [08 — Counter app](#08--counter-app)
  - [09 — Calculator](#09--calculator)
  - [10 — Toggle button](#10--toggle-button)
  - [11 — Live label update](#11--live-label-update)
  - [12 — Note-taking app](#12--note-taking-app)
  - [13 — Unicode](#13--unicode)
  - [14 — Multiple callbacks](#14--multiple-callbacks)
  - [15 — Notification filtering](#15--notification-filtering)
  - [16 — Shared state](#16--shared-state)
  - [17 — Programmatic close](#17--programmatic-close)
  - [18 — Raw set_callback](#18--raw-set_callback)
- [Running the Example Gallery](#running-the-example-gallery)
- [Diagnostics](#diagnostics)
- [Project Structure](#project-structure)
- [Build Reference](#build-reference)
- [Design Notes](#design-notes)
- [License](#license)

---

## Features

- **Pure Win32** — no third-party GUI runtime required
- **NASM x86-64 Assembly core** — all GUI logic is in `wingui32.asm`; Python is only a caller
- **Modern UI out of the box** — ComCtl32 v6 Visual Styles, Segoe UI 10 pt ClearType, DPI-aware, themed `#F3F3F3` background
- **Full Unicode** — UTF-8 in, UTF-16LE in the DLL via `MultiByteToWideChar`; CJK, Arabic, emoji all work
- **Zero dependencies** — only Python's standard library (`ctypes`) and the compiled DLL
- **Two API styles** — OOP (`WinGUI` class) or flat module functions
- **Context manager** — `with WinGUI() as gui:` frees GDI handles automatically
- **Decorator-based events** — `@gui.on_command(control_id=1)` with optional notification-code filtering
- **Multiple handlers per control** — register as many `@on_command` callbacks as you like on the same ID

---

## Architecture

```
Python script
    │
    │  ctypes (zero-copy, ABI-safe)
    ▼
wingui.py  ─────────────────  pure shim, no GUI logic
    │
    │  LoadLibrary / function pointers
    ▼
wingui32.dll  (NASM x86-64 Assembly)
    │
    │  Win32 API calls (W-variants, UTF-16LE)
    ▼
user32.dll · kernel32.dll · gdi32.dll · comctl32.dll
```

The DLL exposes ten C-callable functions:

| Export | Description |
|--------|-------------|
| `create_window` | Register class, init modern UI, `CreateWindowExW` |
| `show_window` | `ShowWindow` + `UpdateWindow` |
| `run_message_loop` | `GetMessageW` / `TranslateMessage` / `DispatchMessageW` |
| `create_button` | `CreateWindowExW("BUTTON")` + `WM_SETFONT` |
| `create_label` | `CreateWindowExW("STATIC")` + `WM_SETFONT` |
| `create_textbox` | `CreateWindowExW("EDIT")` + `WM_SETFONT` |
| `set_window_title` | `SetWindowTextW` on the main window |
| `show_message_box` | `MessageBoxW` |
| `close_window` | `DestroyWindow` + `PostQuitMessage(0)` + GDI cleanup |
| `set_callback` | Install a `WINFUNCTYPE` pointer for `WM_COMMAND` dispatch |

---

## Requirements

| Component | Minimum version |
|-----------|----------------|
| Windows | 10 (1703+) or Windows 11 |
| Python | 3.10 (64-bit) |
| NASM | 2.15+ (to rebuild the DLL) |
| GCC (MinGW-w64) | 12+ **or** MSVC 2019+ (to link) |

> **Important:** Python and the DLL must both be **64-bit**. A 32-bit Python will fail to load `wingui32.dll`.

---

## Installation

### Build the DLL

The pre-built binary lives in `bin/wingui32.dll`. To rebuild from source:

**MSYS2 / MinGW-w64**

```bash
cd asm
nasm -f win64 wingui32.asm -o wingui32.obj
gcc  -shared -o ../bin/wingui32.dll wingui32.obj \
     -luser32 -lkernel32 -lgdi32 -lcomctl32
```

Or use the included batch file from the project root:

```bat
build.bat
```

**MSVC (Developer Command Prompt)**

```bat
cd asm
nasm -f win64 wingui32.asm -o wingui32.obj
link /DLL /OUT:..\bin\wingui32.dll ^
     /EXPORT:create_window   /EXPORT:show_window        ^
     /EXPORT:run_message_loop /EXPORT:create_button     ^
     /EXPORT:create_label    /EXPORT:create_textbox     ^
     /EXPORT:set_window_title /EXPORT:show_message_box  ^
     /EXPORT:close_window    /EXPORT:set_callback       ^
     wingui32.obj user32.lib kernel32.lib gdi32.lib comctl32.lib
```

### Install the package

Install in editable mode from the project root:

```bash
pip install -e .
```

Or copy the `wingui/` directory and `bin/wingui32.dll` next to your script and use it directly.

### Verify the installation

```bash
python -m wingui --check
```

Expected output:

```
✓  wingui32.dll loaded successfully
   Path: D:\...\bin\wingui32.dll
```

---

## Quick Start

### OOP Style

```python
from wingui import WinGUI
import ctypes

_user32 = ctypes.WinDLL("user32")

def read(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    _user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value

with WinGUI() as gui:
    hwnd = gui.create_window(640, 360, "Hello — 你好 🌍")

    gui.create_label  (hwnd, 20, 20, 300, 22, "Enter your name:")
    txt = gui.create_textbox(hwnd, 20, 50, 300, 28)
    gui.create_button (hwnd, 20, 96, 130, 36, "Say Hello", control_id=1)
    gui.create_button (hwnd, 165, 96, 100, 36, "Quit",      control_id=99)

    @gui.on_command(control_id=1)
    def on_hello(hwnd, ctrl_id, notif, ctrl_hwnd):
        name = read(txt) or "stranger"
        gui.show_message_box(f"Hello, {name}! 👋", "Greeting")

    @gui.on_command(control_id=99)
    def on_quit(hwnd, ctrl_id, notif, ctrl_hwnd):
        gui.close_window(hwnd)

    gui.run_message_loop()
```

### Flat Module API

```python
import wingui

hwnd = wingui.create_window(480, 200, "Flat API Demo")
wingui.create_button(hwnd, 20, 60, 120, 35, "Click Me", control_id=1)

@wingui.on_command(control_id=1)
def on_click(hwnd, ctrl_id, notif, ctrl_hwnd):
    wingui.show_message_box("It works!", "Info")

wingui.run_message_loop()
```

### Context Manager

```python
from wingui import WinGUI

with WinGUI() as gui:
    hwnd = gui.create_window(400, 200, "Context Manager")
    gui.create_button(hwnd, 150, 80, 100, 35, "Close", control_id=1)

    @gui.on_command(control_id=1)
    def on_close(hwnd, ctrl_id, notif, ctrl_hwnd):
        gui.close_window(hwnd)

    gui.run_message_loop()
# __exit__ is called here — font and brush handles are freed automatically
```

---

## API Reference

### `WinGUI` class

#### Constructor

```python
WinGUI(dll_path: str | None = None)
```

Loads `wingui32.dll`. Pass an explicit path or let the loader search next to `wingui.py` and in `../bin/`.

#### Window lifecycle

| Method | Signature | Description |
|--------|-----------|-------------|
| `create_window` | `(width, height, title) -> int` | Create and show the main window. Returns HWND. |
| `show_window` | `(hwnd=None)` | `ShowWindow` + `UpdateWindow`. Usually not needed — `create_window` already shows the window. |
| `run_message_loop` | `(threaded=False)` | Block on the Win32 message pump until the window closes. |
| `close_window` | `(hwnd=None)` | `DestroyWindow` → `PostQuitMessage(0)` + GDI cleanup. |
| `set_window_title` | `(hwnd, title)` | Update the title bar at runtime. |

#### Control creation

All control methods return the child **HWND** as a plain `int`. Pass this value to `user32.GetWindowTextW` / `SetWindowTextW` to read/write content at runtime.

| Method | Signature | Description |
|--------|-----------|-------------|
| `create_button` | `(parent, x, y, width, height, text, control_id=0) -> int` | Push-button. `control_id` appears as `ctrl_id` in callbacks. |
| `create_label` | `(parent, x, y, width, height, text) -> int` | Read-only STATIC control. Text colour `#1A1A1A`, background `#F3F3F3`. |
| `create_textbox` | `(parent, x, y, width, height) -> int` | Single-line EDIT control with `ES_AUTOHSCROLL`. Read/write via Win32 directly. |

#### Dialogs

| Method | Signature | Description |
|--------|-----------|-------------|
| `show_message_box` | `(text, caption="Info") -> int` | Modal `MessageBoxW`. Returns `IDOK=1`, `IDCANCEL=2`, etc. |

#### Event system

```python
@gui.on_command(control_id=None, notif=None)
def handler(hwnd, ctrl_id, notif, ctrl_hwnd):
    ...
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `control_id` | `int \| None` | Filter to one control. `None` catches all controls. |
| `notif` | `int \| None` | Filter to one notification code. `BN_CLICKED = 0` for buttons. `None` passes all codes. |

Multiple decorators on the same `control_id` are allowed and called in registration order. A handler that raises an exception does **not** block the others — the traceback is printed and execution continues.

```python
gui.set_callback(fn)
```

Lower-level alternative: installs a single raw `WM_COMMAND` handler that receives every event. Using `@on_command` is preferred.

#### Context manager

```python
with WinGUI() as gui:
    ...
```

`__exit__` calls `close_window` and frees the Segoe UI font and background brush GDI handles. Exceptions inside the `with` block are never suppressed.

---

### Flat API

Every method on `WinGUI` has a module-level twin that operates on an implicit singleton instance:

```python
import wingui

wingui.create_window(width, height, title)
wingui.show_window(hwnd=None)
wingui.run_message_loop(threaded=False)
wingui.create_button(parent, x, y, w, h, text, control_id=0)
wingui.create_label(parent, x, y, w, h, text)
wingui.create_textbox(parent, x, y, w, h)
wingui.set_window_title(hwnd, title)
wingui.show_message_box(text, caption="Info")
wingui.close_window(hwnd=None)
wingui.set_callback(fn)
wingui.on_command(control_id=None, notif=None)
```

Reset the singleton between independent uses:

```python
import wingui as _w
_w._instance = None
```

---

### Callback signature

```python
def handler(hwnd: int, ctrl_id: int, notif: int, ctrl_hwnd: int) -> None:
    ...
```

| Parameter | Description |
|-----------|-------------|
| `hwnd` | Parent window HWND |
| `ctrl_id` | Control identifier (the `control_id` you passed to `create_button`) |
| `notif` | Notification code — `BN_CLICKED = 0` for button clicks |
| `ctrl_hwnd` | Child control HWND |

The type alias `CommandCallbackType` is exported for annotations:

```python
from wingui import CommandCallbackType

def my_handler(hwnd, ctrl_id, notif, ctrl_hwnd) -> None: ...
cb: CommandCallbackType = CommandCallbackType(my_handler)
```

---

## Examples

All 22 examples are runnable via the gallery:

```bash
python -m wingui --examples
# or
python example.py
```

### Reading and writing control text

Most examples use these two small helpers:

```python
import ctypes
_user32 = ctypes.WinDLL("user32")

def read(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(512)
    _user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value

def write(hwnd: int, text: str) -> None:
    _user32.SetWindowTextW(hwnd, text)
```

---

### 01 — Minimal window

Open a blank window. The simplest possible WinGUI program.

```python
from wingui import WinGUI

gui  = WinGUI()
hwnd = gui.create_window(400, 300, "Minimal Window")
gui.run_message_loop()
```

---

### 02 — Single button

Click the button to show a message box.

```python
from wingui import WinGUI

gui  = WinGUI()
hwnd = gui.create_window(400, 200, "Single Button")
gui.create_button(hwnd, x=150, y=80, width=100, height=35,
                  text="Click Me", control_id=1)

@gui.on_command(control_id=1)
def on_click(hwnd, ctrl_id, notif, ctrl_hwnd):
    gui.show_message_box("You clicked the button!", "Hello")

gui.run_message_loop()
```

---

### 03 — Multiple buttons

Three buttons with a single catch-all handler dispatching by `ctrl_id`.

```python
from wingui import WinGUI

gui  = WinGUI()
hwnd = gui.create_window(420, 200, "Multiple Buttons")

gui.create_button(hwnd,  20, 80, 110, 35, "Red",   control_id=1)
gui.create_button(hwnd, 155, 80, 110, 35, "Green", control_id=2)
gui.create_button(hwnd, 290, 80, 110, 35, "Blue",  control_id=3)

colours = {1: "Red 🔴", 2: "Green 🟢", 3: "Blue 🔵"}

@gui.on_command()   # no control_id → catches ALL buttons
def on_any(hwnd, ctrl_id, notif, ctrl_hwnd):
    name = colours.get(ctrl_id, f"Unknown (id={ctrl_id})")
    gui.show_message_box(f"You chose: {name}", "Colour Picker")

gui.run_message_loop()
```

---

### 04 — Labels

Six STATIC text labels at various positions.

```python
from wingui import WinGUI

gui  = WinGUI()
hwnd = gui.create_window(440, 320, "Labels")

gui.create_label(hwnd,  20,  20, 400, 22, "This is a label at the top.")
gui.create_label(hwnd,  20,  60, 400, 22, "Labels use the Win32 STATIC class.")
gui.create_label(hwnd,  20, 100, 400, 22, "Rendered with Segoe UI and modern colours.")
gui.create_label(hwnd,  20, 140, 200, 22, "Left column")
gui.create_label(hwnd, 230, 140, 190, 22, "Right column")
gui.create_label(hwnd,  20, 240, 400, 22, "Unicode: 你好 • مرحبا • こんにちは • 🌍")

gui.run_message_loop()
```

---

### 05 — Text input

Read from an EDIT control when Submit is clicked.

```python
from wingui import WinGUI
import ctypes

_user32 = ctypes.WinDLL("user32")

def read(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    _user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value

gui  = WinGUI()
hwnd = gui.create_window(440, 220, "Text Input")

gui.create_label  (hwnd,  20,  20, 400, 22, "Type something and press Submit:")
txt = gui.create_textbox(hwnd, 20,  50, 400, 28)
gui.create_button (hwnd, 160,  96, 110, 35, "Submit", control_id=1)

@gui.on_command(control_id=1)
def on_submit(hwnd, ctrl_id, notif, ctrl_hwnd):
    text = read(txt)
    if text:
        gui.show_message_box(f'You typed:\n\n"{text}"', "Input Received")
    else:
        gui.show_message_box("The text box is empty!", "Notice")

gui.run_message_loop()
```

---

### 06 — Multi-field form

Name / Last Name / Email form — Submit prints all values.

```python
from wingui import WinGUI
import ctypes

_user32 = ctypes.WinDLL("user32")

def read(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    _user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value

gui  = WinGUI()
hwnd = gui.create_window(480, 320, "Simple Form")

fields = [("First Name:", 30), ("Last Name:", 90), ("Email:", 150)]
textboxes = []

for label_text, y in fields:
    gui.create_label  (hwnd,  20, y,      130, 22, label_text)
    tb = gui.create_textbox(hwnd, 160, y+2, 300, 26)
    textboxes.append(tb)

gui.create_button(hwnd, 180, 230, 120, 35, "Submit", control_id=1)

@gui.on_command(control_id=1)
def on_submit(hwnd, ctrl_id, notif, ctrl_hwnd):
    first, last, email = [read(tb) for tb in textboxes]
    msg = (
        f"First Name : {first  or '(empty)'}\n"
        f"Last Name  : {last   or '(empty)'}\n"
        f"Email      : {email  or '(empty)'}"
    )
    gui.show_message_box(msg, "Form Data")

gui.run_message_loop()
```

---

### 07 — Dynamic title

Each click appends the click count to the title bar.

```python
from wingui import WinGUI

gui   = WinGUI()
hwnd  = gui.create_window(420, 200, "Click to update title")
count = [0]

gui.create_label (hwnd, 20, 20, 380, 22, "Each click updates the title bar.")
gui.create_button(hwnd, 155, 80, 110, 35, "Click", control_id=1)

@gui.on_command(control_id=1)
def on_click(hwnd, ctrl_id, notif, ctrl_hwnd):
    count[0] += 1
    gui.set_window_title(hwnd, f"Clicked {count[0]} time(s)")

gui.run_message_loop()
```

---

### 08 — Counter app

Increment, decrement, and reset — result shown in the title bar.

```python
from wingui import WinGUI

gui     = WinGUI()
hwnd    = gui.create_window(420, 200, "Counter: 0")
counter = [0]

gui.create_label (hwnd,  20, 20, 380, 22, "Use the buttons to change the counter.")
gui.create_button(hwnd,  20, 80, 110, 35, "− Decrement", control_id=1)
gui.create_button(hwnd, 155, 80, 110, 35, "Reset",       control_id=2)
gui.create_button(hwnd, 290, 80, 110, 35, "+ Increment", control_id=3)

def refresh():
    gui.set_window_title(hwnd, f"Counter: {counter[0]}")

@gui.on_command(control_id=1)
def on_dec(hwnd, ctrl_id, notif, ctrl_hwnd):
    counter[0] -= 1; refresh()

@gui.on_command(control_id=2)
def on_reset(hwnd, ctrl_id, notif, ctrl_hwnd):
    counter[0] = 0; refresh()

@gui.on_command(control_id=3)
def on_inc(hwnd, ctrl_id, notif, ctrl_hwnd):
    counter[0] += 1; refresh()

gui.run_message_loop()
```

---

### 09 — Calculator

Two number inputs, four operator buttons, result in a textbox.

```python
from wingui import WinGUI
import ctypes

_user32 = ctypes.WinDLL("user32")

def read(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    _user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value

def write(hwnd, text):
    _user32.SetWindowTextW(hwnd, text)

gui  = WinGUI()
hwnd = gui.create_window(480, 260, "Calculator")

gui.create_label(hwnd,  20, 20,  70, 22, "Number A:")
tb_a = gui.create_textbox(hwnd,  95, 20, 120, 26)

gui.create_label(hwnd, 250, 20,  70, 22, "Number B:")
tb_b = gui.create_textbox(hwnd, 325, 20, 120, 26)

for i, (sym, cid) in enumerate([("+", 1), ("−", 2), ("×", 3), ("÷", 4)]):
    gui.create_button(hwnd, 20 + i * 110, 68, 95, 35, sym, control_id=cid)

gui.create_label(hwnd,  20, 130, 70, 22, "Result:")
tb_result = gui.create_textbox(hwnd, 95, 130, 350, 26)

@gui.on_command()
def on_op(hwnd, ctrl_id, notif, ctrl_hwnd):
    if ctrl_id not in (1, 2, 3, 4):
        return
    try:
        a, b = float(read(tb_a)), float(read(tb_b))
    except ValueError:
        write(tb_result, "Error: enter valid numbers"); return

    if   ctrl_id == 1: result = a + b
    elif ctrl_id == 2: result = a - b
    elif ctrl_id == 3: result = a * b
    elif ctrl_id == 4:
        if b == 0: write(tb_result, "Error: division by zero"); return
        else: result = a / b

    write(tb_result, str(int(result)) if result == int(result) else f"{result:.6g}")

gui.run_message_loop()
```

---

### 10 — Toggle button

Button label flips between OFF and ON ✓ on each click.

```python
from wingui import WinGUI
import ctypes

_user32 = ctypes.WinDLL("user32")

gui   = WinGUI()
hwnd  = gui.create_window(320, 180, "Toggle")
state = [False]

gui.create_label(hwnd, 20, 20, 280, 22, "Toggle the button on and off:")
btn = gui.create_button(hwnd, 95, 80, 130, 35, "OFF", control_id=1)

@gui.on_command(control_id=1)
def on_toggle(hwnd, ctrl_id, notif, ctrl_hwnd):
    state[0] = not state[0]
    label = "ON  ✓" if state[0] else "OFF"
    _user32.SetWindowTextW(btn, label)
    gui.set_window_title(hwnd, f"Toggle ({label.strip()})")

gui.run_message_loop()
```

---

### 11 — Live label update

Update a label's text at runtime from a textbox.

```python
from wingui import WinGUI
import ctypes

_user32 = ctypes.WinDLL("user32")

def read(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    _user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value

gui  = WinGUI()
hwnd = gui.create_window(480, 240, "Live Label Update")

gui.create_label(hwnd, 20, 20, 440, 22, "Type text and press Update:")
txt = gui.create_textbox(hwnd, 20, 50, 440, 28)
lbl = gui.create_label(hwnd, 20, 100, 440, 22, "(nothing yet)")
gui.create_button(hwnd, 175, 148, 130, 35, "Update Label", control_id=1)

@gui.on_command(control_id=1)
def on_update(hwnd, ctrl_id, notif, ctrl_hwnd):
    text = read(txt) or "(empty)"
    _user32.SetWindowTextW(lbl, text)

gui.run_message_loop()
```

---

### 12 — Note-taking app

Add, view, clear, and count notes — status label updates after each action.

```python
from wingui import WinGUI
import ctypes

_user32 = ctypes.WinDLL("user32")

def read(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    _user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value

gui   = WinGUI()
hwnd  = gui.create_window(500, 300, "Note Taker")
notes = []

gui.create_label(hwnd, 20, 20, 460, 22, "Enter a note:")
txt    = gui.create_textbox(hwnd, 20, 48, 460, 28)
status = gui.create_label  (hwnd, 20, 174, 460, 22, "No notes yet.")

gui.create_button(hwnd,  20, 92, 110, 32, "Add Note",   control_id=1)
gui.create_button(hwnd, 145, 92, 110, 32, "Show Notes", control_id=2)
gui.create_button(hwnd, 270, 92, 110, 32, "Clear All",  control_id=3)
gui.create_button(hwnd, 395, 92,  85, 32, "Count",      control_id=4)

@gui.on_command(control_id=1)
def on_add(hwnd, ctrl_id, notif, ctrl_hwnd):
    note = read(txt).strip()
    if note:
        notes.append(note)
        _user32.SetWindowTextW(txt, "")
        _user32.SetWindowTextW(status, f"{len(notes)} note(s) saved.")

@gui.on_command(control_id=2)
def on_show(hwnd, ctrl_id, notif, ctrl_hwnd):
    body = "\n".join(f"{i+1}. {n}" for i, n in enumerate(notes)) if notes else "No notes added yet."
    gui.show_message_box(body, f"Notes ({len(notes)})")

@gui.on_command(control_id=3)
def on_clear(hwnd, ctrl_id, notif, ctrl_hwnd):
    notes.clear()
    _user32.SetWindowTextW(status, "All notes cleared.")

@gui.on_command(control_id=4)
def on_count(hwnd, ctrl_id, notif, ctrl_hwnd):
    gui.show_message_box(f"You have {len(notes)} note(s).", "Count")

gui.run_message_loop()
```

---

### 13 — Unicode

Full Unicode in labels, textboxes, and message boxes.

```python
from wingui import WinGUI

gui  = WinGUI()
hwnd = gui.create_window(520, 320, "Unicode  🌍")

gui.create_label(hwnd, 20,  20, 480, 22, "Chinese:  你好，世界！")
gui.create_label(hwnd, 20,  52, 480, 22, "Arabic:   مرحبا بالعالم")
gui.create_label(hwnd, 20,  84, 480, 22, "Japanese: こんにちは世界")
gui.create_label(hwnd, 20, 116, 480, 22, "Emoji:    🎉 🚀 🌟 🎨 🏆")
gui.create_label(hwnd, 20, 160, 480, 22, "Type any Unicode text below:")

txt = gui.create_textbox(hwnd, 20, 188, 480, 28)
gui.create_button(hwnd, 195, 232, 130, 35, "Show Text", control_id=1)

@gui.on_command(control_id=1)
def on_show(hwnd, ctrl_id, notif, ctrl_hwnd):
    import ctypes
    buf = ctypes.create_unicode_buffer(512)
    ctypes.WinDLL("user32").GetWindowTextW(txt, buf, 512)
    gui.show_message_box(buf.value or "(empty)", "Your Input")

gui.run_message_loop()
```

---

### 14 — Multiple callbacks

Two `@on_command` handlers registered for the same `control_id` — both fire in order.

```python
from wingui import WinGUI

gui = WinGUI()
hwnd = gui.create_window(440, 200, "Multiple Callbacks")
log  = []

gui.create_label (hwnd, 20, 20, 400, 22, "Two handlers are registered for button 1.")
gui.create_button(hwnd, 165, 80, 110, 35, "Click", control_id=1)

@gui.on_command(control_id=1)
def handler_a(hwnd, ctrl_id, notif, ctrl_hwnd):
    log.append("Handler A fired")

@gui.on_command(control_id=1)
def handler_b(hwnd, ctrl_id, notif, ctrl_hwnd):
    log.append("Handler B fired")
    gui.show_message_box("\n".join(log), "Event Log")

gui.run_message_loop()
```

---

### 15 — Notification filtering

Handler fires **only** for `BN_CLICKED` (`notif=0`) — focus events are silently ignored.

```python
from wingui import WinGUI

BN_CLICKED = 0

gui  = WinGUI()
hwnd = gui.create_window(440, 200, "Notification Filtering")

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
```

---

### 16 — Shared state

Accumulate words from a textbox into a Python list across multiple button clicks.

```python
from wingui import WinGUI
import ctypes

_user32 = ctypes.WinDLL("user32")

def read(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    _user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value

gui     = WinGUI()
hwnd    = gui.create_window(480, 220, "Shared State")
history = []

gui.create_label  (hwnd,  20,  20, 440, 22, "Type a word and press Add.")
txt = gui.create_textbox(hwnd, 20,  50, 320, 28)
gui.create_button (hwnd, 350,  48, 110, 30, "Add",          control_id=1)
gui.create_button (hwnd, 165, 110, 150, 35, "Show History", control_id=2)

@gui.on_command(control_id=1)
def on_add(hwnd, ctrl_id, notif, ctrl_hwnd):
    word = read(txt).strip()
    if word:
        history.append(word)
        _user32.SetWindowTextW(txt, "")

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
```

---

### 17 — Programmatic close

A Quit button calls `gui.close_window()` to exit the message loop cleanly.

```python
from wingui import WinGUI

gui  = WinGUI()
hwnd = gui.create_window(400, 180, "Programmatic Close")

gui.create_label (hwnd, 20, 20, 360, 22, "Press Quit to close from code.")
gui.create_button(hwnd, 150, 80, 100, 35, "Quit", control_id=1)

@gui.on_command(control_id=1)
def on_quit(hwnd, ctrl_id, notif, ctrl_hwnd):
    gui.close_window(hwnd)

gui.run_message_loop()
```

---

### 18 — Raw `set_callback`

Uses `gui.set_callback()` directly instead of `@on_command`. Every `WM_COMMAND` event routes to one function.

```python
from wingui import WinGUI

gui  = WinGUI()
hwnd = gui.create_window(440, 200, "Raw set_callback")

gui.create_label (hwnd, 20, 20, 400, 22, "Uses gui.set_callback() directly.")
gui.create_button(hwnd,  20, 80, 110, 35, "Button A", control_id=1)
gui.create_button(hwnd, 155, 80, 110, 35, "Button B", control_id=2)
gui.create_button(hwnd, 290, 80, 110, 35, "Button C", control_id=3)

names = {1: "A", 2: "B", 3: "C"}

def raw_handler(hwnd, ctrl_id, notif, ctrl_hwnd):
    name = names.get(ctrl_id)
    if name:
        gui.show_message_box(f"Button {name} pressed\nctrl_id={ctrl_id}  notif={notif}",
                             "Raw Callback")

gui.set_callback(raw_handler)
gui.run_message_loop()
```

---

## Running the Example Gallery

The `example.py` file contains all 22 examples with an interactive console menu.

```bash
# Via the package entry point
python -m wingui --examples

# Or directly
python example.py
```

The launcher also provides:

```bash
python -m wingui            # Interactive quick-start menu
python -m wingui --demo     # Run the Hello World demo directly
python -m wingui --check    # Verify DLL is present and loadable
python -m wingui --help     # Show help text
```

---

## Diagnostics

If controls fail to appear, run the diagnostic script before filing a bug:

```bash
python wingui/diag.py
```

`diag.py` patches all control-creation calls to print `GetLastError()` codes before Python raises `OSError`, prints `hInstance` values, and independently tests the `STATIC` window class from Python ctypes. Typical error codes:

| Code | Hex | Meaning |
|------|-----|---------|
| 1400 | `0x00000578` | Invalid parent HWND — DLL and EXE handle mismatch. Rebuild the DLL. |
| 1407 | `0x0000057F` | Cannot find window class — wrong `hInstance` in `RegisterClassExW`. Rebuild. |
| 87   | `0x00000057` | Invalid parameter — stack layout or argument type mismatch. |

---

## Project Structure

```
WinGUI/
├── asm/
│   ├── wingui32.asm        # NASM x86-64 source — all GUI logic
│   └── wingui32.def        # DLL export list (for MSVC link)
├── bin/
│   ├── wingui32.dll        # Pre-built 64-bit DLL
│   └── wingui32.obj        # Object file
├── wingui/
│   ├── wingui.py           # ctypes shim — WinGUI class + flat API
│   ├── __init__.py         # Package init, re-exports public API
│   ├── __main__.py         # python -m wingui entry point
│   ├── diag.py             # Win32 diagnostic tool
│   └── py.typed            # PEP 561 marker
├── example.py              # 22-example interactive gallery
├── build.bat               # One-command DLL rebuild (MSYS2)
├── pyproject.toml
├── LICENSE.txt             # GNU LGPL v3.0
└── README.md
```

---

## Build Reference

### `build.bat`

```bat
@echo off
cd asm
nasm -f win64 wingui32.asm -o wingui32.obj
gcc  -shared -o ..\bin\wingui32.dll wingui32.obj ^
     -luser32 -lkernel32 -lgdi32 -lcomctl32
echo Done.
```

### Key assembly design decisions

**`hInstance` via `GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS, WindowProc)`**
rather than `GetModuleHandleW(NULL)`. The `NULL` form returns the host EXE handle; `RegisterClassExW` must use the DLL's own handle so `CreateWindowExW` can locate the class.

**`hInstance = NULL` for system controls** (`BUTTON`, `EDIT`, `STATIC`).
Passing the DLL handle causes `ERROR_CANNOT_FIND_WND_CLASS (1407)` because these classes are registered against the null/system module.

**`SetProcessDpiAwarenessContext` loaded via `GetProcAddress`** at runtime rather than a static import. Static imports of this symbol fail to load on Windows < 1703 where the function may not exist in `user32.dll`.

**Controls created with `NULL` text, then text set via `SetWindowTextW`** after `CreateWindowExW` returns. This avoids the bug where calling `utf8_to_wchar` before `CreateWindowExW` corrupted the stack frame and caused `ERROR_INVALID_WINDOW_HANDLE (1400)`.

**RSP alignment** strictly maintained throughout. On entry to any function, `RSP mod 16 = 8` (return address just pushed). Shadow space of 32 bytes is always reserved. Stack arguments start at `[rsp+32]`.

---

## License

Copyright © 2026 Divyanshu Sinha

Licensed under the **GNU Lesser General Public License v3.0**.
See [LICENSE.txt](https://github.com/DivyanshuSinha136/WinGUI?tab=LGPL-3.0-1-ov-file) for the full text.

In brief: you may use WinGUI in your own applications (commercial or open-source) without restriction. If you modify `wingui32.asm` or `wingui.py` themselves, you must release those modifications under LGPL v3+.

---

*Made with NASM, Python, and the Win32 API — no frameworks were harmed.*
