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
from InvenTree.api_version import INVENTREE_API_VERSION
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

    SETTINGS = {
        "WIREVIZ_PATH": {
            'name': 'Wireviz Upload Path',
            'description': 'Path to store uploaded wireviz template files (relative to media root)',
            'default': 'wireviz',
        },
        "DELETE_OLD_FILES": {
            'name': 'Delete Old Files',
            'description': 'Delete old wireviz files when uploading a new wireviz file',
            'default': True,
            'validator': bool,
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

    def get_diagram_file(self, part: Part):
        """Return the generated HTML file"""

        metadata = part.get_metadata('wireviz')

        # Primary: Find wireviz file specified in metadata
        if metadata and 'diagram' in metadata:
            filename = metadata['diagram']

            if filename:
                for attachment in part.attachments.all():
                    fn = attachment.attachment.name

                    if fn == filename or os.path.basename(fn) == filename:
                        logger.debug(f"Found wireviz diagram file: {fn}")
                        return attachment
        
        # Backup: Find legacy file (wireviz_harness.html)
        for attachment in part.attachments.all():
            fn = attachment.attachment.name

            if fn == self.HARNESS_HTML_FILE:
                logger.debug(f"Found legacy wireviz diagram file: {fn}")
                return attachment
        
        logger.debug(f"Could not find wireviz diagram file for part {part}")

    def get_panel_context(self, view, request, context):
        """Return context information for the Wireviz panel."""

        try:
            part = view.get_object()
        except AttributeError:
            return context
        
        if isinstance(view, PartDetail) and isinstance(part, Part):

            wireviz_metadata = part.get_metadata('wireviz')

            attachment = self.get_diagram_file(part)

            if attachment:
                context['wireviz_harness_html'] = attachment.attachment.read().decode()

            if wireviz_metadata:
                if 'warnings' in wireviz_metadata:
                    context['wireviz_warnings'] = wireviz_metadata.get('warnings', None)
                
                if 'errors' in wireviz_metadata:
                    context['wireviz_errors'] = wireviz_metadata.get('errors', None)

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

            logger.debug(f"Checking for wireviz file for part {part}")

            metadata = part.get_metadata('wireviz')

            if metadata:
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
                    self.process_wireviz_file(filename, part=self.part)

                    # Delete *old* wireviz files
                    if self.get_setting('DELETE_OLD_FILES'):
                        for attach in PartAttachment.objects.filter(part=self.part):
                            # Don't delete this one!
                            if attach.pk == attachment.pk:
                                continue

                            fn = attach.attachment.name

                            # Delete old wireviz files
                            if fn.endswith(".wireviz"):
                                attach.delete()

            except PartAttachment.DoesNotExist:
                pass
    
    def process_wireviz_file(self, wv_file: str, part: Part = None):
        """Process a wireviz file, and extract the relevant information."""

        logger.info(f"WirevizPlugin: Processing wireviz file: {wv_file}")

        # Get a unit registry for conversion
        if INVENTREE_API_VERSION >= 117:
            # Modern InvenTree versions supply a unit registry
            from InvenTree.conversion import get_unit_registry
            self.ureg = get_unit_registry()
        else:
            # Fallback to pint unit registry
            import pint
            self.ureg = pint.UnitRegistry()

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
        try:
            harness = parse_wireviz(
                wireviz_data,
                return_types='harness',
            )
        except Exception as exc:
            logger.error(f"WirevizPlugin: Failed to parse wireviz file: {exc}")

            from InvenTree.exceptions import log_error
            log_error("Wireviz Import")
            return
        
        self.remove_old_wireviz_data(part)

        # Extract BOM data from the harness
        self.extract_bom_data(harness)

        if self.get_setting("ADD_IMAGES"):
            self.add_part_images(harness)

        self.save_bom_data()

        # Generate a new .html harness file
        try:
            harness_file = self.generate_html_output(harness)
            harness_file = harness_file.attachment.name
        except Exception:
            harness_file = None

        # Update the part metadata
        wireviz_data = {
            'diagram': harness_file,
            'errors': self.errors,
            'warnings': self.warnings,
        }

        part.set_metadata('wireviz', wireviz_data, overwrite=True)

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
        self.bom_items = []

        for line in bom:
            designators = line.get('designators', [])
            description = line.get('description', None)
            quantity = line.get('qty', None)
            unit = line.get('unit', None)

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

            if unit or sub_part.units:
                quantity = self.convert_quantity(quantity, unit, sub_part.units)

            if not description:
                self.add_error(f"No description for line: {line}")
                continue

            # Construct a new BomItem object
            self.bom_items.append(BomItem(
                part=self.part,
                sub_part=sub_part,
                quantity=quantity,
                reference=' '.join(designators),
                note="Wireviz BOM item"
            ))

    def save_bom_data(self):
        """Write the extracted BOM data to the database."""

        if not self.get_setting('EXTRACT_BOM'):
            return
        
        if len(self.errors) > 0:
            self.add_warning("Not saving BOM data due to errors")
            return

        if self.get_setting('CLEAR_BOM_DATA'):
            logger.info(f"WirevizPlugin: Clearing existing BOM data for part {self.part}")
            self.part.bom_items.all().delete()
        
        # Create the new BomItem objects in the database
        BomItem.objects.bulk_create(self.bom_items)

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
    
    def remove_old_wireviz_data(self, part: Part):
        """Remove any existing wireviz data from the part."""

        attachment = self.get_diagram_file(part)

        # If an attachment exists, delete it
        if attachment:
            logger.info(f"WirevizPlugin: Deleting old wireviz file: {attachment}")
            attachment.delete()

    def generate_html_output(self, harness: Harness):
        """Generate HTML output from a wireviz harness."""

        logger.info("WirevizPlugin: Generating HTML output for wireviz harness")

        bomlist = bom_list(harness.bom())

        self.html_file = None

        # For now, we must write to a tempfile
        # In the future, work out how to write to an in-memory file object
        out_file = os.path.join(tempfile.gettempdir(), 'harness_out')
        
        harness.output(filename=out_file, fmt=('svg',), view=False)
        generate_html_output(out_file, bomlist, harness.metadata, harness.options)

        # Read the data back in
        with open(out_file + '.html', 'r') as f:
            html_data = f.read()
        
        # Create a new attachment file
        return PartAttachment.objects.create(
            part=self.part,
            attachment=ContentFile(
                html_data.encode(),
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

    def convert_quantity(self, quantity, unit, base_unit):
        """Convert a provided physical quantity into the "base units" of the part.
        
        Args:
            quantity: The quantity to convert
            unit: The unit of the quantity
            base_unit: The base unit of the part
        
        Returns:
            The converted quantity, or the original quantity if conversion failed
        """

        # Ignore unit if quantity not given
        # Will be specified in the part units anyway
        if not unit:
            return quantity

        logger.debug(f"WirevizPlugin: Converting quantity {quantity} {unit} to {base_unit}")

        q = f"{quantity} {unit}"

        try:
            val = self.ureg.Quantity(q)

            if base_unit:
                val = val.to(base_unit)

            return float(val.magnitude)
        except Exception:
            self.add_error(f"Could not convert quantity {quantity} {unit} to {base_unit}")
            return quantity
