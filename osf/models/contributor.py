from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from include import IncludeManager

from addons.iqbrims.apps import IQBRIMSAddonConfig
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.permissions import (
    READ,
    WRITE,
    ADMIN,
)
from website import settings


class AbstractBaseContributor(models.Model):
    objects = IncludeManager()

    primary_identifier_name = 'user__guids___id'

    read = models.BooleanField(default=False)
    write = models.BooleanField(default=False)
    admin = models.BooleanField(default=False)
    visible = models.BooleanField(default=False)
    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)

    def __repr__(self):
        return ('<{self.__class__.__name__}(user={self.user}, '
                'read={self.read}, write={self.write}, admin={self.admin}, '
                'visible={self.visible}'
                ')>').format(self=self)

    class Meta:
        abstract = True

    @property
    def bibliographic(self):
        return self.visible

    @property
    def permission(self):
        if self.admin:
            return 'admin'
        if self.write:
            return 'write'
        return 'read'

class Contributor(AbstractBaseContributor):
    node = models.ForeignKey('AbstractNode', on_delete=models.CASCADE)

    @property
    def _id(self):
        return '{}-{}'.format(self.node._id, self.user._id)

    class Meta:
        unique_together = ('user', 'node')
        # Make contributors orderable
        # NOTE: Adds an _order column
        order_with_respect_to = 'node'

class InstitutionalContributor(AbstractBaseContributor):
    institution = models.ForeignKey('Institution', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'institution')

class RecentlyAddedContributor(models.Model):
    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)  # the user who added the contributor
    contributor = models.ForeignKey('OSFUser', related_name='recently_added_by', on_delete=models.CASCADE)  # the added contributor
    date_added = NonNaiveDateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'contributor')

def get_contributor_permissions(contributor, as_list=True):
    perm = []
    if contributor.read:
        perm.append(READ)
    if contributor.write:
        perm.append(WRITE)
    if contributor.admin:
        perm.append(ADMIN)
    if as_list:
        return perm
    else:
        return perm[-1]


@receiver(post_save, sender=Contributor)
@receiver(post_delete, sender=Contributor)
def change_iqbrims_addon_enabled(sender, instance, **kwargs):
    from osf.models import Node, RdmAddonOption

    if IQBRIMSAddonConfig.short_name not in settings.ADDONS_AVAILABLE_DICT:
        return

    organizational_node = instance.node
    rdm_addon_options = RdmAddonOption.objects.filter(
        provider=IQBRIMSAddonConfig.short_name,
        is_allowed=True,
        management_node__isnull=False,
        organizational_node=organizational_node
    ).all()

    for rdm_addon_option in rdm_addon_options:
        for node in Node.find_by_institutions(rdm_addon_option.institution):
            if organizational_node.is_contributor(node.creator):
                node.add_addon(IQBRIMSAddonConfig.short_name, auth=None, log=False)
            else:
                node.delete_addon(IQBRIMSAddonConfig.short_name, auth=None)
