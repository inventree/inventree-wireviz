"""Wireviz plugin for InvenTree.

Provides integration of "wireviz" into the InvenTree system:

- Render wireviz diagrams in the browser
- Extract and integrate bills of materials from wireviz diagrams
"""

import logging
import os
import tempfile

from wireviz.Harness import Harness
from wireviz.wireviz import parse as parse_wireviz
from wireviz.wv_bom import bom_list
from wireviz.wv_html import generate_html_output

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

from plugin import InvenTreePlugin
from plugin.mixins import EventMixin, PanelMixin, SettingsMixin

from company.models import ManufacturerPart, SupplierPart
from part.models import BomItem, Part, PartAttachment
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

    HARNESS_HTML_FILE = "wireviz_harness.html"
    ERROR_MSG_FILE = 'wireviz_errors.txt'
    WARNING_MSG_FILE = "wireviz_warnings.txt"

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
            'validator': bool,
        },
        "CLEAR_BOM_DATA": {
            'name': 'Clear BOM Data',
            'description': 'Clear existing BOM data when uploading a new wireviz diagram',
            'default': True,
            'validator': bool,
        },
        'ADD_IMAGES': {
            'name': 'Add Part Images',
            'description': 'Include part images in the wireviz diagram (not yet implemeted)',
            'default': True,
            'validator': bool,
        },
    }

    def get_harness_data(self, part: Part):
        """Return the harness html data for the part."""
            
        for attachment in part.attachments.all():
            fn = attachment.attachment.name
            if os.path.basename(fn) == self.HARNESS_HTML_FILE:
                return attachment.attachment.read().decode()
    
        return None

    def get_panel_context(self, view, request, context):
        """Return context information for the Wireviz panel."""

        try:
            part = view.get_object()
        except AttributeError:
            return context
        
        if isinstance(view, PartDetail) and isinstance(part, Part):
            # Extract any wireviz errors from the part attachments
            for attachment in part.attachments.all():
                fn = attachment.attachment.name

                if harness_html := self.get_harness_data(part):
                    context['wireviz_harness_html'] = harness_html

                if os.path.basename(fn) == self.ERROR_MSG_FILE:
                    context['wireviz_errors'] = attachment.attachment.read().decode().split("\n")

                if os.path.basename(fn) == self.WARNING_MSG_FILE:
                    context['wireviz_warnings'] = attachment.attachment.read().decode().split("\n")

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

            if self.get_harness_data(part):
                panels.append({
                    'title': 'WireViz Harness',
                    'icon': 'fas fa-plug',
                    'content_template': 'wireviz/harness_panel.html',
                    'javascript_template': 'wireviz/harness_panel.js',
                })
        
        return panels

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

        self.errors = []
        self.warnings = []
        self.part_map = {}

        # Parse the wireviz file
        filename = os.path.join(settings.MEDIA_ROOT, wv_file)

        if not os.path.exists(filename):
            self.add_error(f"File does not exist: {filename}")
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

        # Extract BOM data from the harness
        self.extract_bom_data(harness)

        if self.get_setting("ADD_IMAGES"):
            self.add_part_images(harness)

        self.generate_html_output(harness)

        # Save any error messages to a file
        self.save_error_file()
        self.save_warning_file()

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
            path = os.path.abspath(path)

            if os.path.exists(path):
                for filename in os.listdir(path):
                    if filename.lower().endswith('.wireviz'):
                        filepath = os.path.join(path, filename)

                        logger.info(f"WirevizPlugin: Loading wireviz template file: {filepath}")

                        with open(filepath, 'r') as f:
                            prepend_data += f.read()
                            prepend_data += '\n\n'

        return prepend_data

    def add_part_images(self, harness: Harness):
        """Add part images to the wireviz harness"""
        
        logger.warning("WirevizPlugin: Adding part images is not yet supported")
        
        # TODO: Implement native image support

        """
        # Path to part images directory
        img_path = pathlib.Path(settings.MEDIA_ROOT)

        for designator, part in self.part_map.items():

            logger.debug(f"Checking image for {designator} - {part}")

            # Check if the part has an image
            if not part.image:
                continue

            # Check if the image exists
            img_filename = pathlib.Path(img_path, part.image.name)

            if not img_filename.exists():
                continue

            # Construct a new image object associated with the part
            img = WirevizImage(img_filename, src=part.image.name, width=100)

            # Add the image to the harness
            if designator in harness.connectors:
                harness.connectors[designator].image = img
            if designator in harness.cables:
                harness.cables[designator].image = img
        """
                
    @transaction.atomic
    def extract_bom_data(self, harness: Harness):
        """Extract Bill of Materials data from a wireviz harness.
        
        Arguments:
            harness: A wireviz Harness instance
        """
        logger.info("WirevizPlugin: Extracting BOM data from wireviz harness")

        bom = harness.bom()

        # A list of BomItem objects to be created
        bom_items = []

        for line in bom:
            designators = line.get('designators', [])
            description = line.get('description', None)
            quantity = line.get('qty', None)

            if not description:
                self.add_error(f"No description for line: {line}")
                continue

            try:
                quantity = float(quantity)
            except (TypeError, ValueError):
                self.add_error(f"Invalid quantity for line: {line}")
                continue

            sub_part = self.match_part(line)

            if not sub_part:
                self.add_warning(f"No matching part for line: {description}")
                continue

            if sub_part == self.part:
                self.add_error(f"Part {sub_part} is the same as the parent part")
                continue

            # Associate the internal part with the designators
            for designator in designators:
                self.part_map[designator] = sub_part

            # Construct a new BomItem object
            bom_items.append(BomItem(
                part=self.part,
                sub_part=sub_part,
                quantity=quantity,
                note="Wireviz BOM item"
            ))

        if self.get_setting('EXTRACT_BOM'):
            if self.get_setting('CLEAR_BOM_DATA'):
                logger.info(f"WirevizPlugin: Clearing existing BOM data for part {self.part}")
                self.part.bom_items.all().delete()
            
            # Create the new BomItem objects in the database
            BomItem.objects.bulk_create(bom_items)

    def match_part(self, line: dict):
        """Attempt to match a BOM line item to an InvenTree part.
        
        Arguments:
            line: A dictionary of BOM line item data
        
        Returns:
            A Part instance, or None
        """

        # Extract data from BOM entry
        pn = line.get('pn', None)
        description = line.get('description', None)
        mpn = line.get('mpn', None)
        spn = line.get('spn', None)

        # Match pn -> part.IPN
        if pn:
            results = Part.objects.filter(IPN=pn)
            if results.count() == 1:
                return results.first()

            # Match pn -> part.name
            results = Part.objects.filter(name=pn)
            if results.count() == 1:
                return results.first()

        # Match description -> part.description
        if description:
            results = Part.objects.filter(description=description)
            if results.count() == 1:
                return results.first()

        # Match mpn -> manufacturer_part.MPN
        if mpn:
            results = ManufacturerPart.objects.filter(MPN=mpn)
            if results.count() == 1:
                return results.first().part
        
        # Match spn -> supplier_part.SKU
        if spn:
            results = SupplierPart.objects.filter(SKU=spn)
            if results.count() == 1:
                return results.first().part

        # For a 'wire', append the wire color and try again
        if pn and description and description.startswith('Wire, '):
            wire_data = [x.strip() for x in description.split(',')]

            """
            For individual wires, the PN does not include the color.
            For example, a wire might have a PN "26AWG-PTFE"
            To fully quality the wire, we need to append the color.
            So, we might get a value like "26AWG-PTFE-YE" for a yellow wire.
            """

            if len(wire_data) >= 3:
                color = wire_data[2]
            
            wire_pn = f"{pn}-{color}"

            # Match wire_pn -> part.IPN
            results = Part.objects.filter(IPN=wire_pn)
            if results.count() == 1:
                return results.first()
        
            # Match wire_pn -> part.name
            results = Part.objects.filter(name=wire_pn)
            if results.count() == 1:
                return results.first()
    
    @transaction.atomic
    def generate_html_output(self, harness: Harness):
        """Generate HTML output from a wireviz harness."""

        logger.info("WirevizPlugin: Generating HTML output for wireviz harness")

        # Delete existing HTML output
        for attachment in self.part.attachments.all():
            if attachment.attachment.name == self.HARNESS_HTML_FILE:
                attachment.delete()

        bomlist = bom_list(harness.bom())

        # For now, we must write to a tempfile
        # In the future, work out how to write to an in-memory file object
        out_file = os.path.join(tempfile.gettempdir(), 'harness_out')
        
        harness.output(filename=out_file, fmt=('svg',), view=False)
        generate_html_output(out_file, bomlist, harness.metadata, harness.options)

        # Read the data back in
        with open(out_file + '.html', 'r') as f:
            html_data = f.read()

        # Create a new PartAttachment for the rendered HTML
        PartAttachment.objects.create(
            part=self.part,
            attachment=ContentFile(
                html_data,
                name=self.HARNESS_HTML_FILE,
            ),
            comment='Wireviz Harness (autogenerated from .wireviz file)',
            user=None
        )

    def add_error(self, msg: str):
        """Add an error message to the list of errors."""

        self.errors.append(msg)
        logger.error(f"WireViz: {msg}")

    def add_warning(self, msg: str):
        """Add a warning message to the list of errors."""

        self.warnings.append(msg)
        logger.warning(f"WireViz: {msg}")

    @transaction.atomic
    def save_error_file(self):
        """Save an error file containing all error messages"""

        # First, delete any existing error file
        for attachment in self.part.attachments.all():
            if attachment.attachment.name == self.ERROR_MSG_FILE:
                attachment.delete()
        
        # Create a new error file
        if len(self.errors) > 0:
            PartAttachment.objects.create(
                part=self.part,
                attachment=ContentFile(
                    '\n'.join(self.errors).encode(),
                    name=self.ERROR_MSG_FILE,
                ),
                comment='Wireviz Error Messages',
                user=None
            )
    
    @transaction.atomic
    def save_warning_file(self):
        """Save a warning file containing all warning messages"""

        # First, delete any existing warning file
        for attachment in self.part.attachments.all():
            if attachment.attachment.name == self.WARNING_MSG_FILE:
                attachment.delete()
        
        # Create a new warning file
        if len(self.warnings) > 0:
            PartAttachment.objects.create(
                part=self.part,
                attachment=ContentFile(
                    '\n'.join(self.warnings).encode(),
                    name=self.WARNING_MSG_FILE,
                ),
                comment='Wireviz Warning Messages',
                user=None
            )
