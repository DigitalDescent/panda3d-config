# Panda3D Config

> Experimental library. Not suitable for production use.

Configuration utilities for the [Panda3D](https://www.panda3d.org/) game engine. Provides a convenient wrapper around Panda3D's configuration system with support for declaring typed variables, validation, change notifications, and loading/saving user settings from files.

## Features

- **Typed variable declarations** — Declare config variables with explicit types (`bool`, `int`, `double`, `string`) and default values.
- **Validation** — Automatic type validation on set, with support for custom per-variable validators.
- **Change notifications** — Messenger events are sent when variables change, making it easy to react to config updates at runtime.
- **Load/Save** — Read and write configuration files in Panda3D's native format, with optional human-readable descriptions.
- **Restart tracking** — Mark variables that require a restart, so your UI can inform users when a restart is needed.
- **Built-in ShowBase config** — `ShowBaseConfig` provides pre-declared variables for common graphics, window, and audio settings.

## Installation

```bash
pip install panda3d-config
```

### Dependencies

- [panda3d](https://pypi.org/project/panda3d/)
- [panda3d-toolbox](https://pypi.org/project/panda3d-toolbox/)

## Quick Start

### Custom configuration

```python
from panda3d import core as p3d
from panda3d_config import PandaConfig

config = PandaConfig("MyGame")

# Declare variables with type and default value
config.declare_variable("music-volume", "0.8", p3d.ConfigFlags.VT_double)
config.declare_variable("show-hud", "true", p3d.ConfigFlags.VT_bool)
config.declare_variable("difficulty", "1", p3d.ConfigFlags.VT_int, restart_required=True)

# Get and set values
config.set("music-volume", "0.5")
value = config.get("music-volume")  # "0.5"

# Save to file
config.save("settings.config")

# Load from file
config.load("settings.config")
```

### Using ShowBaseConfig

`ShowBaseConfig` comes with pre-declared variables for common Panda3D settings like display mode, window size, fullscreen, anti-aliasing, texture filtering, and audio.

```python
from panda3d_config import ShowBaseConfig

settings = ShowBaseConfig()

# Configure before creating ShowBase
settings.set("win-size", "1920 1080")
settings.set("fullscreen", "true")
settings.set("multisamples", "4")
settings.set("framebuffer-multisample", "true")

# Save user preferences
settings.save("user-settings.config")
```

Changes to `win-size` and `fullscreen` are applied to the window automatically at runtime if ShowBase is already running.

### Custom validation

Define a method named `<variable>_validate` (with hyphens replaced by underscores) on a `PandaConfig` subclass to add custom validation logic:

```python
class GameConfig(PandaConfig):
    def __init__(self):
        super().__init__("GameConfig")
        self.declare_variable("difficulty", "1", p3d.ConfigFlags.VT_int)

    def difficulty_validate(self, value: str) -> bool:
        return int(value) in range(0, 4)
```

### Listening for changes

```python
from direct.showbase.DirectObject import DirectObject

class SettingsUI(DirectObject):
    def __init__(self):
        super().__init__()
        self.accept("music-volume-config-value-changed", self.on_volume_changed)

    def on_volume_changed(self, value: str):
        print(f"Volume changed to {value}")
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.