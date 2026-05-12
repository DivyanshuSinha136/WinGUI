# WinGUI

**Native Win32 GUI for Python — zero middleware, zero dependencies.**

All GUI logic is implemented in NASM x86-64 Assembly (`wingui32.asm`) and compiled to a single DLL (`wingui32.dll`). The Python package is a pure `ctypes` shim: no C extensions, no third-party libraries, no build step on the Python side.

---

## Features

- **Assembly-native performance** — every pixel drawn by Win32 directly, no framework overhead
- **Modern UI out of the box** — ComCtl32 v6 Visual Styles, Segoe UI 10pt ClearType, `#F3F3F3` background, per-monitor DPI awareness
- **Full Unicode support** — pass any Python `str`; the DLL converts UTF-8 → UTF-16LE internally via `MultiByteToWideChar`
- **Two API styles** — high-level OOP (`WinGUI` class) or flat module-level functions, your choice
- **Decorator-based event system** — `@gui.on_command(control_id=1)` with optional notification-code filtering
- **Multiple handlers per control** — register as many callbacks as you need; all fire in registration order
- **Context manager support** — `with WinGUI() as gui:` frees GDI handles automatically
- **No Python dependencies** — only the standard library (`ctypes`, `threading`, `traceback`)

---

## Platform

**Windows x86-64 only.** Importing on any other platform raises `ImportError`.

---

## Requirements

| Tool | Purpose |
|---|---|
| Python 3.10+ | Type hints use `type[X]` syntax |
| NASM | Assemble `wingui32.asm` → `wingui32.obj` |
| GCC (MinGW-w64) **or** MSVC | Link `wingui32.obj` → `wingui32.dll` |

---

## Building the DLL

The Python package requires `wingui32.dll` (or the legacy `wingui2.dll`) placed in the same directory as `wingui.py`.

### MSYS2 / MinGW-w64

```sh
nasm -f win64 wingui32.asm -o wingui32.obj
gcc  -shared -o wingui32.dll wingui32.obj \
     -luser32 -lkernel32 -lgdi32 -lcomctl32
```

### MSVC

```bat
nasm -f win64 wingui32.asm -o wingui32.obj
link /DLL /OUT:wingui32.dll ^
     /EXPORT:create_window  /EXPORT:show_window      ^
     /EXPORT:run_message_loop /EXPORT:create_button  ^
     /EXPORT:create_label   /EXPORT:create_textbox   ^
     /EXPORT:set_window_title /EXPORT:show_message_box ^
     /EXPORT:close_window   /EXPORT:set_callback     ^
     wingui32.obj user32.lib kernel32.lib gdi32.lib comctl32.lib
```

Place `wingui32.dll` next to `wingui.py` (or pass an explicit path to `WinGUI(dll_path=...)`).

---

## Installation

No PyPI package yet. Clone the repo and use directly:

```sh
git clone https://github.com/divyanshu-sinha/wingui
cd wingui
# Build the DLL (see above), then:
python example.py
```

---

## Quick Start

### OOP style (recommended)

```python
from wingui import WinGUI

with WinGUI() as gui:
    hwnd = gui.create_window(800, 600, "My App — 你好 🌍")

    gui.create_label  (hwnd, 20, 20,  200, 22, "Enter your name:")
    txt = gui.create_textbox(hwnd, 20, 48,  300, 28)
    gui.create_button (hwnd, 20, 90,  120, 32, "Say Hello", control_id=1)

    @gui.on_command(control_id=1)
    def on_hello(hwnd, ctrl_id, notif, ctrl_hwnd):
        import ctypes
        buf = ctypes.create_unicode_buffer(256)
        ctypes.WinDLL("user32").GetWindowTextW(txt, buf, 256)
        name = buf.value or "stranger"
        gui.show_message_box(f"Hello, {name}! 👋", "Greeting")

    gui.run_message_loop()
```

### Flat API style

