# -*- coding: utf-8 -*-
import csv
import io
import json
import logging
import mock
from mock import call
from nose.tools import *  # noqa

from tests.base import OsfTestCase

from addons.weko import schema


logger = logging.getLogger(__name__)


class TestWEKOSchema(OsfTestCase):

    def test_write_csv_minimal(self):
        buf = io.StringIO()
        index = mock.MagicMock()
        index.identifier = '1000'
        index.title = 'TITLE'
        files = [
            ('test.jpg', 'image/jpeg'),
        ]
        file_metadata = {
            'items': [
                {
                    'schema': 'TEST_SCHEMA',
                    'data': {
                        'grdm-file:pubdate': {
                            'value': '2023-06-17',
                        },
                        'grdm-file:Title.en': {
                            'value': 'ENGLISH TITLE',
                        },
                        'grdm-file:Description Abstract.ja': {
                            'value': '日本語説明',
                        },
                    },
                },
            ],
        }

        schema.write_csv(
            buf,
            index,
            files,
            'TEST_SCHEMA',
            file_metadata
        )

        logger.info(f'CSV: {buf.getvalue()}')
        buf.seek(0)
        reader = csv.reader(buf)
        lines = list(reader)
        assert_equal(len(lines), 6)
        assert_equal(lines[0], [
            '#ItemType',
            'デフォルトアイテムタイプ（フル）(15)',
            'https://localhost:8443/items/jsonschema/15',
        ])
        assert_equal(lines[1], [
            '.publish_status', '.metadata.path[0]', '.pos_index[0]', '.file_path[0]',
            '.metadata.item_1617605131499[0].filename', '.metadata.item_1617605131499[0].format',
            '.metadata.pubdate',
            '.metadata.item_1617186331708[1].subitem_1551255647225',
            '.metadata.item_1617186331708[1].subitem_1551255648112',
            '.metadata.item_1617186626617[0].subitem_description_type',
            '.metadata.item_1617186626617[0].subitem_description',
            '.metadata.item_1617186626617[0].subitem_description_language',
            '#.id', '.uri', '.feedback_mail[0]', '.cnri', '.doi_ra', '.doi', '.edit_mode',
        ])
        assert_equal(lines[2], [
            '.PUBLISH_STATUS',
            '.IndexID[0]', '.POS_INDEX[0]', '.ファイルパス[0]', 'File[0].表示名', 'File[0].フォーマット',
            '', '', '', '', '', '', '#ID', 'URI', '.FEEDBACK_MAIL[0]', '.CNRI', '.DOI_RA', '.DOI',
            'Keep/Upgrade Version',
        ])
        assert_equal(lines[3], [
            '', '', '', '', '', '', '', '', '', '', '', '', '#', '', '', '', '', '', '',
        ])
        assert_equal(lines[4], [
            'Required', 'Allow Multiple', 'Allow Multiple', 'Allow Multiple', 'Allow Multiple',
            'Allow Multiple', '', '', '', '', '', '', '#', '', 'Allow Multiple', '', '', '', 'Required',
        ])
        assert_equal(lines[5], [
            'private', '1000', 'TITLE', 'test.jpg', 'test.jpg', 'image/jpeg', '2023-06-17', 'ENGLISH TITLE',
            'en', 'Abstract', '日本語説明', 'ja', '', '', '', '', '', '', 'Keep',
        ])

    def test_write_csv_full(self):
        buf = io.StringIO()
        index = mock.MagicMock()
        index.identifier = '1000'
        index.title = 'TITLE'
        files = [
            ('test.jpg', 'image/jpeg'),
        ]
        file_metadata = {
            'items': [
                {
                    'schema': 'TEST_SCHEMA',
                    'data': {
                        'grdm-file:pubdate': {
                            'value': '2023-06-17',
                        },
                        'grdm-file:Title.en': {
                            'value': 'ENGLISH TITLE',
                        },
                        'grdm-file:Title.ja': {
                            'value': '日本語タイトル',
                        },
                        'grdm-file:Alternative Title.en': {
                            'value': 'ENGLISH ALTERNATIVE TITLE',
                        },
                        'grdm-file:Alternative Title.ja': {
                            'value': '日本語サブタイトル',
                        },
                        'grdm-file:Description Abstract.ja': {
                            'value': '日本語説明',
                        },
                        'grdm-file:Description Abstract.en': {
                            'value': 'ENGLISH DESCRIPTION',
                        },
                        'grdm-file:Rights Resource': {
                            'value': 'http://rights.resource.rcos.nii.ac.jp',
                        },
                        'grdm-file:Rights Description': {
                            'value': 'LONG DESCRIPTION FOR RIGHTS',
                        },
                        'grdm-file:Creator': {
                            'comments': [],
                            'extra': [],
                            'value': '[{"number": "XXXXXXXX", "name_ja": "情報 ビット", "name_en": "Bit Joho"}]',
                        },
                    },
                },
            ],
        }

        schema.write_csv(
            buf,
            index,
            files,
            'TEST_SCHEMA',
            file_metadata
        )

        logger.info(f'CSV: {buf.getvalue()}')
        buf.seek(0)
        reader = csv.reader(buf)
        lines = list(reader)
        assert_equal(len(lines), 6)
        logger.info(repr(lines))
        assert_equal(lines[0], [
            '#ItemType',
            'デフォルトアイテムタイプ（フル）(15)',
            'https://localhost:8443/items/jsonschema/15',
        ])
        assert_equal(lines[1], [
            '.publish_status', '.metadata.path[0]', '.pos_index[0]', '.file_path[0]',
            '.metadata.item_1617605131499[0].filename', '.metadata.item_1617605131499[0].format',
            '.metadata.pubdate', '.metadata.item_1617186331708[0].subitem_1551255647225',
            '.metadata.item_1617186331708[0].subitem_1551255648112',
            '.metadata.item_1617186331708[1].subitem_1551255647225',
            '.metadata.item_1617186331708[1].subitem_1551255648112',
            '.metadata.item_1617186385884[0].subitem_1551255720400',
            '.metadata.item_1617186385884[0].subitem_1551255721061',
            '.metadata.item_1617186385884[1].subitem_1551255720400',
            '.metadata.item_1617186385884[1].subitem_1551255721061',
            '.metadata.item_1617186419668[0].nameIdentifiers[0].nameIdentifierScheme',
            '.metadata.item_1617186419668[0].nameIdentifiers[0].nameIdentifier',
            '.metadata.item_1617186419668[0].creatorNames[0].creatorName',
            '.metadata.item_1617186419668[0].creatorNames[0].creatorNameLang',
            '.metadata.item_1617186419668[0].creatorNames[1].creatorName',
            '.metadata.item_1617186419668[0].creatorNames[1].creatorNameLang',
            '.metadata.item_1617186499011[0].subitem_1522650727486',
            '.metadata.item_1617186499011[0].subitem_1522651041219',
            '.metadata.item_1617186499011[0].subitem_1522650717957',
            '.metadata.item_1617186626617[0].subitem_description_type',
            '.metadata.item_1617186626617[0].subitem_description',
            '.metadata.item_1617186626617[0].subitem_description_language',
            '.metadata.item_1617186626617[1].subitem_description_type',
            '.metadata.item_1617186626617[1].subitem_description',
            '.metadata.item_1617186626617[1].subitem_description_language',
            '#.id', '.uri', '.feedback_mail[0]', '.cnri', '.doi_ra', '.doi', '.edit_mode',
        ])
        assert_equal(lines[2], [
            '.PUBLISH_STATUS', '.IndexID[0]', '.POS_INDEX[0]', '.ファイルパス[0]', 'File[0].表示名',
            'File[0].フォーマット', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
            '', '', '', '', '', '',
            '#ID', 'URI', '.FEEDBACK_MAIL[0]', '.CNRI', '.DOI_RA', '.DOI', 'Keep/Upgrade Version',
        ])
        assert_equal(lines[3], [
            '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
            '', '', '', '', '', '', '#', '', '', '', '', '', '',
        ])
        assert_equal(lines[4], [
            'Required', 'Allow Multiple', 'Allow Multiple', 'Allow Multiple', 'Allow Multiple', 'Allow Multiple',
            '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
            '#', '', 'Allow Multiple', '', '', '', 'Required',
        ])
        assert_equal(lines[5], [
            'private', '1000', 'TITLE', 'test.jpg', 'test.jpg', 'image/jpeg', '2023-06-17', '日本語タイトル', 'ja',
            'ENGLISH TITLE', 'en', '日本語サブタイトル', 'ja', 'ENGLISH ALTERNATIVE TITLE', 'en', 'e-Rad', 'XXXXXXXX',
            '情報 ビット', 'ja', 'Bit Joho', 'en', 'http://rights.resource.rcos.nii.ac.jp',
            'LONG DESCRIPTION FOR RIGHTS', 'en',
            'Abstract', '日本語説明', 'ja', 'Abstract', 'ENGLISH DESCRIPTION', 'en', '', '', '', '', '', '', 'Keep',
        ])

    def test_to_metadata(self):
        item_metadata = {
            '_item_metadata': {
                '_oai': {'id': 'oai:weko3.test.nii.ac.jp:00000063', 'sets': ['1678242084901']},
                'author_link': [],
                'control_number': '63',
                'item_1617186331708': {
                    'attribute_name': 'Title',
                    'attribute_value_mlt': [
                        {'subitem_1551255647225': '公開したいデータ', 'subitem_1551255648112': 'ja'},
                        {'subitem_1551255647225': 'AWESOME DATA TO BE PUBLISHED', 'subitem_1551255648112': 'en'}
                    ]
                },
                'item_1617186419668': {
                    'attribute_name': 'Creator',
                    'attribute_type': 'creator',
                    'attribute_value_mlt': [
                        {
                            'creatorNames': [
                                {'creatorName': '情報 ビット', 'creatorNameLang': 'ja'},
                                {'creatorName': 'Bit Joho', 'creatorNameLang': 'en'}
                            ],
                            'nameIdentifiers': [
                                {'nameIdentifier': 'XXXXXXXX', 'nameIdentifierScheme': 'e-Rad'}
                            ]
                        }
                    ]
                },
                'item_1617258105262': {
                    'attribute_name': 'Resource Type',
                    'attribute_value_mlt': [
                        {'resourcetype': 'dataset', 'resourceuri': 'http://purl.org/coar/resource_type/c_ddb1'}
                    ]
                },
                'item_1617605131499': {
                    'attribute_name': 'File',
                    'attribute_type': 'file',
                    'attribute_value_mlt': [
                        {
                            'accessrole': 'open_access',
                            'displaytype': 'simple',
                            'filename': 'DATA-TO-BE-PUBLISHED.dat',
                            'format': 'text/plain',
                            'mimetype': 'application/octet-stream',
                            'url': {
                                'url': 'https://weko3.test.nii.ac.jp/record/63/files/DATA-TO-BE-PUBLISHED.dat'
                            },
                            'version_id': 'd0025a85-c9fe-4cef-bdd3-282823b60af4'
                        }
                    ]
                },
                'item_1617186499011': {
                    'attribute_name': 'Rights',
                    'attribute_value_mlt': [
                        {
                            'subitem_1522650717957': 'en',
                            'subitem_1522650727486': 'http://opensource.org/licenses/MIT',
                            'subitem_1522651041219': 'LONG DESCRIPTION FOR RIGHTS'
                        }
                    ]
                },
                'item_1617186626617': {
                    'attribute_name': 'Description',
                    'attribute_value_mlt': [
                        {
                            'subitem_description': 'テストプロジェクトの説明',
                            'subitem_description_language': 'ja',
                            'subitem_description_type': 'Abstract'
                        }
                    ]
                },
                'item_title': '公開したいデータ',
                'item_type_id': '15',
                'owner': '1',
                'path': ['1678242084901'],
                'pubdate': {
                    'attribute_name': 'PubDate',
                    'attribute_value': '2023-05-29'
                },
                'publish_date': '2023-05-29', 'publish_status': '0',
                'relation_version_is_last': True,
                'title': ['公開したいデータ'],
                'weko_shared_id': -1
            }
        }
        metadata = schema.to_metadata('TEST_SCHEMA', {
            'metadata': item_metadata,
        })
        logger.info(f'Result: {metadata}')
        assert_equal(metadata, {
            'grdm-file:pubdate': {
                'comments': [], 'extra': [], 'value': '2023-05-29'
            },
            'grdm-file:Title.ja': {
                'comments': [], 'extra': [], 'value': '公開したいデータ'
            },
            'grdm-file:Title.en': {
                'comments': [], 'extra': [], 'value': 'AWESOME DATA TO BE PUBLISHED'
            },
            'grdm-file:Creator': {
                'comments': [],
                'extra': [],
                'value': '[{"number": "XXXXXXXX", "name_ja": "情報 ビット", "name_en": "Bit Joho"}]',
            },
            'grdm-file:Rights Resource': {
                'extra': [], 'comments': [], 'value': 'http://opensource.org/licenses/MIT',
            },
            'grdm-file:Rights Description': {
                'extra': [], 'comments': [], 'value': 'LONG DESCRIPTION FOR RIGHTS',
            },
            'grdm-file:Description Abstract.ja': {
                'extra': [], 'comments': [], 'value': 'テストプロジェクトの説明'
            },
            'grdm-file:resourcetype': {
                'comments': [], 'extra': [], 'value': 'dataset'
            },
        })
