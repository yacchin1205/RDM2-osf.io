import jsonschema
from django.utils import timezone
from rest_framework import serializers as ser
from rest_framework import exceptions

from addons.twofactor.models import UserSettings as TwoFactorUserSettings
from api.base.exceptions import InvalidModelValueError, Conflict
from api.base.serializers import (
    BaseAPISerializer, JSONAPISerializer, JSONAPIRelationshipSerializer,
    VersionedDateTimeField, HideIfDisabled, IDField,
    Link, LinksField, TypeField, RelationshipField, JSONAPIListField,
    WaterbutlerLink, ShowIfCurrentUser,
)
from api.base.utils import absolute_reverse, get_user_auth, waterbutler_api_url_for, is_deprecated
from api.files.serializers import QuickFilesSerializer
from osf.exceptions import ValidationValueError, ValidationError
from osf.models import OSFUser, QuickFilesNode
from website.settings import MAILCHIMP_GENERAL_LIST, OSF_HELP_LIST, CONFIRM_REGISTRATIONS_BY_EMAIL
from osf.models.provider import AbstractProviderGroupObjectPermission
from website.profile.views import update_osf_help_mails_subscription, update_mailchimp_subscription
from api.users.schemas.utils import validate_user_json, from_json
from framework.auth.views import send_confirm_email


class QuickFilesRelationshipField(RelationshipField):

    def to_representation(self, value):
        relationship_links = super(QuickFilesRelationshipField, self).to_representation(value)
        quickfiles_guid = value.nodes_created.filter(type=QuickFilesNode._typedmodels_type).values_list('guids___id', flat=True).get()
        upload_url = waterbutler_api_url_for(quickfiles_guid, 'osfstorage')
        relationship_links['links']['upload'] = {
            'href': upload_url,
            'meta': {},
        }
        relationship_links['links']['download'] = {
            'href': '{}?zip='.format(upload_url),
            'meta': {},
        }
        return relationship_links


class SocialField(ser.DictField):
    def __init__(self, min_version, **kwargs):
        super(SocialField, self).__init__(**kwargs)
        self.min_version = min_version
        self.help_text = 'This field will change data formats after version {}'.format(self.min_version)

    def to_representation(self, value):
        old_social_string_fields = ['twitter', 'github', 'linkedIn']
        request = self.context.get('request')
        show_old_format = request and is_deprecated(request.version, self.min_version) and request.method == 'GET'
        if show_old_format:
            social = value.copy()
            for key in old_social_string_fields:
                if social.get(key):
                    social[key] = value[key][0]
                elif social.get(key) == []:
                    social[key] = ''
            value = social
        return super(SocialField, self).to_representation(value)


class UserSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'full_name',
        'given_name',
        'middle_names',
        'family_name',
        'id',
        'uid',
    ])
    writeable_method_fields = frozenset([
        'accepted_terms_of_service',
    ])
    non_anonymized_fields = ['type']
    id = IDField(source='_id', read_only=True)
    uid = IDField(source='id', read_only=True)
    type = TypeField()
    full_name = ser.CharField(source='fullname', required=True, label='Full name', help_text='Display name used in the general user interface', max_length=186)
    given_name = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    middle_names = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    family_name = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    suffix = HideIfDisabled(ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations'))
    date_registered = HideIfDisabled(VersionedDateTimeField(read_only=True))
    active = HideIfDisabled(ser.BooleanField(read_only=True, source='is_active'))
    timezone = HideIfDisabled(ser.CharField(required=False, help_text="User's timezone, e.g. 'Etc/UTC"))
    locale = HideIfDisabled(ser.CharField(required=False, help_text="User's locale, e.g.  'en_US'"))
    social = SocialField(required=False, min_version='2.10')
    employment = JSONAPIListField(required=False, source='jobs')
    education = JSONAPIListField(required=False, source='schools')
    can_view_reviews = ShowIfCurrentUser(ser.SerializerMethodField(help_text='Whether the current user has the `view_submissions` permission to ANY reviews provider.'))
    accepted_terms_of_service = ShowIfCurrentUser(ser.SerializerMethodField())

    links = HideIfDisabled(LinksField(
        {
            'html': 'absolute_url',
            'profile_image': 'profile_image_url',
        },
    ))

    nodes = HideIfDisabled(RelationshipField(
        related_view='users:user-nodes',
        related_view_kwargs={'user_id': '<_id>'},
        related_meta={'projects_in_common': 'get_projects_in_common'},
    ))

    quickfiles = HideIfDisabled(QuickFilesRelationshipField(
        related_view='users:user-quickfiles',
        related_view_kwargs={'user_id': '<_id>'},
    ))

    registrations = HideIfDisabled(RelationshipField(
        related_view='users:user-registrations',
        related_view_kwargs={'user_id': '<_id>'},
    ))

    institutions = HideIfDisabled(RelationshipField(
        related_view='users:user-institutions',
        related_view_kwargs={'user_id': '<_id>'},
        self_view='users:user-institutions-relationship',
        self_view_kwargs={'user_id': '<_id>'},
    ))

    preprints = HideIfDisabled(RelationshipField(
        related_view='users:user-preprints',
        related_view_kwargs={'user_id': '<_id>'},
    ))

    emails = ShowIfCurrentUser(RelationshipField(
        related_view='users:user-emails',
        related_view_kwargs={'user_id': '<_id>'},
    ))

    default_region = ShowIfCurrentUser(RelationshipField(
        related_view='regions:region-detail',
        related_view_kwargs={'region_id': 'get_default_region_id'},
        read_only=True,
    ))

    class Meta:
        type_ = 'users'

    def get_projects_in_common(self, obj):
        user = get_user_auth(self.context['request']).user
        if obj == user:
            return user.contributor_to.count()
        return obj.n_projects_in_common(user)

    def absolute_url(self, obj):
        if obj is not None:
            return obj.absolute_url
        return None

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'users:user-detail', kwargs={
                'user_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def get_can_view_reviews(self, obj):
        group_qs = AbstractProviderGroupObjectPermission.objects.filter(group__user=obj, permission__codename='view_submissions')
        return group_qs.exists() or obj.abstractprovideruserobjectpermission_set.filter(permission__codename='view_submissions')

    def get_default_region_id(self, obj):
        try:
            # use the annotated value if possible
            region_id = obj.default_region
        except AttributeError:
            # use computed property if region annotation does not exist
            region_id = obj.osfstorage_region._id
        return region_id

    def get_accepted_terms_of_service(self, obj):
        return bool(obj.accepted_terms_of_service)

    def profile_image_url(self, user):
        size = self.context['request'].query_params.get('profile_image_size')
        return user.profile_image_url(size=size)

    def validate_employment(self, value):
        validate_user_json(value, 'employment-schema.json')
        return value

    def validate_education(self, value):
        validate_user_json(value, 'education-schema.json')
        return value

    def validate_social(self, value):
        schema = from_json('social-schema.json')
        try:
            jsonschema.validate(value, schema)
        except jsonschema.ValidationError as e:
            raise InvalidModelValueError(e)

        return value

    def update(self, instance, validated_data):
        assert isinstance(instance, OSFUser), 'instance must be a User'
        for attr, value in validated_data.items():
            if 'social' == attr:
                for key, val in value.items():
                    instance.social[key] = val
            elif 'accepted_terms_of_service' == attr:
                if value and not instance.accepted_terms_of_service:
                    instance.accepted_terms_of_service = timezone.now()
            else:
                setattr(instance, attr, value)
        try:
            instance.save()
        except ValidationValueError as e:
            raise InvalidModelValueError(detail=e.message)
        except ValidationError as e:
            raise InvalidModelValueError(e)

        return instance

class UserAddonSettingsSerializer(JSONAPISerializer):
    """
    Overrides UserSerializer to make id required.
    """
    id = ser.CharField(source='config.short_name', read_only=True)
    user_has_auth = ser.BooleanField(source='has_auth', read_only=True)

    links = LinksField({
        'self': 'get_absolute_url',
        'accounts': 'account_links',
    })

    class Meta:
        type_ = 'user_addons'

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'users:user-addon-detail',
            kwargs={
                'provider': obj.config.short_name,
                'user_id': self.context['request'].parser_context['kwargs']['user_id'],
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def account_links(self, obj):
        # TODO: [OSF-4933] remove this after refactoring Figshare
        if hasattr(obj, 'external_accounts'):
            return {
                account._id: {
                    'account': absolute_reverse(
                        'users:user-external_account-detail', kwargs={
                            'user_id': obj.owner._id,
                            'provider': obj.config.short_name,
                            'account_id': account._id,
                            'version': self.context['request'].parser_context['kwargs']['version'],
                        },
                    ),
                    'nodes_connected': [n.absolute_api_v2_url for n in obj.get_attached_nodes(account)],
                }
                for account in obj.external_accounts.all()
            }
        return {}

class UserDetailSerializer(UserSerializer):
    """
    Overrides UserSerializer to make id required.
    """
    id = IDField(source='_id', required=True)


class UserQuickFilesSerializer(QuickFilesSerializer):
    links = LinksField({
        'info': Link('files:file-detail', kwargs={'file_id': '<_id>'}),
        'upload': WaterbutlerLink(),
        'delete': WaterbutlerLink(),
        'move': WaterbutlerLink(),
        'download': WaterbutlerLink(must_be_file=True),
    })


class ReadEmailUserDetailSerializer(UserDetailSerializer):

    email = ser.CharField(source='username', read_only=True)


class RelatedInstitution(JSONAPIRelationshipSerializer):
    id = ser.CharField(required=False, allow_null=True, source='_id')
    class Meta:
        type_ = 'institutions'

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url


class UserInstitutionsRelationshipSerializer(BaseAPISerializer):

    data = ser.ListField(child=RelatedInstitution())
    links = LinksField({
        'self': 'get_self_url',
        'html': 'get_related_url',
    })

    def get_self_url(self, obj):
        return absolute_reverse(
            'users:user-institutions-relationship', kwargs={
                'user_id': obj['self']._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def get_related_url(self, obj):
        return absolute_reverse(
            'users:user-institutions', kwargs={
                'user_id': obj['self']._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    class Meta:
        type_ = 'institutions'


class UserIdentitiesSerializer(JSONAPISerializer):
    id = IDField(source='_id', read_only=True)
    type = TypeField()
    external_id = ser.CharField(read_only=True)
    status = ser.CharField(read_only=True)

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'users:user-identities-detail',
            kwargs={
                'user_id': self.context['request'].parser_context['kwargs']['user_id'],
                'version': self.context['request'].parser_context['kwargs']['version'],
                'identity_id': obj['_id'],
            },
        )

    class Meta:
        type_ = 'external-identities'

class UserAccountExportSerializer(BaseAPISerializer):
    type = TypeField()

    class Meta:
        type_ = 'user-account-export-form'


class UserAccountDeactivateSerializer(BaseAPISerializer):
    type = TypeField()

    class Meta:
        type_ = 'user-account-deactivate-form'


class UserChangePasswordSerializer(BaseAPISerializer):
    type = TypeField()
    existing_password = ser.CharField(write_only=True, required=True)
    new_password = ser.CharField(write_only=True, required=True)

    class Meta:
        type_ = 'user_password'


class UserSettingsSerializer(JSONAPISerializer):
    id = IDField(source='_id', read_only=True)
    type = TypeField()
    two_factor_enabled = ser.SerializerMethodField()
    subscribe_osf_general_email = ser.SerializerMethodField()
    subscribe_osf_help_email = ser.SerializerMethodField()

    def get_two_factor_enabled(self, obj):
        try:
            two_factor = TwoFactorUserSettings.objects.get(owner_id=obj.id)
            return not two_factor.deleted
        except TwoFactorUserSettings.DoesNotExist:
            return False

    def get_subscribe_osf_general_email(self, obj):
        return obj.mailchimp_mailing_lists.get(MAILCHIMP_GENERAL_LIST, False)

    def get_subscribe_osf_help_email(self, obj):
        return obj.osf_mailing_lists.get(OSF_HELP_LIST, False)

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'users:user_settings',
            kwargs={
                'user_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    class Meta:
        type_ = 'user_settings'


class UserSettingsUpdateSerializer(UserSettingsSerializer):
    id = IDField(source='_id', required=True)
    two_factor_enabled = ser.BooleanField(write_only=True, required=False)
    two_factor_verification = ser.IntegerField(write_only=True, required=False)
    subscribe_osf_general_email = ser.BooleanField(read_only=False, required=False)
    subscribe_osf_help_email = ser.BooleanField(read_only=False, required=False)

    # Keys represent field names values represent the human readable names stored in DB.
    MAP_MAIL = {
        'subscribe_osf_help_email': OSF_HELP_LIST,
        'subscribe_osf_general_email': MAILCHIMP_GENERAL_LIST,
    }

    def update_email_preferences(self, instance, attr, value):
        if self.MAP_MAIL[attr] == OSF_HELP_LIST:
            update_osf_help_mails_subscription(user=instance, subscribe=value)
        else:
            update_mailchimp_subscription(instance, self.MAP_MAIL[attr], value)
        instance.save()

    def update_two_factor(self, instance, value, two_factor_addon):
        if value:
            if not two_factor_addon:
                two_factor_addon = instance.get_or_add_addon('twofactor')
                two_factor_addon.save()
        else:
            auth = get_user_auth(self.context['request'])
            instance.delete_addon('twofactor', auth=auth)

        return two_factor_addon

    def verify_two_factor(self, instance, value, two_factor_addon):
        if not two_factor_addon:
            raise exceptions.ValidationError(detail='Two-factor authentication is not enabled.')
        if two_factor_addon.verify_code(value):
            two_factor_addon.is_confirmed = True
        else:
            raise exceptions.PermissionDenied(detail='The two-factor verification code you provided is invalid.')
        two_factor_addon.save()

    def to_representation(self, instance):
        """
        Overriding to_representation allows using different serializers for the request and response.
        """
        context = self.context
        return UserSettingsSerializer(instance=instance, context=context).data

    def update(self, instance, validated_data):

        for attr, value in validated_data.items():
            if 'two_factor_enabled' == attr:
                two_factor_addon = instance.get_addon('twofactor')
                self.update_two_factor(instance, value, two_factor_addon)
            elif 'two_factor_verification' == attr:
                two_factor_addon = instance.get_addon('twofactor')
                self.verify_two_factor(instance, value, two_factor_addon)
            elif attr in self.MAP_MAIL.keys():
                self.update_email_preferences(instance, attr, value)

        return instance


class UserEmail(object):
    def __init__(self, email_id, address, confirmed, primary):
        self.id = email_id
        self.address = address
        self.confirmed = confirmed
        self.primary = primary


class UserEmailsSerializer(JSONAPISerializer):
    id = IDField(read_only=True)
    type = TypeField()
    email_address = ser.CharField(source='address')
    confirmed = ser.BooleanField(read_only=True)
    primary = ser.BooleanField(required=False)
    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        user = self.context['request'].user
        return absolute_reverse(
            'users:user-email-detail',
            kwargs={
                'user_id': user._id,
                'email_id': obj.id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    class Meta:
        type_ = 'user_emails'

    def create(self, validated_data):
        user = self.context['request'].user
        address = validated_data['address']
        if address in user.unconfirmed_emails or address in user.emails.all().values_list('address', flat=True):
            raise Conflict('This user already has registered with the email address {}'.format(address))
        try:
            token = user.add_unconfirmed_email(address)
            user.save()
            if CONFIRM_REGISTRATIONS_BY_EMAIL:
                send_confirm_email(user, email=address)
        except ValidationError as e:
            raise exceptions.ValidationError(e.args[0])

        return UserEmail(email_id=token, address=address, confirmed=False, primary=False)

    def update(self, instance, validated_data):
        user = self.context['request'].user
        primary = validated_data.get('primary', None)
        if primary and instance.confirmed:
            user.username = instance.address
            user.save()
        elif primary and not instance.confirmed:
            raise exceptions.ValidationError('You cannot set an unconfirmed email address as your primary email address.')
        return instance
