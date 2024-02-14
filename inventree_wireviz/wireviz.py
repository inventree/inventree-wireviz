"""Wireviz plugin for InvenTree.

Provides integration of "wireviz" into the InvenTree system:

- Render wireviz diagrams in the browser
- Extract and integrate bills of materials from wireviz diagrams
"""

import logging
import os

from django.conf import settings
from django.template.loader import render_to_string
from django.urls import path

from plugin import InvenTreePlugin
from plugin.mixins import PanelMixin, ReportMixin, SettingsMixin, UrlsMixin

from build.views import BuildDetail
from part.models import Part, PartCategory
from part.views import PartDetail

from .version import PLUGIN_VERSION


logger = logging.getLogger('inventree')


class WirevizPlugin(PanelMixin, ReportMixin, SettingsMixin, UrlsMixin, InvenTreePlugin):
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
        "HARNESS_CATEGORY": {
            'name': 'Wire Harness Category',
            'description': 'Select the part category for wire harnesses',
            'model': 'part.partcategory',
        },
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

            context['part'] = part

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

            add_panel = False

            # We are on the PartDetail or BuildDetail page
            if isinstance(view, PartDetail) or isinstance(view, BuildDetail):

                logger.debug(f"Checking for wireviz file for part {part}")

                metadata = part.get_metadata('wireviz')

                if metadata:
                    add_panel = True

            if not add_panel and isinstance(view, PartDetail):
                # Check if the Part belongs to the harness category
                if harness_category := self.get_setting('HARNESS_CATEGORY'):
                    try:
                        category = PartCategory.objects.get(pk=harness_category)
                        children = category.get_descendants(include_self=True)

                        if part.category in children:
                            add_panel = True

                    except (PartCategory.DoesNotExist, ValueError):
                        pass

            if add_panel:
                panels.append({
                    'title': 'Harness Diagram',
                    'icon': 'fas fa-project-diagram',
                    'content_template': 'wireviz/harness_panel.html',
                    'javascript_template': 'wireviz/harness_panel.js',
                })
        
        return panels

    def get_template_files(self):
        """Return a list of existing WireViz template files which have been uploaded."""

        templates = []
        subdir = self.get_setting('WIREVIZ_PATH')

        if subdir:
            path = os.path.join(settings.MEDIA_ROOT, subdir)
            path = os.path.abspath(path)

            if os.path.exists(path):
                for f in os.listdir(path):
                    if f.endswith('.wireviz'):
                        template = os.path.join(subdir, f)
                        templates.append(template)

        return templates

    def setup_urls(self):
        """Setup URL patterns for the wireviz plugin."""

        from . import views

        return [
            path('upload/', views.UploadWirevizView.as_view(), name='wireviz-file-upload'),
            path('delete/', views.DeleteWirevizView.as_view(), name='wireviz-file-delete'),
            path('upload-template/', views.UploadTemplateView.as_view(), name='wireviz-upload-template'),
            path('delete-template/', views.DeleteTemplateView.as_view(), name='wireviz-delete-template'),
        ]

    def get_settings_content(self, request):
        """Custom settings content for the wireviz plugin page."""

        ctx = {
            'plugin': self,
            'templates': self.get_template_files(),
        }

        try:
            return render_to_string('wireviz/settings_panel.html', context=ctx, request=request)
        except Exception as exp:
            return f"""
                <div class='panel-heading'>
                    <h4>Template Error</h4>
                </div>
                <div class='panel-content'>
                    <div class='alert alert-warning alert-block'>
                    {str(exp)}
                    </div>
                </div>
                """
