# -*- coding: utf-8 -*-
"""
Tests for KAKEN suggestion module
"""
import mock
from nose.tools import *  # noqa
from elasticsearch.exceptions import ConnectionError as ESConnectionError, ConnectionTimeout

from tests.base import OsfTestCase
from osf_tests.factories import UserFactory, ProjectFactory

from addons.metadata.suggestions.kaken import kaken_candidates
from addons.metadata.suggestions.kaken.suggest import _kaken_candidates_for_node


class TestKakenSuggestion(OsfTestCase):
    """Test KAKEN suggestion functionality"""

    def setUp(self):
        super(TestKakenSuggestion, self).setUp()
        self.user = UserFactory()
        self.user.erad = '12345678'
        self.user.save()

        self.project = ProjectFactory(creator=self.user)
        self.project.save()

    def tearDown(self):
        self.project.delete()
        self.user.delete()
        super(TestKakenSuggestion, self).tearDown()

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', None)
    def test_suggest_kaken_disabled_when_uri_is_none(self):
        """Test that suggest_kaken returns empty list when KAKEN_ELASTIC_URI is None"""
        from addons.metadata.suggestions.kaken.suggest import suggest_kaken

        result = suggest_kaken('kaken:kenkyusha_shimei', 'test', self.project)
        assert_equal(result, [])

    @mock.patch('addons.metadata.settings.KAKEN_ELASTIC_URI', None)
    def test_kaken_candidates_disabled_when_uri_is_none(self):
        """Test that kaken_candidates returns empty list when KAKEN_ELASTIC_URI is None"""
        result = kaken_candidates('12345678')
        assert_equal(result, [])

    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_kaken_candidates_when_index_does_not_exist(self, mock_es_service):
        """Test that kaken_candidates returns empty list when index doesn't exist"""
        mock_es = mock.MagicMock()
        mock_es.get_researcher_by_erad.return_value = None
        mock_es.close.return_value = None
        mock_es_service.return_value = mock_es

        result = kaken_candidates('12345678')
        assert_equal(result, [])

    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_elasticsearch_unavailable(self, mock_es_service):
        """Test behavior when Elasticsearch service is unavailable"""
        mock_es = mock.MagicMock()
        mock_es.get_researcher_by_erad.side_effect = ESConnectionError('Connection refused')
        mock_es.close.return_value = None
        mock_es_service.return_value = mock_es

        # Service unavailability should be visible to caller
        assert_raises(ESConnectionError, kaken_candidates, '12345678')

    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_elasticsearch_timeout(self, mock_es_service):
        """Test behavior when Elasticsearch request times out"""
        mock_es = mock.MagicMock()
        mock_es.get_researcher_by_erad.side_effect = ConnectionTimeout('Request timed out')
        mock_es.close.return_value = None
        mock_es_service.return_value = mock_es

        assert_raises(ConnectionTimeout, kaken_candidates, '12345678')

    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_retrieves_researcher_data(self, mock_es_service):
        """Test successful retrieval of researcher data"""
        mock_es = mock.MagicMock()
        mock_es.get_researcher_by_erad.return_value = {
            'work:project': [{
                'recordSource': {'id:project:kakenhi': '12345678'},
                'title': [{'humanReadableValue': [{'text': 'Test Project', 'lang': 'ja'}]}]
            }]
        }
        mock_es.close.return_value = None
        mock_es_service.return_value = mock_es

        result = kaken_candidates('12345678')

        assert_equal(len(result), 1)
        assert_equal(result[0]['kadai_id'], '12345678')

    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_no_matching_researchers(self, mock_es_service):
        """Test when no researchers match the ERAD ID"""
        mock_es = mock.MagicMock()
        mock_es.get_researcher_by_erad.return_value = None
        mock_es.close.return_value = None
        mock_es_service.return_value = mock_es

        result = kaken_candidates('99999999')

        assert_equal(result, [])

    @mock.patch('addons.metadata.suggestions.kaken.suggest.kaken_candidates')
    def test_node_level_service_failure(self, mock_kaken_candidates):
        """Test that service failures affect node-level searches"""
        mock_kaken_candidates.side_effect = ESConnectionError('Service unavailable')

        # Service failure should affect the whole operation
        assert_raises(ESConnectionError, _kaken_candidates_for_node, self.project)


