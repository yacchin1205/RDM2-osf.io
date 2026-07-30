from rest_framework import status as http_status

from unittest import mock
import pytest

from framework.auth import Auth
from osf.models import OSFUser
from website import mails, settings
from website.project.views.contributor import (
    send_claim_email,
)
from api.institutions.authentication import NEW_USER_NO_NAME

from tests.base import (
    fake,
    OsfTestCase,
)
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    ProjectFactory,
)


### refer to tests/test_views.py:TestClaimViews
@pytest.mark.enable_implicit_clean
@pytest.mark.enable_quickfiles_creation
class TestInvite(OsfTestCase):

    def setUp(self):
        super(TestInvite, self).setUp()
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)
        self.given_name = fake.name()
        self.given_email = fake_email()
        self.user = self.project.add_unregistered_contributor(
            fullname=self.given_name,
            email=self.given_email,
            auth=Auth(user=self.referrer)
        )
        self.project.save()

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', False)
    def test_claim_user_not_login_by_eppn(self):
        url = self.project.web_url_for(
            'claim_user_login_by_eppn',
            uid=self.user._id,
            token='faketoken',
        )
        res = self.app.get(url, auth=self.referrer.auth, expect_errors=True)
        assert (res.status_code) == (http_status.HTTP_400_BAD_REQUEST)
        assert ('This URL does not support LOGIN_BY_EPPN=False') in (res.text)

    def _common_redirect_to_claim_user_login_by_eppn(self, user2):
        unclaimed_record = self.user.get_unclaimed_record(self.project._primary_key)
        token = unclaimed_record['token']
        # verify_url = '/user/eppn/{uid}/{pid}/claim/verify/{token}/'.format(
        #     uid=self.user._id,
        #     pid=self.project._id,
        #     token=token
        # )
        verify_url = self.project.web_url_for(
            'claim_user_login_by_eppn',
            uid=self.user._id,
            token=token,
        )
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url, auth=user2.auth)
        assert (res.status_code) == (302)
        assert (verify_url) in (res.headers.get('Location'))
        res2 = res.follow(auth=user2.auth)
        assert (res2.status_code) == (http_status.HTTP_200_OK)
        if user2.have_email:  # existing user
            assert (user2.username) in (res2.text)
            assert (user2.fullname) in (res2.text)
            assert (self.user.username) in (res2.text)
            assert (self.user.fullname) not in (res2.text)
        else:
            assert (self.user.username) in (res2.text)
            assert (self.user.fullname) in (res2.text)
            assert (user2.username) not in (res2.text)

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    def test_redirect_by_existing_user_to_claim_user_login_by_eppn(self):
        user2 = AuthUserFactory()
        user2.eppn = fake_email()  # fake ePPN
        user2.have_email = True
        user2.save()
        self._common_redirect_to_claim_user_login_by_eppn(user2)

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    def test_redirect_by_new_user_to_claim_user_login_by_eppn(self):
        user2 = AuthUserFactory()
        user2.fullname = NEW_USER_NO_NAME
        user2.have_email = False
        user2.save()
        self._common_redirect_to_claim_user_login_by_eppn(user2)

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    def test_claim_url_for_eppn_with_bad_token_returns_400(self):
        url = self.project.web_url_for(
            'claim_user_login_by_eppn',
            uid=self.user._id,
            token='badtoken',
        )
        res = self.app.get(url, auth=self.referrer.auth, expect_errors=400)
        assert (res.status_code) == (http_status.HTTP_400_BAD_REQUEST)
        assert ('The token in the URL is invalid or has expired.') in (res.text)

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    def test_cannot_claim_user_with_eppn_user_who_is_already_contributor(self):
        # user who is already a contirbutor to the project
        contrib = AuthUserFactory()
        self.project.add_contributor(contrib, auth=Auth(self.project.creator))
        self.project.save()
        # Claiming user goes to claim url, but contrib is already logged in
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(
            url,
            auth=contrib.auth,
        ).follow(
            auth=contrib.auth,
            expect_errors=True,
        )
        assert (res.status_code) == (http_status.HTTP_400_BAD_REQUEST)
        assert ('The logged-in user is already a contributor to this ') in (res.text)

    def _common_posting_to_claim_user_login_by_eppn(self, user2, send_mail, existing_user):
        if existing_user:
            expected_username = user2.username
            expected_fullname = user2.fullname
        else:
            expected_username = self.user.username
            if user2.fullname == NEW_USER_NO_NAME:
                expected_fullname = self.user.fullname
            else:
                expected_fullname = user2.fullname
        unclaimed_record = self.user.get_unclaimed_record(self.project._primary_key)
        token = unclaimed_record['token']
        verify_url = self.project.web_url_for(
            'claim_user_login_by_eppn',
            uid=self.user._id,
            token=token,
        )
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url, auth=user2.auth)
        assert (res.status_code) == (302)
        assert (verify_url) in (res.headers.get('Location'))

        with mock.patch('website.project.views.contributor.mapcore_sync_map_group') as mock1, \
             mock.patch('website.project.views.contributor.mapcore_sync_is_enabled') as mock2:
            mock2.return_value = True
            res2 = self.app.post(verify_url, auth=user2.auth)
        assert (mock1.call_count) == (1)
        assert (res2.status_code) == (302)
        assert (self.project.url) in (res2.headers.get('Location'))

        user2.reload()  # update have_email
        assert (user2.have_email)
        if existing_user:
            assert (send_mail.call_count) == (0)
        else:
            assert (send_mail.call_count) == (1)  # welcome

        user2_auth = Auth(OSFUser.objects.get(username=user2.username))
        res3 = res2.follow(auth=user2_auth)
        assert (res3.status_code) == (http_status.HTTP_200_OK)

        self.project.reload()
        self.user.reload()
        user2.reload()
        assert (self.user.fullname) == ('Deleted user')
        assert not (self.user.is_active)
        assert (self.project._primary_key) not in (self.user.unclaimed_records)
        assert (self.user) not in (self.project.contributors)
        assert (user2.username) == (expected_username)
        assert (user2.fullname) == (expected_fullname)
        assert (user2) in (self.project.contributors)
        assert (user2.emails.filter(address=self.given_email).exists())

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    @mock.patch('website.project.views.contributor.send_welcome')
    def test_posting_by_new_user_no_name_to_claim_user_login_by_eppn(self, send_mail):
        user2 = AuthUserFactory()
        user2.fullname = NEW_USER_NO_NAME
        user2.have_email = False
        user2.save()
        self._common_posting_to_claim_user_login_by_eppn(user2, send_mail,
                                                         False)

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    @mock.patch('website.project.views.contributor.send_welcome')
    def test_posting_by_new_user_to_claim_user_login_by_eppn(self, send_mail):
        user2 = AuthUserFactory()
        user2.fullname = 'not ' + NEW_USER_NO_NAME
        user2.have_email = False
        user2.save()
        self._common_posting_to_claim_user_login_by_eppn(user2, send_mail,
                                                         False)

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    @mock.patch('website.project.views.contributor.send_welcome')
    def test_posting_by_existing_user_to_claim_user_login_by_eppn(self, send_mail):
        user2 = AuthUserFactory()
        user2.eppn = fake_email()  # fake ePPN
        user2.have_email = True
        user2.save()
        self._common_posting_to_claim_user_login_by_eppn(user2, send_mail,
                                                         True)

    @mock.patch('website.project.views.contributor.LOGIN_BY_EPPN', True)
    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_email_to_given_email_for_eppn(self, send_mail):
        project = ProjectFactory()
        given_email = fake_email()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(project.creator),
        )
        project.save()
        claim_url = unreg_user.get_claim_url(project._primary_key, external=True)
        claimer_email = given_email.lower().strip()
        unclaimed_record = unreg_user.get_unclaimed_record(project._primary_key)
        referrer = OSFUser.load(unclaimed_record['referrer_id'])

        send_claim_email(email=given_email, unclaimed_user=unreg_user,
                         node=project)

        assert (send_mail.called)
        send_mail.assert_called_with(
            given_email,
            mails.INVITE_DEFAULT,
            user=unreg_user,
            referrer=referrer,
            node=project,
            claim_url=claim_url,
            email=claimer_email,
            fullname=unclaimed_record['name'],
            branded_service=None,
            can_change_preferences=False,
            logo=settings.OSF_LOGO,
            osf_contact_email=settings.OSF_CONTACT_EMAIL,
            login_by_eppn=True,  # checking mainly
        )
