import json
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.db.models import Q
from django.forms.fields import CharField
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView, DeleteView
from django.views.generic.list import ListView
from actstream.signals import action as actstream_action
from collab.mixins import SpacesMixin, SpaceAdminRequiredMixin
from .forms import UserCreationForm
from .models import MembersPlugin
User = get_user_model()

class ContextMixin(object):
    """
        Adds 
        * The name of this plugin
    """
    def get_context_data(self, **kwargs):
        context = super(ContextMixin, self).get_context_data(**kwargs)
        context['plugin_selected'] = MembersPlugin.name
        return context


class Index(ContextMixin, SpacesMixin, TemplateView):
    template_name = "spaces_members/index.html"

    def get_context_data(self, **kwargs):
        context = super(Index, self).get_context_data(**kwargs)
        members = self.request.SPACE.get_members().user_set.all()
        context['members'] = members
        context['space'] = self.request.SPACE
        return context

class CreateUser(ContextMixin, SpaceAdminRequiredMixin, FormView):
    """
        Creates a new user, adds user to the current Space, and sends off a
        welcome email for setting up a password.
    """
    form_class = UserCreationForm
    template_name ="spaces_members/create.html"
    success_url = reverse_lazy('spaces_members:index')


    def get_form_kwargs(self):
        kwargs = super(CreateUser, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def _add_user(self, form):
        email = form.data["email1"]
        user = User.objects.get(email=email)
        member_group = self.request.SPACE.get_members()
        user.groups.add(member_group)
        actstream_action.send(
            sender=self.request.user,
            verb=_("has been added to group"),
            target=self.request.SPACE,
            action_object=user
        )
        if "is_team" in form.data.keys():
            team = self.request.SPACE.get_team()
            user.groups.add(team)
        if "is_admin" in form.data.keys():
            admins = self.request.SPACE.get_admins()
            user.groups.add(admins)
 

    def form_invalid(self, form):
        # For better UX, intercept the edge case of the admin trying to
        # invite a user who is already on the platform, manually
        # add this user to the group and return with a success message:
        if len(form.errors.keys()) == 1 and ("email2" in form.errors.keys()):
            if form.errors["email2"].as_data()[0].code == "email_exists":
                self._add_user(form)
                return redirect(self.get_success_url())

        return super().form_invalid(form)

    def form_valid(self, form):
        new_user = form.save()
        actstream_action.send(
                sender=self.request.user,
                verb=_("was created"),
                target=self.request.SPACE,
                action_object=new_user
            )
        return redirect(self.get_success_url())


class AjaxUserSearch(SpaceAdminRequiredMixin, ListView):
    """
        Return a JSON-formatted list of users that fit the given search string.
    """
    model = User

    
    def dispatch(self, *args, **kwargs):
        keyword = CharField(required=False).clean(kwargs['keyword'])
        self.keyword = keyword
        return super(AjaxUserSearch, self).dispatch(*args, **kwargs)

    def render_to_json_response(self, context, **kwargs):
        """
        Returns a JSON response, transforming 'context' to make the payload.
        """
        return JsonResponse(
            {'users':context['users']},
            **kwargs
        )

    def render_to_response(self, context, **kwargs):
        return self.render_to_json_response(context, **kwargs)

    def get_queryset(self):
        qs = self.model.objects.filter(
            Q(username__icontains=self.keyword) |
            Q(first_name__icontains=self.keyword) |
            Q(last_name__icontains=self.keyword) |
            Q(email__icontains=self.keyword) 
        )
        # allow users to search for "firstname whitespace lastname")
        print("self.keyword:", self.keyword)
        if " " in self.keyword:
            split_keywords = self.keyword.split(" ")
            qs_split = self.model.objects.filter(
                Q(first_name__icontains=split_keywords[0]) &
                Q(last_name__icontains=split_keywords[1]) 
            )
            qs = qs | qs_split
        # exclude anonymous user
        qs = qs.exclude(id__lt=1) 
        # exclude existing members
        existing_members = self.request.SPACE.get_members().user_set.all()
        qs = qs.exclude(id__in=existing_members)[:10] 
        return qs

    def get_context_data(self, **kwargs):
        context = super(AjaxUserSearch, self).get_context_data( **kwargs)
        user_dictlist = [{  'username':obj.username, 
                            'avatar':obj.profile.avatar, 
                            'pk':obj.pk} for obj in self.get_queryset()]
        context['users'] = json.dumps(user_dictlist)
        return context

class AjaxUserAdd(SpacesMixin, View):
    """
    Make the given user a member of the current Space.
    """
    def post(self, request, *args, **kwargs):
        if request.is_ajax:
            if 'user_pk' in request.POST:
                user_pk = request.POST['user_pk']
                user = get_object_or_404(User, pk=user_pk)
                member_group = request.SPACE.get_members()
                user.groups.add(member_group)
                actstream_action.send(
                    sender=request.user,
                    verb=_("has been added to group"),
                    target=request.SPACE,
                    action_object=user
                )
                return JsonResponse(
                    {}
                )
            context = {'reason': 'No user_pk provided.'}
        context = {'reason':'This route is only accessible via ajax.'}
        return HttpResponse(json.dumps(context), 
            content_type='application/json', 
            status_code=400
        )


class NotReallyDelete(ContextMixin, SpacesMixin, SuccessMessageMixin, DeleteView):
    """
    Behaves like DeleteView, but just removes a user from the space.
    """
    model = User
    success_message = _("User was removed successfully.")
    success_url = reverse_lazy('spaces_members:index')
    pk_url_kwarg = "user_pk"
    template_name = "spaces_members/user_confirm_remove.html"

    def delete(self, request, *args, **kwargs):
        user = self.object = self.get_object()
        space = self.request.SPACE
        space.get_members().user_set.remove(user)
        space.get_team().user_set.remove(user)
        space.get_admins().user_set.remove(user)
        success_url = self.get_success_url()
        actstream_action.send(
                sender=request.user,
                verb=_("was removed from group"),
                target=request.SPACE,
                action_object=user
            )
        return redirect(success_url)


class AddRole(SpacesMixin, View):
    """
        Add the given user to  'team' group of current Space.
    """
    success_url = reverse_lazy('spaces_members:index')

    def post(self, request, *args, **kwargs):
        if not 'user_pk' in request.POST:
            messages.error(request, _("User was missing, could not promote."))
            return redirect(self.success_url)
        user = get_object_or_404(User, pk=request.POST['user_pk'])
        if 'role' in request.POST:
            role = request.POST['role']
        group = None
        if role == 'team':
            group = self.request.SPACE.get_team()
            success_msg = _("User has been added to Team successfully.")
            action_verb = _("has has been added to Team")
        elif role == 'admin':
            group = self.request.SPACE.get_admins()
            success_msg = _("User has been added to Administrators successfully.")
            action_verb = _("has has been added to Administrators")
        if group:
            user.groups.add(group)
            messages.success(request, success_msg)
            actstream_action.send(
                    sender=request.user,
                    verb=action_verb,
                    target=request.SPACE,
                    action_object=user
            )
        else:
            messages.error(request, _("Role was missing, could not promote user."))
        return redirect(self.success_url)

class RemoveRole(SpacesMixin, View):
    """
        Remove a role the given user had in the current space.
    """
    success_url = reverse_lazy('spaces_members:index')

    def post(self, request, *args, **kwargs):
        if not 'user_pk' in request.POST:
            messages.error(request, _("User was missing, could not demote."))
            return redirect(self.success_url)
        user = get_object_or_404(User, pk=request.POST['user_pk'])
        if 'role' in request.POST:
            role = request.POST['role']
        group = None
        if role == 'team':
            group = self.request.SPACE.get_team()
            msg = _("User was removed from Team successfully.")
            action_verb = _('has been removed from Team')
        elif role == 'admin':
            group = self.request.SPACE.get_admins()
            msg = _("User was removed from Administrators successfully.")
            action_verb = _('has been removed from Administrators.')
        if group:
            group.user_set.remove(user)
            messages.success(request, msg)
            actstream_action.send(
                    sender=request.user,
                    verb=action_verb,
                    target=request.SPACE,
                    action_object=user
            )
        else:
            messages.error(request, _("Role was missing, could not demote user."))
        return redirect(self.success_url)
    