```python
import wingui

hwnd = wingui.create_window(640, 400, "Flat API")
wingui.create_button(hwnd, 20, 20, 100, 32, "OK", control_id=1)

@wingui.on_command(control_id=1)
def on_ok(hwnd, ctrl_id, notif, ctrl_hwnd):
    wingui.show_message_box("Done!", "Info")

wingui.run_message_loop()
```

---

## API Reference

### `WinGUI(dll_path=None)`

Main class. Accepts an optional explicit path to `wingui32.dll`; when omitted, the DLL is located automatically next to `wingui.py`.

#### Window lifecycle

| Method | Description |
|---|---|
| `create_window(width, height, title) → int` | Create and show the main window. Returns its HWND. Raises `OSError` on failure. |
| `show_window(hwnd=None)` | Call `ShowWindow` + `UpdateWindow`. Usually unnecessary — `create_window` includes `WS_VISIBLE`. |
| `run_message_loop(threaded=False)` | Enter the Win32 message pump. Blocks until the window closes. Pass `threaded=True` to run on a daemon thread. |
| `close_window(hwnd=None)` | Destroy the window (`DestroyWindow` → `PostQuitMessage`). Also frees the font and background brush GDI handles. |
| `set_window_title(hwnd, title)` | Update the title bar text at runtime. |

#### Control factory

| Method | Description |
|---|---|
| `create_button(parent, x, y, width, height, text, control_id=0) → int` | Themed push-button. Returns HWND. |
| `create_label(parent, x, y, width, height, text) → int` | Read-only STATIC text control. Returns HWND. |
| `create_textbox(parent, x, y, width, height) → int` | Editable single-line EDIT control. Returns HWND. Read/write via `user32.GetWindowTextW` / `SetWindowTextW`. |

All factory methods raise `OSError` (with the Win32 error code) when `CreateWindowExW` returns `NULL`.

#### Dialogs

| Method | Description |
|---|---|
| `show_message_box(text, caption="Info") → int` | Show a modal `MessageBoxW`. Returns the IDOK / IDCANCEL code. |

#### Event system

| Method | Description |
|---|---|
| `on_command(control_id=None, notif=None)` | Decorator factory. Registers a `WM_COMMAND` handler. Both filters are optional (`None` = match any). |
| `set_callback(fn)` | Install a single raw `WM_COMMAND` hook (replaces the decorator system). |

**Handler signature:**

```python
def handler(hwnd: int, ctrl_id: int, notif: int, ctrl_hwnd: int) -> None:
    ...
```

| Parameter | Description |
|---|---|
| `hwnd` | Parent window handle |
| `ctrl_id` | Control identifier (matches `control_id` passed to `create_button`) |
| `notif` | Notification code (`BN_CLICKED = 0` for push-buttons) |
| `ctrl_hwnd` | Child control handle |

#### Context manager

```python
with WinGUI() as gui:
    ...
# __exit__ runs close_window automatically; GDI handles are freed.
```

---

### Flat module API

Every `WinGUI` method is mirrored as a module-level function backed by a lazily-created singleton:

```python
import wingui

wingui.create_window(...)
wingui.create_button(...)
wingui.create_label(...)
wingui.create_textbox(...)
wingui.show_window(...)
wingui.run_message_loop(...)
wingui.set_window_title(...)
wingui.show_message_box(...)
wingui.close_window(...)
wingui.set_callback(...)
wingui.on_command(...)
```

The singleton is stored at `wingui._instance`. Reset it to `None` between independent runs (e.g. in test suites or example galleries).

---

### `CommandCallbackType`

The `ctypes.WINFUNCTYPE` callable type for `WM_COMMAND` callbacks. Useful for type annotations and for passing callbacks to `set_callback` directly.

```python
from wingui import CommandCallbackType

cb: CommandCallbackType = CommandCallbackType(my_handler)
```

> **Important:** Keep a Python reference to every `CommandCallbackType` object for as long as the window is alive. `ctypes` does not prevent garbage collection, and the DLL would hold a dangling function pointer.

---

## Examples

Run the interactive example gallery:

```sh
python example.py
```

The gallery includes 22 self-contained demos:

