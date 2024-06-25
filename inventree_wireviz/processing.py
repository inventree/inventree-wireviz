"""Wireviz file processing functionality."""

import logging
import os
import yaml

from django.conf import settings
from django.core.files.base import ContentFile
from rest_framework.exceptions import ValidationError

from company.models import ManufacturerPart, SupplierPart
from InvenTree.helpers import str2bool
from part.models import BomItem, Part
from plugin.registry import registry

from wireviz.Harness import Harness
from wireviz.wireviz import parse as parse_wireviz


logger = logging.getLogger("inventree")


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

        self.part = None
        self.errors = []
        self.warnings = []
        self.part_map = {}

    def create_attachment(self, part, attachment, comment, user):
        """Upload a file attachment to the specified part.
        
        Note: We support both the "legacy" and "modern" attachment table.

        Ref: https://github.com/inventree/InvenTree/pull/7420
        """

        # First, try the "modern" attachment table
        try:
            from common.models import Attachment

            return Attachment.objects.create(
                model_type='part',
                model_id=part.pk,
                attachment=attachment,
                comment=comment,
                upload_user=user
            )
        except Exception:
            pass

        # Second, try the "legacy" attachment table
        try:
            from part.models import PartAttachment

            return PartAttachment.objects.create(
                part=part,
                attachment=attachment,
                comment=comment,
                user=user
            )
        except Exception:
            pass

        # Attachment not created
        raise ValidationError("Error creating attachment file")

    def prepend_templates(self):
        """Prepend the contents of the wireviz template files to the wireviz file."""

        prepend_data = ''

        for template in self.plugin.get_template_files():
            tf = os.path.abspath(os.path.join(settings.MEDIA_ROOT, template))

            with open(tf, 'r') as f:

                template_data = f.read()

                try:
                    yaml.safe_load(template_data)
                except Exception as exc:
                    self.add_error(f"Invalid YAML data in template file '{template}'")
                    self.add_error(f"YAML parsing error: {exc}")
                    continue

                prepend_data += template_data
                prepend_data += '\n\n'

        return prepend_data

    def parse_wireviz_file(self, wv_file) -> Harness:
        """Process the provided wireviz file.

        Returns a wireviz Harness object (if the file is valid)
        
        Raises:
            ValidationError: If the file is invalid (for some reason)
        """
        
        wv_file.seek(0)
        wv_data = wv_file.read().decode('utf-8')

        try:
            yaml.safe_load(wv_data)
        except Exception as exc:
            raise ValidationError([
                {str(exc)},
                "Not a valid YAML file",
            ])

        # Prepend data from existing templates
        wv_data = self.prepend_templates() + wv_data

        try:
            harness = parse_wireviz(wv_data, return_types='harness')
        except Exception as exc:
            raise ValidationError([
                {str(exc)},
                "Failed to parse wireviz file:",
            ])

        return harness

    def cleanup_old_files(self, part: Part):
        """Remove old files from an existing Part instance."""

        metadata = part.get_metadata('wireviz')

        if not metadata:
            return
        
        file_keys = [
            'source_file',
            'svg_file',
        ]

        filenames = []

        for key in file_keys:
            if key in metadata:
                filenames.append(metadata[key])

        for attachment in part.attachments.all():
            fn = attachment.attachment.name

            if fn in filenames or os.path.basename(fn) in filenames:
                logger.info("WireViz: Deleting old file '%s'", fn)
                attachment.delete()

    def import_harness(self, wv_file, part: Part, user):
        """Import a wireviz file into the specified part."""
        
        logger.info("Importing wireviz harness file")

        # Determine runtime settings
        delete_old_files = str2bool(self.plugin.get_setting('DELETE_OLD_FILES'))
        save_bom_data = str2bool(self.plugin.get_setting('EXTRACT_BOM'))
        clear_bom_data = str2bool(self.plugin.get_setting('CLEAR_BOM_DATA'))

        self.part = part

        if delete_old_files:
            self.cleanup_old_files(part)

        # Extract harness information
        harness = self.parse_wireviz_file(wv_file.file)

        self.extract_bom_data(harness)

        if save_bom_data:
            if clear_bom_data:
                self.part.bom_items.all().delete()
            
            # Bulk create new Bom Items
            BomItem.objects.bulk_create(self.bom_items)

        wv_file.file.seek(0)
        wv_data = wv_file.file.read().decode('utf-8')

        wv_filename = os.path.basename(wv_file.name)

        # Save the uploaded wireviz file as an attachment for the Part instance
        wv_attachment = self.create_attachment(
            self.part,
            ContentFile(wv_data, name=wv_filename),
            'Wireviz Harness File',
            user,
        )

        # Generate SVG output
        try:
            svg_file = self.generate_svg_output(harness, wv_filename, user)
            svg_file = svg_file.attachment.name
        except Exception as exc:
            svg_file = None
            self.add_error(f"Failed to generate SVG file: {exc}")

        # Update the part metadata
        wireviz_data = {
            'source_file': wv_attachment.attachment.name,
            'svg_file': svg_file,
            'bom_data': self.bom_lines,
            'errors': self.errors,
            'warnings': self.warnings
        }

        self.part.set_metadata('wireviz', wireviz_data, overwrite=True)

    def extract_bom_data(self, harness: Harness):
        """Extract BOM data from the provided harness file."""

        logger.info("WireViz: Extracting BOM data from wireviz file")

        bom = harness.bom()

        self.bom_items = []
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

    def add_error(self, msg: str):
        """Add an error message."""
        self.errors.append(msg)
        logger.error(f"WireViz: {msg}")
    
    def add_warning(self, msg: str):
        """Add a warning message."""
        self.warnings.append(msg)
        logger.warning(f"WireViz: {msg}")

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
    
    def generate_svg_output(self, harness: Harness, filename: str, user):
        """Generate SVG output from a wireviz harness."""

        logger.info("WirevizPlugin: Generating SVG output for wireviz harness")

        graph = harness.create_graph()
        svg_data = graph.pipe(format='svg')

        return self.create_attachment(
            self.part,
            ContentFile(
                svg_data.decode('utf-8'),
                name='wireviz_harness.svg',
            ),
            f"Wireviz Harness (autogenerated from {filename})",
            user
        )