# Sample real KAKEN researcher data with dummy personal information
SAMPLE_KAKEN_RESEARCHER = {
    "accn": "id:person:kakenhi**12345",
    "id:person:erad": ["12345678"],
    "recordSource": {
        "id:person:kakenhi": ["12345", "67890"]
    },
    "name": {
        "humanReadableValue": [
            {"text": "山田 太郎", "lang": "ja"},
            {"text": "YAMADA Taro", "lang": "en"}
        ],
        "name:familyName": [
            {"text": "山田", "lang": "ja"},
            {"text": "YAMADA", "lang": "en"}
        ],
        "name:givenName": [
            {"text": "太郎", "lang": "ja"},
            {"text": "Taro", "lang": "en"}
        ]
    },
    "affiliations:history": [
        {
            "sequence": 1,
            "since": {"commonEra:year": 1999, "month": 4, "day": 1},
            "until": {"commonEra:year": 2001, "month": 4, "day": 1},
            "affiliation:institution": {
                "humanReadableValue": [
                    {"text": "テスト大学", "lang": "ja"},
                    {"text": "Test University", "lang": "en"}
                ]
            },
            "affiliation:department": {
                "humanReadableValue": [
                    {"text": "研究所", "lang": "ja"}
                ]
            },
            "affiliation:jobTitle": {
                "humanReadableValue": [
                    {"text": "教授", "lang": "ja"}
                ]
            }
        }
    ],
    "work:project": [
        {
            "recordSource": {
                "id:project:kakenhi": ["KAKENHI-PROJECT-11111111"]
            },
            "title": [
                {
                    "humanReadableValue": [
                        {"text": "テスト研究プロジェクト１", "lang": "ja"},
                        {"text": "Test Research Project 1", "lang": "en"}
                    ]
                }
            ],
            "since": {"fiscal:year": {"commonEra:year": "1989"}},
            "until": {"fiscal:year": {"commonEra:year": "1989"}},
            "category": [
                {
                    "humanReadableValue": [
                        {"text": "一般研究(C)", "lang": "ja"},
                        {"text": "Grant-in-Aid for General Scientific Research (C)", "lang": "en"}
                    ]
                }
            ],
            "institution": [
                {
                    "humanReadableValue": [
                        {"text": "テスト大学", "lang": "ja"},
                        {"text": "Test University", "lang": "en"}
                    ]
                }
            ]
        },
        {
            "recordSource": {
                "id:project:kakenhi": ["KAKENHI-PROJECT-22222222"]
            },
            "title": [
                {
                    "humanReadableValue": [
                        {"text": "テスト研究プロジェクト２", "lang": "ja"}
                    ]
                }
            ],
            "since": {"fiscal:year": {"commonEra:year": "1990"}},
            "until": {"fiscal:year": {"commonEra:year": "1990"}}
        }
    ],
    "_source_url": "https://nrid.nii.ac.jp/nrid/1000012345678.json"
}


