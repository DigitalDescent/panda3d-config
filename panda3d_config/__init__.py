"""
Copyright (c) 2026, Digital Descent, LLC. All rights reserved.

config.py:
    PandaConfig: A wrapper around Panda3D's configuration system that allows for end user settings
"""

from panda3d import core as p3d
from panda3d_toolbox import runtime

from direct.showbase.DirectObject import DirectObject

# --------------------------------------------------------------------------------------------------------------- #

WANT_CONFIG_DESCRIPTIONS = p3d.ConfigVariableBool(
    'want-config-descriptions', True, "Whether to include descriptions when saving configuration to a file.")

# --------------------------------------------------------------------------------------------------------------- #


class PandaConfig(DirectObject):
    """
    A wrapper around Panda3D's configuration system that allows for end user management of configuration 
    variables and loading/saving from files. Typically for application settings that may need to be changed by users.
    """

    def __init__(self, name: str = None):
        super().__init__()
        self._name = name if name is not None else self.__class__.__name__
        self._page_mgr = p3d.ConfigPageManager.get_global_ptr()
        self._page = self._page_mgr.make_explicit_page(self._name)
        self._declaration_restart_required = {}
        self._declaration_types = {}
        self._declarations = {}

        self._variable_mgr = p3d.ConfigVariableManager.get_global_ptr()
        self._variables = {}

        for i in range(self._variable_mgr.get_num_variables()):
            var = self._variable_mgr.get_variable(i)
            self._variables[var.get_name()] = var

    @property
    def name(self) -> str:
        """
        Get the name of this configuration.
        """

        return self._name

    def declare_variable(
            self,
            key: str,
            default_value: str,
            value_type: p3d.ConfigFlags.ValueType,
            restart_required: bool = False) -> None:
        """
        Declare a configuration variable with a default value and description.

        Args:
            key: The name of the variable to declare.
            default_value: The default value of the variable as a string.
            value_type: The type of the variable (e.g. VT_bool, VT_int, VT_double, VT_string).
            restart_required: Whether a restart is required for changes to this variable to take effect.
        """

        decl = self._page.make_declaration(key, str(default_value))
        self._declarations[key] = decl
        self._declaration_types[key] = value_type
        self._declaration_restart_required[key] = restart_required

    def set(self, key: str, value: str) -> bool:
        """
        Set a configuration variable.

        Args:
            key: The name of the variable to set.
            value: The value to set the variable to.

        Returns:
            Whether a restart is required for the change to take effect.
        """

        if key not in self._declarations:
            raise KeyError(
                f"Variable '{key}' has not been declared in the configuration.")

        restart_required = self._declaration_restart_required[key]
        value_type = self._declaration_types[key]

        if not self._validate_value(key, value, value_type):
            raise ValueError(
                f"Invalid value '{value}' for variable '{key}' of type '{self._value_type_to_string(value_type)}'.")

        decl = self._declarations[key]
        decl.set_string_value(str(value))
        self._notify_change(key, value)
        return restart_required

    def _value_type_to_string(self, value_type: p3d.ConfigFlags.ValueType) -> str:
        """
        Convert a Panda3D ConfigFlags.ValueType to a human-readable string.

        Args:
            value_type: The value type to convert.

        Returns:
            A string representation of the value type.
        """

        attributes = p3d.ConfigFlags.__dict__
        attribute_name = str(value_type)

        for name, val in attributes.items():
            if val == value_type:
                attribute_name = name
                break

        return attribute_name

    def _validate_value(self, key: str, value: str, value_type: p3d.ConfigFlags.ValueType) -> bool:
        """
        Validate a string value against a Panda3D ConfigVariable type.

        Args:
            key: The name of the variable to validate.
            value: The string value to validate.
            value_type: The expected type of the value.

        Returns:
            Whether the value is valid for the given type.
        """

        try:
            if value_type == p3d.ConfigFlags.VT_bool:
                if type(value) == bool:
                    return True
                if value.lower() not in ['true', 'false', '1', '0']:
                    return False
            elif value_type == p3d.ConfigFlags.VT_int:
                int(value)
            elif value_type == p3d.ConfigFlags.VT_double:
                float(value)
        except ValueError:
            return False

        validate_handler_name = f"{key.replace('-', '_')}_validate"
        if hasattr(self, validate_handler_name):
            validate_handler = getattr(self, validate_handler_name, None)
            if callable(validate_handler):
                return validate_handler(value)

        return True

    def _notify_change(self, key: str, value: str) -> None:
        """
        Notify listeners that a configuration variable has changed.

        Args:
            key: The name of the variable that changed.
            value: The new value of the variable.
        """

        value = str(value)
        change_handler_name = f"{key.replace('-', '_')}_changed"

        if hasattr(self, change_handler_name):
            change_handler = getattr(self, change_handler_name, None)
            if callable(change_handler):
                change_handler(value)

        if not runtime.has_messenger():
            return

        runtime.messenger.send(f"{self._name}-config-changed", [key, value])
        runtime.messenger.send(f"{key}-config-value-changed", [value])

    def get(self, key: str, default: str = None) -> str:
        """
        Get a configuration variable.

        Args:
            key: The name of the variable to get.
            default: The default value to return if the variable is not set.

        Returns:
            The value of the variable, or the default if it is not set.
        """

        if key in self._declarations:
            decl = self._declarations[key]
            return decl.get_string_value()

        return default

    def load(self, filename: str) -> None:
        """
        Load configuration from a file.

        Args:
            filename: The name of the file to load from.
        """

        with open(filename, "r") as f:
            data = f.read()

        lines = data.splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("#") or line == "":
                continue

            if " " not in line:
                continue

            key, value = line.split(" ", 1)
            key = key.strip()
            value = value.strip()

            if key in self._declarations:
                try:
                    self.set(key, value)
                except ValueError:
                    print(
                        f"Warning: Invalid value '{value}' for variable '{key}' in config file '{filename}'. Skipping.")

    def save(self, filename: str) -> None:
        """
        Save the current configuration to a file.

        Args:
            filename: The name of the file to save to.
        """

        stream = p3d.StringStream()
        if not WANT_CONFIG_DESCRIPTIONS.get_value():
            self._page.write(stream)

            with open(filename, "wb") as f:
                f.write(stream.get_data())

            return

        lines = []
        decl_count = self._page.get_num_declarations()
        for i in range(decl_count):
            decl = self._page.get_declaration(i)
            var = decl.get_variable()
            if var is not None and var.get_description() != '':
                description = var.get_description()

                # Wrap long descriptions at 80 characters
                wrapped = '\n# '.join(__import__(
                    'textwrap').wrap(description, width=77))
                lines.append(f"\n# {wrapped}")

            stream.clear_data()
            decl.write(stream)

            decl_line = stream.get_data().decode("utf-8").strip()
            lines.append(decl_line)

        with open(filename, "wb") as f:
            f.write("\n".join(lines).encode("utf-8"))