| # | Demo |
|---|---|
| 01 | Minimal blank window |
| 02 | Custom size and title |
| 03 | Single button + message box |
| 04 | Multiple buttons with unique IDs |
| 05 | Static text labels |
| 06 | Text input (EDIT control) |
| 07 | Multi-field form |
| 08 | Dynamic window title |
| 09 | Message box variations |
| 10 | Counter app (increment / decrement / reset) |
| 11 | Simple calculator |
| 12 | Programmatic window close |
| 13 | Multiple callbacks on one button |
| 14 | Notification-code filtering |
| 15 | Flat module API (no class) |
| 16 | Shared Python state across callbacks |
| 17 | Toggle button (stateful UI) |
| 18 | Full Unicode input and display |
| 19 | Context manager (`with WinGUI() as gui:`) |
| 20 | Live label update at runtime |
| 21 | Simple note-taking app |
| 22 | Raw `set_callback` hook |

---

## ctypes Modifications

Because wingui controls are plain Win32 HWNDs, you can reach into `user32`, `gdi32`, and `kernel32` directly via `ctypes` to do anything the DLL doesn't expose natively. All examples below work inside any `@gui.on_command` handler or anywhere after `create_window` returns.

```python
import ctypes
import ctypes.wintypes as wt

user32  = ctypes.WinDLL("user32")
gdi32   = ctypes.WinDLL("gdi32")
kernel32 = ctypes.WinDLL("kernel32")
```

---

### Reading and writing control text

`create_textbox` and `create_label` both return a raw HWND. Use `GetWindowTextW` / `SetWindowTextW` to read and write their content at any time.

```python
# Read from a textbox or label
buf = ctypes.create_unicode_buffer(512)
user32.GetWindowTextW(txt_hwnd, buf, 512)
value = buf.value           # Python str, full Unicode

# Write to a textbox, label, or button
user32.SetWindowTextW(txt_hwnd, "Hello, 世界!")

# Clear a textbox
user32.SetWindowTextW(txt_hwnd, "")
```

These are the same calls used throughout `example.py`'s `_read()` / `_write()` helpers.

---

### Querying control text length

```python
# Returns the number of characters (not bytes), excluding the null terminator
length = user32.GetWindowTextLengthW(ctrl_hwnd)
buf = ctypes.create_unicode_buffer(length + 1)
user32.GetWindowTextW(ctrl_hwnd, buf, length + 1)
text = buf.value
```

---

### Enabling and disabling controls

```python
# Disable a button (greys it out, ignores clicks)
user32.EnableWindow(btn_hwnd, False)

# Re-enable it
user32.EnableWindow(btn_hwnd, True)
```

Useful for submit buttons that should only be active when a form is complete.

---

### Showing and hiding controls

```python
SW_HIDE = 0
SW_SHOW = 5

user32.ShowWindow(ctrl_hwnd, SW_HIDE)   # hide
user32.ShowWindow(ctrl_hwnd, SW_SHOW)   # show
```

---

### Moving and resizing controls at runtime

`SetWindowPos` repositions and resizes any child control without recreating it.

```python
SWP_NOZORDER   = 0x0004
SWP_NOACTIVATE = 0x0010

user32.SetWindowPos(
    ctrl_hwnd,       # target control
    0,               # hWndInsertAfter (ignored with SWP_NOZORDER)
    new_x, new_y,    # new position in client coords
    new_w, new_h,    # new size
    SWP_NOZORDER | SWP_NOACTIVATE,
)
```

---

### Changing a control's font

The DLL sets Segoe UI 10pt on every control at creation time. You can replace it with any GDI font.

