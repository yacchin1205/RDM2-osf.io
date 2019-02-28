# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-13 17:35
from __future__ import unicode_literals

import logging

from django.db import migrations, models
from django.core.paginator import Paginator

from addons.osfstorage.models import NodeSettings as OSFSNodeSettings, OsfStorageFolder
from osf.models import OSFUser, QuickFilesNode, Contributor
from osf.models.base import ensure_guid
from osf.models.quickfiles import get_quickfiles_project_title

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def add_quickfiles(*args, **kwargs):
    logger.info('Test...!')
    ids_without_quickfiles = list(OSFUser.objects.exclude(nodes_created__type=QuickFilesNode._typedmodels_type).values_list('id', flat=True))

    users_without_quickfiles = OSFUser.objects.filter(id__in=ids_without_quickfiles).order_by('id')
    total_quickfiles_to_create = users_without_quickfiles.count()

    logger.info('About to add a QuickFilesNode for {} users.'.format(total_quickfiles_to_create))

    paginated_users = Paginator(users_without_quickfiles, 1000)

    total_created = 0
    for page_num in paginated_users.page_range:
        quickfiles_to_create = []
        for user in paginated_users.page(page_num).object_list:
            quickfiles_to_create.append(
                QuickFilesNode(
                    title=get_quickfiles_project_title(user),
                    creator=user
                )
            )
            total_created += 1

        all_quickfiles = QuickFilesNode.objects.bulk_create(quickfiles_to_create)
        logger.info('Created {}/{} QuickFilesNodes'.format(total_created, total_quickfiles_to_create))
        logger.info('Preparing to create contributors and folders')

        contributors_to_create = []
        osfs_folders_to_create = []
        for quickfiles in all_quickfiles:
            ensure_guid(QuickFilesNode, quickfiles, True)
            osfs_folders_to_create.append(
                OsfStorageFolder(provider='osfstorage', name='', node=quickfiles)
            )

            contributors_to_create.append(
                Contributor(
                    user=quickfiles.creator,
                    node=quickfiles,
                    visible=True,
                    read=True,
                    write=True,
                    admin=True,
                    _order=0
                )
            )

        Contributor.objects.bulk_create(contributors_to_create)
        OsfStorageFolder.objects.bulk_create(osfs_folders_to_create)

        logger.info('Contributors and addons folders')
        logger.info('Adding storage addons')
        osfs_to_create = []
        for folder in osfs_folders_to_create:
            osfs_to_create.append(
                OSFSNodeSettings(owner=folder.node, root_node=folder)
            )

        OSFSNodeSettings.objects.bulk_create(osfs_to_create)

def remove_quickfiles(*args, **kwargs):
    QuickFilesNode.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0052_preprintprovider_share_publish_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuickFilesNode',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('osf.abstractnode',),
        ),
        migrations.AlterField(
            model_name='abstractnode',
            name='type',
            field=models.CharField(choices=[('osf.node', 'node'), ('osf.collection', 'collection'), ('osf.registration', 'registration'), ('osf.quickfilesnode', 'quickfilesnode')], db_index=True, max_length=255),
        ),
        migrations.RunPython(add_quickfiles, remove_quickfiles),
        migrations.RunSQL(
            [
                """
                CREATE UNIQUE INDEX one_quickfiles_per_user ON osf_abstractnode (creator_id, type, is_deleted)
                WHERE type='osf.quickfilesnode' AND is_deleted=FALSE;
                """
            ], [
                """
                DROP INDEX IF EXISTS one_quickfiles_per_user RESTRICT;
                """
            ]
        ),
    ]
