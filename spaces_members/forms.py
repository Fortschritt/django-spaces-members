from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import ugettext as _

User = get_user_model()

class UserCreationForm(forms.ModelForm):
    """
    A form for creating a new user add adding her to the current Space.
    """
    subject_template_name = 'spaces_members/email/welcome_subject.txt'
    email_template_name = 'spaces_members/email/welcome_email.txt'
    html_email_template_name = None
    from_email = settings.SERVER_EMAIL

    error_messages = {
        'email_mismatch': _("The two email addresses didn't match."),
        'email_exists': _("A user with this email address already exists: %s"),
    }

    email1 = forms.EmailField(label=_("Email address"))
    email2 = forms.EmailField(label=_("Confirm email address"))
    message = forms.CharField(
        label=_("Personal message"),
        required=False,
        widget = forms.Textarea)
    is_team = forms.BooleanField(label=_("Assign Team role?"),required=False)
    is_admin = forms.BooleanField(label=_("Assign Admin role?"),required=False)

    class Meta:
        model = User
        fields = ('username',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super(UserCreationForm, self).__init__(*args, **kwargs)

    def clean_email2(self):
        email1 = self.cleaned_data.get("email1")
        email2 = self.cleaned_data.get("email2")
        if email1 and email2 and email1 != email2:
            raise forms.ValidationError(
                self.error_messages['email_mismatch'],
                code='email_mismatch',
            )
        user = User.objects.filter(email=email1)
        if user.exists():
            raise forms.ValidationError(
                self.error_messages['email_exists'] % user.first().username,
                code='email_exists',
            )
        return email2

    def set_roles(self, user, is_team=False, is_admin=False):
        space = self.request.SPACE
        user.groups.add(space.get_members())
        if is_team:
            user.groups.add(space.get_team())
        if is_admin:
            user.groups.add(space.get_admins())
            

    def save(self):
        user = super(UserCreationForm, self).save(commit=False)
        email = self.cleaned_data["email2"]
        user.email = email
        user.save()
        self.set_roles(
            user,
            is_team=self.cleaned_data.get("is_team"),
            is_admin=self.cleaned_data.get("is_admin")
        )
        # user created, now send a welcome mail with password reset token
        token_generator=default_token_generator
        current_site = get_current_site(self.request)
        site_name = current_site.name
        domain = current_site.domain
        context = {
            'email': user.email,
            'domain': domain,
            'site_name': site_name,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'username': user.username,
            'token': token_generator.make_token(user),
            'user_message': self.cleaned_data.get("message")
        }
        self.send_mail(context, self.from_email, user.email,
                       html_email_template_name=self.html_email_template_name)
        return user

    def send_mail(self,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Sends a django.core.mail.EmailMultiAlternatives to `to_email`.
        (Method is copied from django.contrib.auth.forms.SetPasswordForm)
        """
        subject = loader.render_to_string(self.subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(self.email_template_name, context)

        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if self.html_email_template_name is not None:
            html_email = loader.render_to_string(self.html_email_template_name, context)
            email_message.attach_alternative(html_email, 'text/html')

        email_message.send()
        # TODO: error handling if server didn't like the email?
        
        