# --------------------------------------------------------------------------------------------------------------- #


class ShowBaseConfig(PandaConfig):
    """
    A configuration class for settings that need to be applied before ShowBase is initialized. This can be used for
    things like graphics settings that need to be set before the window is created.
    """

    def __init__(self):
        super().__init__(self.__class__.__name__)
        self._declare_variables()

    def _declare_variables(self) -> None:
        """
        Declare all configuration variables for ShowBase.
        """

        self.declare_variable('load-display', self.get_default_display_type(),
                              p3d.ConfigFlags.VT_string, True)
        self.declare_variable('sync-video', False,
                              p3d.ConfigFlags.VT_bool, True)
        self.declare_variable('win-size', '1280 720',
                              p3d.ConfigFlags.VT_string, False)
        self.declare_variable('fullscreen', self.is_console_device(),
                              p3d.ConfigFlags.VT_bool, False)
        self.declare_variable('show-frame-rate-meter', False,
                              p3d.ConfigFlags.VT_bool, False)

        self.declare_variable('multisamples', 0, p3d.ConfigFlags.VT_int, True)
        self.declare_variable('framebuffer-multisample',
                              False, p3d.ConfigFlags.VT_bool, True)

        self.declare_variable('texture-ansisotropic-degree',
                              0, p3d.ConfigFlags.VT_int, True)
        self.declare_variable('texture-minfilter', 'linear',
                              p3d.ConfigFlags.VT_string, True)
        self.declare_variable('texture-magfilter', 'linear',
                              p3d.ConfigFlags.VT_string, True)
        self.declare_variable('compressed-textures', False,
                              p3d.ConfigFlags.VT_bool, False)

        self.declare_variable('audio-volume', 1.0,
                              p3d.ConfigFlags.VT_double, False)
        self.declare_variable('audio-music-active', True,
                              p3d.ConfigFlags.VT_bool, False)
        self.declare_variable('audio-sfx-active', True,
                              p3d.ConfigFlags.VT_bool, False)

    def get_available_display_types(self) -> list:
        """
        Get a list of available display types for Panda3D on the current platform.

        Returns:
            A list of available display type strings.
        """

        display_types = ['pandagl']

        # TODO: platform specific display types

        return display_types

    def get_default_display_type(self) -> str:
        """
        Get the default display type to use for the 'load-display' variable based on the platform.

        Returns:
            The default display type string for Panda3D.
        """

        return 'pandagl'

    def is_console_device(self) -> bool:
        """
        Checks if the application is running on a game console like device (e.g. Xbox, PlayStation, Switch) 
        where certain settings may need to be different.
        """

        # TODO: Implement actual console device detection logic if targeting consoles.
        return False

    def load_display_validate(self, value: str) -> bool:
        """
        Validate the value for the 'load-display' variable to ensure it's an available display type.

        Args:
            value: The display type string to validate.

        Returns:
            Whether the value is a valid display type.
        """

        return value in self.get_available_display_types()

    def win_size_changed(self, value: str) -> None:
        """
        Handle changes to the 'win-size' configuration variable.

        Args:
            value: The new value of the variable.
        """

        self.__configure_window()

    def fullscreen_changed(self, value: str) -> None:
        """
        Handle changes to the 'fullscreen' configuration variable.

        Args:
            value: The new value of the variable.
        """

        self.__configure_window()

    def __configure_window(self) -> None:
        """
        Configure the Panda3D window based on the current configuration variables.
        """

        if not runtime.has_base() or runtime.base.win is None:
            return

        width, height = self.get('win-size', '1280 720').split(' ')
        is_fullscreen = self.get('fullscreen', 'false').lower() in [
            'true', '1']

        props = p3d.WindowProperties()
        props.set_size(int(width), int(height))
        props.set_fullscreen(is_fullscreen)
        runtime.base.win.request_properties(props)