class TestKakenWithSampleData(OsfTestCase):
    """Tests for processing KAKEN data with sample data structures"""

    def setUp(self):
        super(TestKakenWithSampleData, self).setUp()
        from addons.metadata.suggestions.kaken.transformer import KakenToElasticsearchTransformer
        self.transformer = KakenToElasticsearchTransformer()
        self.user = UserFactory()
        self.user.erad = '12345678'
        self.user.save()
        self.project = ProjectFactory(creator=self.user)
        self.project.save()

    def tearDown(self):
        self.project.delete()
        self.user.delete()
        super(TestKakenWithSampleData, self).tearDown()

    def test_transform_sample_researcher_data(self):
        """Test transforming sample KAKEN researcher data structure"""
        # Transform the data
        es_doc = self.transformer.transform_researcher(SAMPLE_KAKEN_RESEARCHER)

        # Verify basic structure is preserved
        assert_equal(es_doc['accn'], 'id:person:kakenhi**12345')
        assert_equal(es_doc['id:person:erad'], ['12345678'])
        assert_in('_source_url', es_doc)

        # Verify search_text is generated
        assert_in('search_text', es_doc)
        assert_in('山田 太郎', es_doc['search_text'])
        assert_in('YAMADA Taro', es_doc['search_text'])
        assert_in('テスト大学', es_doc['search_text'])
        assert_in('テスト研究プロジェクト１', es_doc['search_text'])

    @mock.patch('addons.metadata.suggestions.kaken.elasticsearch.Elasticsearch')
    def test_index_and_retrieve_researcher(self, mock_es_class):
        """Test indexing and retrieving researcher data"""
        from addons.metadata.suggestions.kaken.elasticsearch import KakenElasticsearchService

        # Setup mock Elasticsearch
        mock_es = mock.MagicMock()
        mock_es_class.return_value = mock_es

        # Mock search response
        mock_es.search.return_value = {
            'hits': {
                'total': 1,
                'hits': [{
                    '_source': SAMPLE_KAKEN_RESEARCHER
                }]
            }
        }

        # Initialize service (connection details don't matter since ES is mocked)
        es_service = KakenElasticsearchService(
            hosts=['http://test:9200'],
            index_name='test_kaken'
        )

        # Index the document
        transformed = self.transformer.transform_researcher(SAMPLE_KAKEN_RESEARCHER)
        es_service.index_researcher(transformed)

        # Verify indexing was called
        mock_es.index.assert_called_once()
        call_args = mock_es.index.call_args
        assert_equal(call_args[1]['index'], 'test_kaken')
        assert_equal(call_args[1]['body'], transformed)

        # Retrieve by ERAD ID
        result = es_service.get_researcher_by_erad('12345678')

        # Verify result
        assert_is_not_none(result)
        assert_equal(result['id:person:erad'], ['12345678'])

    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_kaken_candidates_generation_with_sample_structure(self, mock_service_class):
        """Test generating candidates from sample researcher data structure"""
        # Setup mock service
        mock_service = mock.MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_researcher_by_erad.return_value = SAMPLE_KAKEN_RESEARCHER
        mock_service.close.return_value = None

        # Get candidates
        candidates = kaken_candidates('12345678')

        # Should have one candidate per project
        assert_equal(len(candidates), 2)

        # Verify first candidate
        candidate1 = candidates[0]
        assert_equal(candidate1['erad'], '12345678')
        assert_equal(candidate1['kadai_id'], '11111111')
        assert_equal(candidate1['kenkyusha_shimei_ja'], '山田|太郎')
        assert_equal(candidate1['kenkyusha_shimei_en'], 'YAMADA|Taro')
        assert_in('テスト大学', candidate1['kenkyukikan_mei'])
        assert_equal(candidate1['nendo'], '1989')
        assert_equal(candidate1['japan_grant_number'], 'JP11111111')

        # Verify second candidate
        candidate2 = candidates[1]
        assert_equal(candidate2['kadai_id'], '22222222')
        assert_equal(candidate2['nendo'], '1990')

    @mock.patch('addons.metadata.suggestions.kaken.suggest.KakenElasticsearchService')
    def test_filtering_candidates_by_field(self, mock_service_class):
        """Test filtering candidates by various fields with sample data structure"""
        # Setup mock service
        mock_service = mock.MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_researcher_by_erad.return_value = SAMPLE_KAKEN_RESEARCHER
        mock_service.close.return_value = None

        # Test filtering by institution name
        candidates = kaken_candidates('12345678', kenkyukikan_mei='テスト')
        assert_equal(len(candidates), 2)  # Both projects should match

        # Test filtering by project title
        candidates = kaken_candidates('12345678', kadai_mei='プロジェクト２')
        assert_equal(len(candidates), 1)
        assert_equal(candidates[0]['kadai_id'], '22222222')

        # Test filtering by non-existent text
        candidates = kaken_candidates('12345678', kenkyusha_shimei='鈴木')
        assert_equal(len(candidates), 0)

    def test_transform_researcher_without_projects(self):
        """Test transforming researcher with no projects"""
        researcher_no_projects = dict(SAMPLE_KAKEN_RESEARCHER)
        researcher_no_projects['work:project'] = []

        # Transform the data
        es_doc = self.transformer.transform_researcher(researcher_no_projects)

        # Should still have basic data
        assert_equal(es_doc['accn'], 'id:person:kakenhi**12345')
        assert_in('search_text', es_doc)
        assert_in('山田 太郎', es_doc['search_text'])

    def test_transform_researcher_with_malformed_data(self):
        """Test transformer handles malformed data gracefully"""
        malformed_researcher = {
            'accn': 'test123',
            'id:person:erad': '99999999',  # String instead of list
            'name': {
                'humanReadableValue': 'Test Name'  # String instead of list
            },
            'work:project': None  # None instead of list
        }

        # Should not raise exception
        es_doc = self.transformer.transform_researcher(malformed_researcher)
        assert_equal(es_doc['accn'], 'test123')
        assert_in('search_text', es_doc)