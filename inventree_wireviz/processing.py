"""Wireviz file processing functionality."""


from rest_framework.exceptions import ValidationError

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


def parse_wireviz_file(wv_file, prepend_files=None) -> Harness:
    """Process the provided wireviz file.

    Returns a wireviz Harness object (if the file is valid)
     
    Raises:
        ValidationError: If the file is invalid (for some reason)
    """
    
    wv_data = wv_file.read().decode('utf-8')

    # TODO: prepend data from other files

    # Try to parse the wireviz file
    try:
        harness = parse_wireviz(
            wv_data,
            return_types='harness'
        )
    except Exception as exc:
        raise ValidationError(f"Failed to parse wireviz file: {str(exc)}")
