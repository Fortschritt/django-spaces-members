from django.conf.urls import url
from spaces.urls import space_patterns
from .views import Index, CreateUser, AjaxUserSearch, AjaxUserAdd, NotReallyDelete, AddRole, RemoveRole

app_name = 'spaces_members'
urlpatterns = space_patterns(

    url(r'^members/$', Index.as_view(), name='index'),
    url(r'^members/create/$', CreateUser.as_view(), name='create'),
    url(r'^members/search/(?P<keyword>[_\-0-9A-Za-z]+)/$',
        AjaxUserSearch.as_view(), name='search'),
    url(r'^members/add/$', AjaxUserAdd.as_view(), name='add'),
    url(r'^members/remove/(?P<user_pk>[-\w]+)/$', NotReallyDelete.as_view(), name='remove'),
    url(r'^members/add_role/$', AddRole.as_view(), name='add_role'),
    url(r'^members/remove_role/$', RemoveRole.as_view(), name='remove_role'),
)