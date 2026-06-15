"""Wireviz plugin for InvenTree.

Provides integration of "wireviz" into the InvenTree system:

- Render wireviz diagrams in the browser
- Extract and integrate bills of materials from wireviz diagrams
"""

import logging
import os

from django.conf import settings
from django.urls import path

from part.models import Part, PartCategory
from plugin import InvenTreePlugin
from plugin.mixins import ReportMixin, SettingsMixin, UrlsMixin, UserInterfaceMixin

from . import PLUGIN_VERSION

logger = logging.getLogger('inventree')


class WirevizPlugin(
    ReportMixin, SettingsMixin, UrlsMixin, UserInterfaceMixin, InvenTreePlugin
):
    """Wireviz plugin for InvenTree.

    - Provides a custom panel for rendering wireviz diagrams
    - Automatically renders wireviz diagrams when a .wireviz file is uploaded
    - Extract BOM information from the wireviz diagram
    """

    AUTHOR = 'Oliver Walters'
    DESCRIPTION = 'Wireviz plugin for InvenTree'
    VERSION = PLUGIN_VERSION

    MIN_VERSION = '0.12.0'

    NAME = 'Wireviz'
    SLUG = 'wireviz'
    TITLE = 'Wireviz Plugin'

    # Javascript file which renders custom plugin settings
    ADMIN_SOURCE = 'WirevizSettings.js'

    # Filenames and key constants
    HARNESS_SVG_FILE = 'wireviz_harness.svg'

    HARNESS_SRC_KEY = 'source_file'
    HARNESS_SVG_KEY = 'svg_file'
    HARNESS_BOM_KEY = 'bom_data'

    SETTINGS = {
        'CATEGORY_PARAMETER': {
            'name': 'Category Parameter',
            'description': 'Parameter used to specify wire harness categories',
            'model': 'common.parametertemplate',
            "model_filters": {
                "for_model": "partcategory"
            }
        },
        'HARNESS_GROUP_VIEWERS': {
            'name': 'Wire Harness Viewers',
            'description': 'Select user group who can view wire harnesses',
            'model': 'auth.group',
        },
        'HARNESS_GROUP_EDITORS': {
            'name': 'Wire Harness Editors',
            'description': 'Select user group who can edit wire harnesses',
            'model': 'auth.group',
        },
        'DELETE_OLD_FILES': {
            'name': 'Delete Old Files',
            'description': 'Delete old wireviz files when uploading a new wireviz file',
            'default': True,
            'validator': bool,
        },
        'EXTRACT_BOM': {
            'name': 'Extract BOM Data',
            'description': 'Automatically extract BOM data from wireviz diagrams',
            'default': True,
            'validator': bool,
        },
        'CLEAR_BOM_DATA': {
            'name': 'Clear BOM Data',
            'description': 'Clear existing BOM data when uploading a new wireviz diagram',
            'default': True,
            'validator': bool,
        },
        # TODO: Implement this feature in the future
        # 'ADD_IMAGES': {
        #     'name': 'Add Part Images',
        #     'description': 'Include part images in the wireviz diagram (not yet implemeted)',
        #     'default': True,
        #     'validator': bool,
        # },
    }

    def get_category_parameter_template(self):
        """Return the ParameterTemplate used to specify wire harness categories."""
        from common.models import ParameterTemplate

        if parameter_id := self.get_setting('CATEGORY_PARAMETER'):
            try:
                parameter = ParameterTemplate.objects.get(pk=parameter_id)
                return parameter
            except (ValueError, TypeError, ParameterTemplate.DoesNotExist):
                return None

        return None

    def does_category_indicate_harness(self, category):
        """Determine if the provided category (or its ancestors) indicate a wire harness.

        This check is used to determine if the Wireviz panel should be displayed for a given part,
        based on its category.
        """
        if not category:
            return False

        template = self.get_category_parameter_template()

        if not template:
            return False

        # Check if this category (or any parent category) has the specified parameter
        for cat in category.get_ancestors(include_self=True).order_by('-level'):
            parameter = cat.parameters_list.filter(template=template).first()

            if not parameter:
                continue

            return str(parameter.data).lower() in ['true', 'yes']

        # No matching parameter found in category or parent categories
        return False

    def get_admin_context(self) -> dict:
        """Return the context for the admin settings page."""
        ctx = {}

        return ctx

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

    def get_harness_category(self):
        """Return the wire harness category ID."""
        if category_id := self.get_setting('HARNESS_CATEGORY'):
            try:
                category = PartCategory.objects.get(pk=category_id)
                return category
            except PartCategory.DoesNotExist:
                logger.warning('Wireviz: Invalid wire harness category ID')
                return None

        return None

    def user_can_view_harness(self, user) -> bool:
        """Determine if the provided user can view wire harnesses."""
        if user.is_superuser:
            # Superuser can view everything
            return True

        if group_id := self.get_setting('HARNESS_GROUP_VIEWERS'):
            # View group is specified - user must be a member of this group
            return user.groups.filter(pk=group_id).exists()

        # No group specified - user can view wire harnesses
        return True

    def user_can_edit_harness(self, user) -> bool:
        """Determine if the provided user can edit wire harnesses."""
        if not self.user_can_view_harness(user):
            return False

        if user.is_superuser:
            # Superuser can edit everything
            return True

        if group_id := self.get_setting('HARNESS_GROUP_EDITORS'):
            # Edit group is specified - user must be a member of this group
            return user.groups.filter(pk=group_id).exists()

        # No group specified - user can edit wire harnesses
        return True

    def should_display_panel(self, part, build, user):
        """Determine if the wireviz panel should be displayed for the given part."""
        # Part is not a Part instance
        if not part or not isinstance(part, Part):
            return False

        # Part must be marked as an assembly item
        if not part.assembly:
            return False

        # Check if the user is in a group that can view wire harnesses
        if not self.user_can_view_harness(user):
            return False

        # If the part already has a wireviz diagram, show the panel
        if part.get_metadata('wireviz'):
            return True

        if build:
            # Beyond this point, if we are displaying for a build order, we do not display the panel
            return False

        # If the part category (or any parent category) indicates that this is a wire harness, show the panel
        return self.does_category_indicate_harness(part.category)

    def panel_context_from_instance(self, instance):
        """Return the context for the wireviz panel, based on the given instance."""
        part = self.get_part_from_instance(instance)

        context = {}

        if part and isinstance(part, Part):
            context['part'] = part

            # Get wireviz file information from part metadata
            wireviz_metadata = part.get_metadata('wireviz')

            if wireviz_metadata:
                svg_file = wireviz_metadata.get(self.HARNESS_SVG_KEY, None)
                bom_data = wireviz_metadata.get(self.HARNESS_BOM_KEY, None)
                src_file = wireviz_metadata.get(self.HARNESS_SRC_KEY, None)

                if svg_file:
                    context['wireviz_svg_file'] = os.path.join(
                        settings.MEDIA_URL, svg_file
                    )

                if src_file:
                    context['wireviz_source_file'] = os.path.join(
                        settings.MEDIA_URL, src_file
                    )

                if bom_data:
                    context['wireviz_bom_data'] = bom_data

                # Add warnings and errors
                context['wireviz_warnings'] = wireviz_metadata.get('warnings', None)
                context['wireviz_errors'] = wireviz_metadata.get('errors', None)

        return context

    def get_ui_dashboard_items(self, request, context=None, **kwargs):
        """Return custom dashboard items for the wireviz plugin."""
        user = getattr(request, 'user', None)

        items = []

        # Only show if user can *create* wireviz diagrams
        if self.user_can_edit_harness(user):
            items.append({
                'key': 'wireviz',
                'title': 'Create Wireviz Diagram',
                'description': 'Create a new wireviz diagram from the dashboard',
                'icon': 'ti:topology-star:outline',
                'source': self.plugin_static_file(
                    'WirevizDashboard.js:RenderWirevizDashboard'
                ),
            })

        return items

    def get_ui_panels(self, request, context=None, **kwargs):
        """Return custom UI panels for the wireviz plugin."""
        from build.models import Build

        context = context or {}

        target_model = context.get('target_model', None)
        target_id = context.get('target_id', None)

        panels = []
        part = None
        build = None

        if target_model == 'part':
            try:
                part = Part.objects.get(pk=target_id)
            except Part.DoesNotExist:
                part = None

        elif target_model == 'build':
            # Display on the "build" page too
            try:
                build = Build.objects.get(pk=target_id)
                part = build.part
            except Build.DoesNotExist:
                part = None

        if self.should_display_panel(part, build, request.user):
            ctx = self.panel_context_from_instance(part)

            ctx['part'] = part.pk
            ctx['can_edit'] = self.user_can_edit_harness(request.user) and not build

            panels.append({
                'key': 'wireviz',
                'title': 'Harness Diagram',
                'description': 'View wire harness diagram',
                'icon': 'ti:topology-star:outline',
                'context': ctx,
                'source': self.plugin_static_file('WirevizPanel.js:RenderWirevizPanel'),
            })

        return panels

    def setup_urls(self):
        """Setup URL patterns for the wireviz plugin."""
        from . import views

        return [
            path(
                'upload/', views.UploadWirevizView.as_view(), name='wireviz-file-upload'
            ),
            path(
                'delete/', views.DeleteWirevizView.as_view(), name='wireviz-file-delete'
            ),
        ]
