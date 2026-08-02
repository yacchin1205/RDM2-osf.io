import pytest


from admin.spam.templatetags import spam_extras


@pytest.mark.django_db
class TestReverseTags:
    @pytest.fixture(autouse=True)
    def override_urlconf(self, settings):
        settings.ROOT_URLCONF = 'admin.base.urls'

    def test_reverse_spam_detail(self):
        res = spam_extras.reverse_spam_detail('123ab', page='2', status='4')
        assert ('/spam/123ab/?') in (res)
        assert ('page=2') in (res)
        assert ('status=4') in (res)
        assert (len('/spam/123ab/?page=2&status=4')) == (len(res))

    def test_reverse_spam_list(self):
        res = spam_extras.reverse_spam_list(page='2', status='4')
        assert ('/spam/?') in (res)
        assert ('page=2') in (res)
        assert ('status=4') in (res)
        assert (len('/spam/?page=2&status=4')) == (len(res))

    def test_reverse_spam_user(self):
        res = spam_extras.reverse_spam_user('kzzab', page='2', status='4')
        assert ('/spam/user/kzzab/?') in (res)
        assert ('page=2') in (res)
        assert ('status=4') in (res)
        assert (len('/spam/user/kzzab/?page=2&status=4')) == (len(res))