```python
# Create a bold 14pt Segoe UI font
LOGPIXELSY    = 90
FW_BOLD       = 700
DEFAULT_CHARSET = 1
OUT_DEFAULT_PRECIS = 0
CLIP_DEFAULT_PRECIS = 0
CLEARTYPE_QUALITY = 5
DEFAULT_PITCH = 0
FF_SWISS      = 32

hfont = gdi32.CreateFontW(
    -14,              # height (negative = character height in points)
    0,                # width (0 = auto)
    0, 0,             # escapement, orientation
    FW_BOLD,          # weight
    False, False, False,          # italic, underline, strikeout
    DEFAULT_CHARSET,
    OUT_DEFAULT_PRECIS,
    CLIP_DEFAULT_PRECIS,
    CLEARTYPE_QUALITY,
    DEFAULT_PITCH | FF_SWISS,
    "Segoe UI",
)

WM_SETFONT = 0x0030
user32.SendMessageW(ctrl_hwnd, WM_SETFONT, hfont, True)

# Delete the font handle when the window closes to avoid a GDI leak
gdi32.DeleteObject(hfont)
```

---

### Reading keyboard focus

```python
focused_hwnd = user32.GetFocus()
```

Returns the HWND of the control that currently has keyboard focus, or `0` if none (or focus is in another thread/process).

---

### Sending a synthetic button click

You can programmatically trigger a button as if the user clicked it:

```python
BM_CLICK = 0x00F5
user32.SendMessageW(btn_hwnd, BM_CLICK, 0, 0)
```

This fires `WM_COMMAND` / `BN_CLICKED` on the parent window, so all registered `@on_command` handlers run normally.

---

### Setting an EDIT control's selection

```python
EM_SETSEL = 0x00B1

# Select all text
user32.SendMessageW(txt_hwnd, EM_SETSEL, 0, -1)

# Deselect (move caret to end)
user32.SendMessageW(txt_hwnd, EM_SETSEL, -1, 0)

# Select characters 3–7
user32.SendMessageW(txt_hwnd, EM_SETSEL, 3, 7)
```

---

### Setting a password mask on a textbox

```python
EM_SETPASSWORDCHAR = 0x00CC

# Show bullets instead of characters
user32.SendMessageW(txt_hwnd, EM_SETPASSWORDCHAR, ord("•"), 0)

# Force a repaint so the mask takes effect immediately
user32.InvalidateRect(txt_hwnd, None, True)

# Remove the mask
user32.SendMessageW(txt_hwnd, EM_SETPASSWORDCHAR, 0, 0)
user32.InvalidateRect(txt_hwnd, None, True)
```

---

### Limiting input length on a textbox

```python
EM_SETLIMITTEXT = 0x00C5

# Allow at most 32 characters
user32.SendMessageW(txt_hwnd, EM_SETLIMITTEXT, 32, 0)
```

---

### Getting and setting the window rectangle

```python
class RECT(ctypes.Structure):
    _fields_ = [
        ("left",   ctypes.c_long),
        ("top",    ctypes.c_long),
        ("right",  ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

rect = RECT()

# Screen coordinates of the window frame
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(rect.left, rect.top, rect.right, rect.bottom)

# Client area size (excludes title bar and borders)
user32.GetClientRect(hwnd, ctypes.byref(rect))
print(f"Client area: {rect.right} × {rect.bottom}")
```

---

### Centering the window on screen

```python
SM_CXSCREEN = 0
SM_CYSCREEN = 1

screen_w = user32.GetSystemMetrics(SM_CXSCREEN)
screen_h = user32.GetSystemMetrics(SM_CYSCREEN)

rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
win_w = rect.right  - rect.left
win_h = rect.bottom - rect.top

x = (screen_w - win_w) // 2
y = (screen_h - win_h) // 2

SWP_NOSIZE     = 0x0001
SWP_NOZORDER   = 0x0004
SWP_NOACTIVATE = 0x0010

user32.SetWindowPos(hwnd, 0, x, y, 0, 0,
                    SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)
```

---

### Flashing the taskbar button

```python
class FLASHWINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize",    ctypes.c_uint),
        ("hwnd",      ctypes.c_size_t),
        ("dwFlags",   ctypes.c_uint),
        ("uCount",    ctypes.c_uint),
        ("dwTimeout", ctypes.c_uint),
    ]

FLASHW_ALL        = 0x00000003
FLASHW_TIMERNOFG  = 0x0000000C

fwi = FLASHWINFO(
    cbSize   = ctypes.sizeof(FLASHWINFO),
    hwnd     = hwnd,
    dwFlags  = FLASHW_ALL | FLASHW_TIMERNOFG,
    uCount   = 5,       # flash 5 times
    dwTimeout= 0,       # default cursor blink rate
)
user32.FlashWindowEx(ctypes.byref(fwi))
```

