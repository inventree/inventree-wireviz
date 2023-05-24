"""Wireviz plugin for InvenTree.

Provides integration of "wireviz" into the InvenTree system:

- Render wireviz diagrams in the browser
- Extract and integrate bills of materials from wireviz diagrams
"""

import io
import os
import logging

from wireviz.wireviz import parse as parse_wireviz
from wireviz.Harness import Harness
from wireviz.wv_bom import bom_list
from wireviz.wv_html import generate_html_output

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

from plugin import InvenTreePlugin
from plugin.mixins import EventMixin, PanelMixin, SettingsMixin

from part.models import Part, PartAttachment
from part.views import PartDetail

from .version import PLUGIN_VERSION


logger = logging.getLogger('inventree')


class WirevizPlugin(EventMixin, PanelMixin, SettingsMixin, InvenTreePlugin):
    """"Wireviz plugin for InvenTree
    
    - Provides a custom panel for rendering wireviz diagrams
    - Automatically renders wireviz diagrams when a .wireviz file is uploaded
    - Extract BOM information from the wireviz diagram
    """

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
        "EXTRACT_BOM": {
            'name': 'Extract BOM Data',
            'description': 'Automatically extract BOM data from wireviz diagrams',
            'default': True,
            'valitator': bool,
        },
        "CLEAR_BOM_DATA": {
            'name': 'Clear BOM Data',
            'description': 'Clear existing BOM data when uploading a new wireviz diagram',
            'default': True,
            'valitator': bool,
        }
    }

    def get_panel_context(self, view, request, context):
        """Return context information for the Wireviz panel."""

        # TODO

        return context

    def get_custom_panels(self, view, request):
        """Determine if custom panels should be displayed in the UI."""

        panels = []

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

    def process_event(self, event, *args, **kwargs):
        """Callback for event processing.
        
        We are interested in the following events:
        - part_partattachment.created
        """

        # Callback for when a new PartAttachment is created
        if event == 'part_partattachment.created':
            pk = kwargs.get('id', None)

            try:
                attachment = PartAttachment.objects.get(pk=pk)
                filename = attachment.attachment.name

                # Store a reference to the parent Part
                self.part = attachment.part

                # Check if the attachment is a .wireviz file
                if filename.endswith(".wireviz"):
                    self.process_wireviz_file(filename)
            except PartAttachment.DoesNotExist:
                pass
    
    def process_wireviz_file(self, wv_file: str, part: Part = None):
        """Process a wireviz file, and extract the relevant information."""
        logger.info(f"WirevizPlugin: Processing wireviz file: {wv_file}")

        # Parse the wireviz file
        filename = os.path.join(settings.MEDIA_ROOT, wv_file)

        if not os.path.exists(filename):
            logger.error(f"WirevizPlugin: File does not exist: {filename}")
            return
        
        with open(filename, 'r') as f:
            wireviz_data = f.read()

        if prepend := self.prepend_wireviz_data():
            wireviz_data = prepend + wireviz_data

        # Parse the wireviz data
        harness = parse_wireviz(
            wireviz_data,
            return_types='harness',
        )

        # Construct a list of error messages to display to the user
        self.errors = []

        if self.get_setting('EXTRACT_BOM'):
            self.extract_bom_data(harness)

        self.generate_html_output(harness)

        # Generate BOM data
        bom = harness.bom()

    def prepend_wireviz_data(self):
        """Load (and prepend) any custom wireviz templates.
        
        - Any '.wireviz' files found in the WIREVIZ_PATH directory will be loaded
        - The contents of these files will be prepended to the wireviz data
        """

        prepend_data = ''

        subdir = self.get_setting('WIREVIZ_PATH')

        logger.info(f"WirevizPlugin: Prepending wireviz data from {subdir}")

        if subdir:
            path = os.path.join(settings.MEDIA_ROOT, subdir)

            if os.path.exists(path):
                for filename in os.listdir(path):
                    if filename.lower().endswith('.wireviz'):
                        filepath = os.path.join(path, filename)

                        logger.debug(f"WirevizPlugin: Loading wireviz template file: {filepath}")

                        with open(filepath, 'r') as f:
                            prepend_data += f.read()
                            prepend_data += '\n\n'
            
            else:
                logger.warning(f"WirevizPlugin: Wireviz path does not exist: {path}")

        return prepend_data

    @transaction.atomic
    def extract_bom_data(self, harness: Harness):
        """Extract Bill of Materials data from a wireviz harness.
        
        Arguments:
            harness: A wireviz Harness instance        
        """
        logger.info(f"WirevizPlugin: Extracting BOM data from wireviz harness")

        bom = harness.bom()

        # Clear existing BOM data
        if self.get_setting('CLEAR_BOM_DATA'):
            logger.info(f"WirevizPlugin: Clearing existing BOM data for part {self.part}")
            self.part.bom_items.all().delete()

        for line in bom:
            if part := self.match_part(line):
                logger.debug(f"WirevizPlugin: Matched part: {part}")
            else:
                logger.warning(f"WirevizPlugin: No matching part for line: {line}")

    def match_part(self, line: dict):
        """Attempt to match a BOM line item to an InvenTree part.
        
        Arguments:
            line: A dictionary of BOM line item data
        
        Returns:
            A Part instance, or None
        """

        part = None

        # Extract part number from line
        if pn := line.get('pn', None):

            # Try to match by part name
            part = Part.objects.filter(name=pn).first()

            # Try to match by IPN
            if not part:
                part = Part.objects.filter(IPN=pn).first()

        # TODO: Try to match by description?

        # TODO: Try to match by MPN?

        # TODO: Try to match by manufacturer?

        # TODO: Try to match by supplier?

        # TODO: Try to match by other methods?

        return part

    def generate_html_output(self, harness: Harness):
        """Generate HTML output from a wireviz harness."""

        """
        # Create a new PartAttachment for the rendered HTML
        PartAttachment.objects.create(
            part=self.part,
            attachment=ContentFile(
                html_file.getvalue().encode(),
                name='wireviz_harness.html',
            ),
            comment=f'Wireviz Harness (autogenerated from {wv_file})',
            user=None
        )
        """
        ...
