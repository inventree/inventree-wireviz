"""Wireviz file processing functionality."""


from rest_framework.exceptions import ValidationError

from plugin.registry import registry

from wireviz.Harness import Harness
from wireviz.wireviz import parse as parse_wireviz


def get_unit_registry():
    """Return the pint unit registry"""

    from InvenTree.api_version import INVENTREE_API_VERSION

    if INVENTREE_API_VERSION >= 117:
        # Modern version of InvenTree supports custom unit registry
        import InvenTree.conversion
        return InvenTree.conversion.get_unit_registry()
    
    # Fallback to the default pint unit registry
    import pint
    return pint.UnitRegistry()


class WirevizImportManager:
    """Class for managing a wireviz file import session."""

    def __init__(self):
        """Initialize the WirevizImportManager."""
        
        # Grab a reference to the wireviz plugin
        self.plugin = registry.get_plugin('wireviz')

        # Get the unit registry
        self.ureg = get_unit_registry()

    def parse_wireviz_file(self, wv_file) -> Harness:
        """Process the provided wireviz file.

        Returns a wireviz Harness object (if the file is valid)
        
        Raises:
            ValidationError: If the file is invalid (for some reason)
        """
        
        # TODO: Prepend data from other files

        wv_data = wv_file.read().decode('utf-8')

        try:
            harness = parse_wireviz(wv_data, return_types='harness')
        except Exception as exc:
            raise ValidationError([
                {str(exc)},
                "Failed to parse wireviz file:",
            ])

        return harness
