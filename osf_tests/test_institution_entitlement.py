from osf.models.institution_entitlement import InstitutionEntitlement
from .factories import InstitutionFactory, InstitutionEntitlementFactory, AuthUserFactory
import pytest


class TestInstitutionEntitlementModel:

    @pytest.mark.django_db
    def test_factory(self):
        institution = InstitutionFactory()
        user = AuthUserFactory()
        inst = InstitutionEntitlementFactory(institution=institution, login_availability=True, modifier=user)
        assert (inst.institution) == (institution)
        assert (inst.login_availability) == (True)
        assert (inst.modifier) == (user)

    @pytest.mark.django_db
    def test__init__(self):
        institution = InstitutionFactory()
        user = AuthUserFactory()
        institution_entitlement = InstitutionEntitlement(institution=institution, login_availability=True, modifier=user)
        assert (institution_entitlement.institution) == (institution)
        assert (institution_entitlement.login_availability) == (True)
        assert (institution_entitlement.modifier) == (user)

    @pytest.mark.django_db
    def test__unitcode__(self):
        institution = InstitutionFactory()
        user = AuthUserFactory()
        inst = InstitutionEntitlementFactory(institution=institution, login_availability=True, modifier=user)
        expectedResult = u'institution_{}:{}'.format(inst.institution._id, inst.entitlement)
        assert (inst.__unicode__()) == (expectedResult)