---

### Putting it all together — a live character counter

```python
from wingui import WinGUI
import ctypes

user32 = ctypes.WinDLL("user32")

with WinGUI() as gui:
    hwnd = gui.create_window(460, 200, "Character Counter")

    gui.create_label(hwnd, 20, 20, 200, 22, "Type below (max 50 chars):")
    txt = gui.create_textbox(hwnd, 20, 48, 420, 28)
    lbl = gui.create_label(hwnd, 20, 90, 420, 22, "0 / 50 characters")
    gui.create_button(hwnd, 175, 130, 110, 35, "Submit", control_id=1)

    # Limit input to 50 characters
    EM_SETLIMITTEXT = 0x00C5
    user32.SendMessageW(txt, EM_SETLIMITTEXT, 50, 0)

    @gui.on_command(control_id=1)
    def on_submit(hwnd, ctrl_id, notif, ctrl_hwnd):
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(txt, buf, 512)
        text = buf.value
        n = len(text)
        user32.SetWindowTextW(lbl, f"{n} / 50 characters")
        gui.show_message_box(f'Submitted ({n} chars):\n\n"{text}"', "Done")

    gui.run_message_loop()
```

---

## Architecture

```
wingui32.asm          NASM x86-64 Assembly source
    │
    │  nasm + gcc/link
    ▼
wingui32.dll          Native Win32 DLL (all GUI logic)
    │
    │  ctypes shim (wingui.py)
    ▼
WinGUI / flat API     Python interface
```

The DLL performs one-time initialisation on the first `create_window` call:

- `SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)` — loaded via `GetProcAddress` for compatibility with Windows < 1703
- `InitCommonControlsEx(ICC_STANDARD_CLASSES)` — enables ComCtl32 v6 visual styles
- `CreateFontW("Segoe UI", -13, ClearType)` — sent to every control via `WM_SETFONT`
- `CreateSolidBrush(0x00F3F3F3)` — window background

All string parameters flow as UTF-8 `const char*` into the DLL, which converts them to UTF-16LE via `MultiByteToWideChar(CP_UTF8)` before any Win32 Wide-API call. Full Unicode — emoji, CJK, Arabic, RTL scripts — is supported end-to-end.

HWND values are typed as `c_size_t` (not `c_void_p`) to ensure ctypes always returns a plain `int`. `c_void_p` returns `None` for a zero handle, which breaks validity checks; `c_size_t` returns `0`, which is unambiguous.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `FileNotFoundError: wingui32.dll not found` | DLL not built yet | Run the NASM + GCC build commands above |
| `OSError: create_window failed — Win32 error 1400` | Invalid HWND | Rebuild the DLL; ensure `-lgdi32 -lcomctl32` are linked |
| `OSError: create_label failed — Win32 error 1407` | Wrong `hInstance` in DLL | Use the v3.3 source; earlier versions passed the DLL handle for system control classes |
| Window appears but controls are invisible | ComCtl32 v6 not activated | Ensure the DLL links `-lcomctl32` and calls `InitCommonControlsEx` |
| Crash after closing window | Callback GC'd prematurely | Store every `CommandCallbackType` object on a Python variable with window lifetime |
| `ImportError` on non-Windows | Expected | wingui is Windows-only |

---

## Project Structure

```
wingui/
├── wingui32.asm      Assembly source (build this to produce the DLL)
├── wingui.py         Python ctypes shim + WinGUI class + flat API
├── __init__.py       Package init — re-exports the public API
├── example.py        Interactive example gallery (22 demos)
└── README.md
```

---

## License

LGPL v3+. See `LICENSE` for the full text.

---

## Author

**Divyanshu Sinha** — divyanshu.sinha631@gmail.com
