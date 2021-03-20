from osf.models import RdmAddonOption
from osf.models.region_external_account import RegionExternalAccount
from addons.osfstorage.models import Region
from addons.onedrivebusiness import SHORT_NAME


def get_region_external_account(node):
    user = node.creator
    institution = user.affiliated_institutions.first()
    addon_option = RdmAddonOption.objects.filter(
        provider=SHORT_NAME,
        institution_id=institution.id,
        is_allowed=True
    ).first()
    if addon_option is None:
        return None
    region = Region.objects.get(_id=institution._id)
    return RegionExternalAccount.objects.get(region=region)
