"""Wireviz plugin for InvenTree.

Provides integration of "wireviz" into the InvenTree system:

- Render wireviz diagrams in the browser
- Extract and integrate bills of materials from wireviz diagrams
"""

import logging

from plugin import InvenTreePlugin
from plugin.mixins import EventMixin, PanelMixin, SettingsMixin

from part.views import PartDetail

from .version import PLUGIN_VERSION


logger = logging.getLogger('inventree')


class WirevizPlugin(EventMixin, PanelMixin, SettingsMixin, InvenTreePlugin):
    """"Wireviz" plugin for InvenTree."""

    AUTHOR = "Oliver Walters"
    DESCRIPTION = "Wireviz plugin for InvenTree"
    VERSION = PLUGIN_VERSION

    NAME = "Wireviz"
    SLUG = "wireviz"
    TITLE = "Wireviz Plugin"

    SETTINGS = {
        "WIREVIZ_PATH": {
            'name': 'Wireviz Upload Path',
            'description': 'Path to store uploaded wireviz template files (relative to media root)',
            'default': 'wireviz',
        },
    }

    def get_panel_context(self, view, request, context):
        """Return context information for the Wireviz panel."""

        # TODO

        return context

    def get_custom_panels(self, view, request):
        """Determine if custom panels should be displayed in the UI."""

        panels = []

        logger.info(f"wireviz: get_custom_panels called for {view}")

        try:
            instance = view.get_object()
        except AttributeError:
            return panels
    
        if isinstance(view, PartDetail):
            part = instance

            logger.info(f"Checking for wireviz file for part {part}")

            if True or self.get_harness_file(part) is not None:

                panels.append({
                    'title': 'Wire Harness',
                    'icon': 'fas fa-plug',
                    'content_template': 'wireviz/harness_panel.html',
                    'javascript_template': 'wireviz/harness_panel.js',
                })
        
        return panels

    def get_harness_file(self, part):
        """Return the harness file associated with a given Part instance.
        
        - Look for any files with the .wireviz extension
        - Return the first one found (latest date first)

        Arguments:
            part: The Part instance to check
        
        Returns:
            The first matching WirevizFile instance, or None
        """

        # Check if any attachment has the correct format
        for attachment in part.attachments.all().order_by('-upload_date'):
            if attachment.filename.lower().endswith('.wireviz'):
                return attachment
