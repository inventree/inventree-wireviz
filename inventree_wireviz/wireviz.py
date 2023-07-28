"""Wireviz plugin for InvenTree.

Provides integration of "wireviz" into the InvenTree system:

- Render wireviz diagrams in the browser
- Extract and integrate bills of materials from wireviz diagrams
"""

import logging
import os

from wireviz.Harness import Harness
from wireviz.wireviz import parse as parse_wireviz

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

from plugin import InvenTreePlugin
from plugin.mixins import EventMixin, PanelMixin, ReportMixin, SettingsMixin

from build.views import BuildDetail
from company.models import ManufacturerPart, SupplierPart
from InvenTree.api_version import INVENTREE_API_VERSION
from part.models import BomItem, Part, PartAttachment
from part.views import PartDetail

from .version import PLUGIN_VERSION


logger = logging.getLogger('inventree')


class WirevizPlugin(EventMixin, PanelMixin, ReportMixin, SettingsMixin, InvenTreePlugin):
    """"Wireviz plugin for InvenTree
    
    - Provides a custom panel for rendering wireviz diagrams
    - Automatically renders wireviz diagrams when a .wireviz file is uploaded
    - Extract BOM information from the wireviz diagram
    """

    AUTHOR = "Oliver Walters"
    DESCRIPTION = "Wireviz plugin for InvenTree"
    VERSION = PLUGIN_VERSION

    MIN_VERSION = '0.12.0'

    NAME = "Wireviz"
    SLUG = "wireviz"
    TITLE = "Wireviz Plugin"

    # Filenames and key constants
    HARNESS_SVG_FILE = "wireviz_harness.svg"

    HARNESS_SRC_KEY = "source_file"
    HARNESS_SVG_KEY = "svg_file"
    HARNESS_BOM_KEY = "bom_data"

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

    def get_part_from_instance(self, instance):
        """Return a Part object from the given instance."""

        if not instance:
            return None

        if isinstance(instance, Part):
            return instance
    
        if hasattr(instance, 'part') and isinstance(instance.part, Part):
            return instance.part
        
        # No match
        return None

    def add_report_context(self, report_instance, model_instance, request, context):
        """Inject wireviz data into the report context."""

        # Extract a Part model from the model instance
        part = self.get_part_from_instance(model_instance)

        if isinstance(part, Part):
            metadata = part.get_metadata('wireviz')

            if metadata:
                if svg_file := metadata.get(self.HARNESS_SVG_KEY, None):
                    svg_path = os.path.join(settings.MEDIA_ROOT, svg_file)
                    
                    # Ensure that the file really does exist
                    if os.path.exists(svg_path):
                        context['wireviz_svg_file'] = svg_file

                if bom_data := metadata.get(self.HARNESS_BOM_KEY, None):
                    context['wireviz_bom_data'] = bom_data

    def get_panel_context(self, view, request, context):
        """Return context information for the Wireviz panel."""

        try:
            instance = view.get_object()
        except AttributeError:
            return context

        part = self.get_part_from_instance(instance)

        if part and isinstance(part, Part):

            # Get wireviz file information from part metadata
            wireviz_metadata = part.get_metadata('wireviz')

            if wireviz_metadata:
                svg_file = wireviz_metadata.get(self.HARNESS_SVG_KEY, None)
                bom_data = wireviz_metadata.get(self.HARNESS_BOM_KEY, None)
                src_file = wireviz_metadata.get(self.HARNESS_SRC_KEY, None)

                if svg_file:
                    context['wireviz_svg_file'] = os.path.join(settings.MEDIA_URL, svg_file)

                if src_file:
                    context['wireviz_source_file'] = os.path.join(settings.MEDIA_URL, src_file)

                if bom_data:
                    context['wireviz_bom_data'] = bom_data
                
                # Add warnings and errors
                context['wireviz_warnings'] = wireviz_metadata.get('warnings', None)
                context['wireviz_errors'] = wireviz_metadata.get('errors', None)

        return context

    def get_custom_panels(self, view, request):
        """Determine if custom panels should be displayed in the UI."""

        panels = []

        try:
            instance = view.get_object()
        except AttributeError:
            return panels
        
        part = self.get_part_from_instance(instance)

        # A valid part object has been found
        if part and isinstance(part, Part):
    
            # We are on the PartDetail or BuildDetail page
            if isinstance(view, PartDetail) or isinstance(view, BuildDetail):

                logger.debug(f"Checking for wireviz file for part {part}")

                metadata = part.get_metadata('wireviz')

                if metadata:
                    panels.append({
                        'title': 'Harness Diagram',
                        'icon': 'fas fa-project-diagram',
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
                    self.cleanup_old_files(filename, self.part)
                    self.process_wireviz_file(filename, part=self.part)

            except PartAttachment.DoesNotExist:
                pass
    
    def cleanup_old_files(self, filename: str, part: Part):
        """Remove any old wireviz files from the part."""

        if not self.get_setting('DELETE_OLD_FILES'):
            # Don't delete old files
            return
        
        file_keys = [
            self.HARNESS_SRC_KEY,
            self.HARNESS_SVG_KEY,
        ]

        metadata = part.get_metadata('wireviz')

        if not metadata:
            # No metadata to check
            return

        filenames = []

        for key in file_keys:
            if key in metadata:
                filenames.append(metadata[key])

        for attachment in part.attachments.all():
            fn = attachment.attachment.name

            if fn == filename or os.path.basename(fn) == filename:
                # Don't delete the newly uploaded file!
                continue

            if fn in filenames or os.path.basename(fn) in filenames:
                logger.info(f"Deleting old wireviz file: {fn}")
                attachment.delete()

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
        
        # Extract BOM data from the harness
        self.extract_bom_data(harness)

        if self.get_setting("ADD_IMAGES"):
            self.add_part_images(harness)

        wz_filename = os.path.basename(wv_file)

        # Generate SVG output

        try:
            svg_file = self.generate_svg_output(harness, wz_filename)
            svg_file = svg_file.attachment.name
        except Exception as exc:
            self.add_error(f"Failed to generate SVG output for wireviz file: {wv_file}")
            self.add_error(f"Exception: {exc}")
            svg_file = None

        # Update the part metadata
        wireviz_data = {
            self.HARNESS_SRC_KEY: wv_file,
            self.HARNESS_SVG_KEY: svg_file,
            self.HARNESS_BOM_KEY: self.bom_lines,
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

        # A list of BOM lines to be exported to csv
        self.bom_lines = []

        for line in bom:
            designators = line.get('designators', [])
            description = line.get('description', None)
            pn = line.get('pn', None)
            mpn = line.get('mpn', None)
            spn = line.get('spn', None)
            quantity = line.get('qty', None)
            unit = line.get('unit', None)

            try:
                quantity = float(quantity)
            except (TypeError, ValueError):
                self.add_error(f"Invalid quantity for line: {line}")
                continue

            sub_part = self.match_part(line)

            # Add line to internally stored BOM data
            self.bom_lines.append({
                'idx': len(self.bom_lines) + 1,
                'description': description,
                'designators': ', '.join(designators),
                'quantity': quantity,
                'unit': unit,
                'sub_part': sub_part.pk if sub_part else None,
                'pn': pn,
                'mpn': mpn,
                'spn': spn,
            })

            if not sub_part:
                # No matching part can be found
                continue

            if sub_part == self.part:
                self.add_error(f"Part {sub_part} is the same as the parent part")
                continue

            # Check that it is a *valid* option for the BOM
            if not sub_part.check_add_to_bom(self.part):
                self.add_error(f"Part {sub_part} is not a valid option for the BOM")
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
            # Prevent zero-quantity BOM Items
            if quantity > 0:
                self.bom_items.append(BomItem(
                    part=self.part,
                    sub_part=sub_part,
                    quantity=quantity,
                    reference=' '.join(designators),
                    note="Wireviz BOM item"
                ))
        
        # Write BOM data to database
        self.save_bom_data()

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

    def generate_svg_output(self, harness: Harness, filename: str):
        """Generate SVG output from a wireviz harness."""

        logger.info("WirevizPlugin: Generating SVG output for wireviz harness")

        graph = harness.create_graph()
        svg_data = graph.pipe(format='svg')

        return PartAttachment.objects.create(
            part=self.part,
            attachment=ContentFile(
                svg_data.decode('utf-8'),
                name='wireviz_harness.svg',
            ),
            comment=f"Wireviz Harness (autogenerated from {filename})",
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
