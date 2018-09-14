from django.utils.translation import ugettext as _
from spaces.models import Space,SpacePluginRegistry, SpacePlugin


class SpacesMembers(SpacePlugin):
    """
    Membership managemant for Django Spaces.
    This model only provides general metadata per space.
    """
    # active field (boolean) inherited from SpacePlugin
    # space field (foreignkey) inherited from SpacePlugin
    reverse_url = 'spaces_members:index'


class MembersPlugin(SpacePluginRegistry):
    """
    Provide a Members plugin for Spaces. This makes the SpacesMembers class visible 
    to the plugin system.
    """
    name = 'spaces_members'
    title = _('Members')
    plugin_model = SpacesMembers
