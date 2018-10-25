from __future__ import absolute_import, unicode_literals

from django.core.urlresolvers import reverse, reverse_lazy
from django.http import Http404
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic.edit import FormView, UpdateView, CreateView
from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth import login, REDIRECT_FIELD_NAME, authenticate, logout

from osf.models.user import OSFUser
from osf.models import AdminProfile, AbstractProvider
from admin.common_auth.forms import LoginForm, UserRegistrationForm, DeskUserForm
import logging
logger = logging.getLogger(__name__)

from osf.models.institution import Institution
import urllib
from framework.auth import get_or_create_user

class LoginView(FormView):
    form_class = LoginForm
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'login.html'

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = authenticate(
            username=form.cleaned_data.get('email').strip(),
            password=form.cleaned_data.get('password').strip()
        )
        if user is not None:
            login(self.request, user)
        else:
            messages.error(
                self.request,
                'Email and/or Password incorrect. Please try again.'
            )
            return redirect('auth:login')
        return super(LoginView, self).form_valid(form)

    def get_success_url(self):
        redirect_to = self.request.GET.get(self.redirect_field_name, '')
        if not redirect_to or redirect_to == '/':
            redirect_to = reverse('home')
        return redirect_to

class ShibLoginView(FormView):
    form_class = LoginForm
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'shib-login.html'

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        ''' TODO:
            add login from shibboleth:
            username -> request
        '''

        idp = request.environ['HTTP_AUTH_SHIB_IDENTITY_PROVIDER']
        institution = Institution.objects.filter(login_url__contains=idp)
        institution = Institution.objects.filter(login_url__contains=urllib.quote(idp, safe='')) if not institution else institution
        if not institution:
          print('Authentication failed: Invalid institution id specified "{}"'.format(idp))
          return redirect('auth:login')
        print(vars(institution))

        # user = request.user
        # if hasattr(user, 'affiliated_institutions') and user.affiliated_institutions.all():
        #   user.affiliated_institutions.add(institution)
        # else:
        #   print('Authentication failed: No affiliated institutions "{}"'.format(user.username))
        #   return redirect('auth:login')
 
        eppn = request.environ['HTTP_AUTH_EPPN']
        if not eppn:
          message = 'login failed: eppn required'
          print(message)
          return redirect('auth:login')
        eppn_user = OSFUser.objects.filter(username=eppn)
        if eppn_user:
          user_is_staff = hasattr(eppn_user, 'is_staff') and eppn_user.is_staff
          user_is_superuser = hasattr(eppn_user, 'is_superuser') and eppn_user.is_superuser
          if user_is_staff or user_is_superuser or "GakuninRDMAdmin" in request.environ['HTTP_AUTH_ENTITLEMENT']: 
            # login success
            # not sure about this code
            return super(ShibLoginView, self).dispatch(request, *args, **kwargs)
          else:
            # login failure occurs and the screen transits to the error screen
            # not sure about this code
            message = 'login failed: not staff or superuser'
            print(message)
            return redirect('auth:login')
        else:
          if "GakuninRDMAdmin" not in request.HTTP_AUTH_ENTITLEMENT:
            message = 'login failed: no user with matching eppn'
            print(message)
            return redirect('auth:login')
          else:
            new_user, created = get_or_create_user(request.environ['HTTP_AUTH_DISPLAYNAME'], eppn, is_staff=True)
            new_user.affiliated_institutions.add(institution)
            eppn_user = new_user

        auth.login(request, eppn_user)

        logger.info('ShibLoginView.dispatch.request.environ:{}'.format((request.environ)))
#       logger.info('ShibLoginView.dispatch.request.user:{}'.format(vars(request.user)))

        # Transit to the administrator's home screen
        # not sure about this code
        return super(ShibLoginView, self).dispatch(request, *args, **kwargs)   
 
    def form_valid(self, form):
        user = authenticate(
            username=form.cleaned_data.get('email').strip(),
            password=form.cleaned_data.get('password').strip()
        )
        if user is not None:
            login(self.request, user)
        else:
            messages.error(
                self.request,
                'Email and/or Password incorrect. Please try again.'
            )
            return redirect('auth:shib-login')
        return super(ShibLoginView, self).form_valid(form)

    def get_success_url(self):
        redirect_to = self.request.GET.get(self.redirect_field_name, '')
        if not redirect_to or redirect_to == '/':
            redirect_to = reverse('home')
        return redirect_to

def logout_user(request):
    logout(request)
    return redirect('auth:login')


class RegisterUser(PermissionRequiredMixin, FormView):
    form_class = UserRegistrationForm
    template_name = 'register.html'
    permission_required = 'osf.change_user'
    raise_exception = True

    def form_valid(self, form):
        osf_id = form.cleaned_data.get('osf_id')
        osf_user = OSFUser.load(osf_id)

        if not osf_user:
            raise Http404('OSF user with id "{}" not found. Please double check.'.format(osf_id))

        osf_user.is_staff = True
        osf_user.save()

        # create AdminProfile for this new user
        profile, created = AdminProfile.objects.get_or_create(user=osf_user)

        prereg_admin_group = Group.objects.get(name='prereg_admin')
        for group in form.cleaned_data.get('group_perms'):
            osf_user.groups.add(group)
            split = group.name.split('_')
            group_type = split[0]
            if group_type == 'reviews':
                provider_id = split[2]
                provider = AbstractProvider.objects.get(id=provider_id)
                provider.notification_subscriptions.get(event_name='new_pending_submissions').add_user_to_subscription(osf_user, 'email_transactional')
            if group == prereg_admin_group:
                administer_permission = Permission.objects.get(codename='administer_prereg')
                osf_user.user_permissions.add(administer_permission)

        osf_user.save()

        if created:
            messages.success(self.request, 'Registration successful for OSF User {}!'.format(osf_user.username))
        else:
            messages.success(self.request, 'Permissions update successful for OSF User {}!'.format(osf_user.username))
        return super(RegisterUser, self).form_valid(form)

    def get_success_url(self):
        return reverse('auth:register')

    def get_initial(self):
        initial = super(RegisterUser, self).get_initial()
        initial['osf_id'] = self.request.GET.get('id')
        return initial

class DeskUserCreateFormView(PermissionRequiredMixin, CreateView):
    form_class = DeskUserForm
    template_name = 'desk/settings.html'
    success_url = reverse_lazy('auth:desk')
    permission_required = 'osf.view_desk'
    raise_exception = True

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(DeskUserCreateFormView, self).form_valid(form)


class DeskUserUpdateFormView(PermissionRequiredMixin, UpdateView):
    form_class = DeskUserForm
    template_name = 'desk/settings.html'
    success_url = reverse_lazy('auth:desk')
    permission_required = 'osf.view_desk'
    raise_exception = True

    def get_object(self, queryset=None):
        return self.request.user.admin_profile
