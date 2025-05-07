"""
KAKEN Elasticsearch Service

This module provides Elasticsearch integration for KAKEN researcher data,
including index management, document operations, and search functionality.
"""

from typing import Dict, List, Optional
import logging
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
logger = logging.getLogger(__name__)


class KakenElasticsearchService:
    """Elasticsearch service for KAKEN/NRID researcher data"""

    def __init__(self,
                 hosts: List[str],
                 index_name: str,
                 analyzer_config: Dict = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 retry_on_timeout: bool = True,
                 **kwargs):
        """
        Initialize Elasticsearch service

        Args:
            hosts: Elasticsearch host URLs (required)
            index_name: Index name for researcher data (required)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            retry_on_timeout: Whether to retry on timeout
            **kwargs: Additional Elasticsearch client options
        """
        if not hosts:
            raise ValueError("hosts is required")
        if not index_name:
            raise ValueError("index_name is required")

        self.hosts = hosts
        self.index_name = index_name
        self.analyzer_config = analyzer_config or {}
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_on_timeout = retry_on_timeout

        # Initialize Elasticsearch client
        self.client = self._create_client(**kwargs)

    def _create_client(self, **kwargs) -> Elasticsearch:
        """Create Elasticsearch client with configuration"""
        client_config = {
            'hosts': self.hosts,
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'retry_on_timeout': self.retry_on_timeout,
        }

        # Add additional configuration from kwargs
        client_config.update(kwargs)

        return Elasticsearch(**client_config)

    def create_index(self, delete_existing: bool = False):
        """
        Create Elasticsearch index with proper mapping

        Args:
            delete_existing: Whether to delete existing index
        """
        # Delete existing index if requested
        if delete_existing and self.index_exists():
            logger.info(f"Deleting existing index: {self.index_name}")
            self.client.indices.delete(index=self.index_name)

        # Check if index already exists
        if self.index_exists():
            logger.info(f"Index {self.index_name} already exists")
            return

        # Create index with mapping
        mapping = self._build_mapping()
        logger.info(f"Creating index: {self.index_name}")

        response = self.client.indices.create(
            index=self.index_name,
            body=mapping
        )

        logger.info(f"Index created successfully: {response}")

    def index_exists(self) -> bool:
        """Check if index exists"""
        return self.client.indices.exists(index=self.index_name)

    def _build_mapping(self) -> Dict:
        """Build Elasticsearch mapping for KAKEN researcher data"""
        # Default analyzer configuration
        default_analysis = {
            "analyzer": {
                "kuromoji_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["cjk_width", "lowercase"]
                }
            }
        }

        # Use provided analyzer configuration or default
        analysis_config = self.analyzer_config.get('analysis', default_analysis)

        return {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": analysis_config
            },
            "mappings": {
                "doc": {
                    "properties": {
                    "_source_url": {
                        "type": "keyword"
                    },
                    "accn": {
                        "type": "keyword"
                    },
                    "affiliations:history": {
                        "type": "nested",
                        "properties": {
                            "sequence": {"type": "integer"},
                            "since": {
                                "type": "object",
                                "properties": {
                                    "commonEra:year": {"type": "integer"},
                                    "month": {"type": "integer"},
                                    "day": {"type": "integer"}
                                }
                            },
                            "until": {
                                "type": "object",
                                "properties": {
                                    "commonEra:year": {"type": "integer"},
                                    "month": {"type": "integer"},
                                    "day": {"type": "integer"}
                                }
                            },
                            "affiliation:institution": {
                                "type": "object",
                                "properties": {
                                    "humanReadableValue": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                            "lang": {"type": "keyword"}
                                        }
                                    }
                                }
                            },
                            "affiliation:department": {
                                "type": "object",
                                "properties": {
                                    "humanReadableValue": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                            "lang": {"type": "keyword"}
                                        }
                                    }
                                }
                            },
                            "affiliation:jobTitle": {
                                "type": "object",
                                "properties": {
                                    "humanReadableValue": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                            "lang": {"type": "keyword"}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "id:person:erad": {
                        "type": "keyword"
                    },
                    "name": {
                        "type": "object",
                        "properties": {
                            "since": {
                                "type": "object",
                                "properties": {
                                    "commonEra:year": {"type": "integer"},
                                    "month": {"type": "integer"},
                                    "day": {"type": "integer"}
                                }
                            },
                            "until": {
                                "type": "object",
                                "properties": {
                                    "commonEra:year": {"type": "integer"},
                                    "month": {"type": "integer"},
                                    "day": {"type": "integer"}
                                }
                            },
                            "humanReadableValue": {
                                "type": "nested",
                                "properties": {
                                    "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                    "lang": {"type": "keyword"}
                                }
                            },
                            "name:familyName": {
                                "type": "nested",
                                "properties": {
                                    "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                    "lang": {"type": "keyword"}
                                }
                            },
                            "name:givenName": {
                                "type": "nested",
                                "properties": {
                                    "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                    "lang": {"type": "keyword"}
                                }
                            }
                        }
                    },
                    "names": {
                        "type": "nested",
                        "properties": {
                            "sequence": {"type": "integer"},
                            "since": {
                                "type": "object",
                                "properties": {
                                    "commonEra:year": {"type": "integer"},
                                    "month": {"type": "integer"},
                                    "day": {"type": "integer"}
                                }
                            },
                            "until": {
                                "type": "object",
                                "properties": {
                                    "commonEra:year": {"type": "integer"},
                                    "month": {"type": "integer"},
                                    "day": {"type": "integer"}
                                }
                            },
                            "humanReadableValue": {
                                "type": "nested",
                                "properties": {
                                    "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                    "lang": {"type": "keyword"}
                                }
                            },
                            "name:familyName": {
                                "type": "nested",
                                "properties": {
                                    "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                    "lang": {"type": "keyword"}
                                }
                            },
                            "name:givenName": {
                                "type": "nested",
                                "properties": {
                                    "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                    "lang": {"type": "keyword"}
                                }
                            }
                        }
                    },
                    "recordSource": {
                        "type": "object",
                        "properties": {
                            "id:person:kakenhi": {"type": "keyword"},
                            "id:project:kakenhi": {"type": "keyword"}
                        }
                    },
                    "relation:relatedResource": {
                        "type": "nested",
                        "properties": {
                            "id:project:kakenhi": {"type": "keyword"}
                        }
                    },
                    "work:project": {
                        "type": "nested",
                        "properties": {
                            "recordSource": {
                                "type": "object",
                                "properties": {
                                    "id:project:kakenhi": {"type": "keyword"}
                                }
                            },
                            "role": {
                                "type": "nested",
                                "properties": {
                                    "humanReadableValue": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                            "lang": {"type": "keyword"}
                                        }
                                    },
                                    "code:roleInProject:kakenhi": {"type": "keyword"}
                                }
                            },
                            "projectStatus": {
                                "type": "object",
                                "properties": {
                                    "statusCode": {"type": "keyword"},
                                    "fiscal:year": {
                                        "type": "object",
                                        "properties": {
                                            "commonEra:year": {"type": "keyword"},
                                            "firstDate:month": {"type": "integer"},
                                            "firstDate:day": {"type": "integer"}
                                        }
                                    }
                                }
                            },
                            "keyword": {
                                "type": "nested",
                                "properties": {
                                    "humanReadableValue": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "keyword"},
                                            "lang": {"type": "keyword"}
                                        }
                                    }
                                }
                            },
                            "since": {
                                "type": "object",
                                "properties": {
                                    "fiscal:year": {
                                        "type": "object",
                                        "properties": {
                                            "commonEra:year": {"type": "keyword"},
                                            "firstDate:month": {"type": "integer"},
                                            "firstDate:day": {"type": "integer"}
                                        }
                                    }
                                }
                            },
                            "until": {
                                "type": "object",
                                "properties": {
                                    "fiscal:year": {
                                        "type": "object",
                                        "properties": {
                                            "commonEra:year": {"type": "keyword"},
                                            "firstDate:month": {"type": "integer"},
                                            "firstDate:day": {"type": "integer"}
                                        }
                                    }
                                }
                            },
                            "title": {
                                "type": "nested",
                                "properties": {
                                    "humanReadableValue": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                            "lang": {"type": "keyword"}
                                        }
                                    }
                                }
                            },
                            "category": {
                                "type": "nested",
                                "properties": {
                                    "humanReadableValue": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                            "lang": {"type": "keyword"},
                                            "path": {"type": "keyword"},
                                            "niiCode": {"type": "keyword"}
                                        }
                                    }
                                }
                            },
                            "field": {
                                "type": "nested",
                                "properties": {
                                    "humanReadableValue": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                            "lang": {"type": "keyword"},
                                            "sequence": {"type": "integer"},
                                            "path": {"type": "keyword"},
                                            "niiCode": {"type": "keyword"},
                                            "fieldTable": {"type": "keyword"}
                                        }
                                    }
                                }
                            },
                            "institution": {
                                "type": "nested",
                                "properties": {
                                    "humanReadableValue": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                            "lang": {"type": "keyword"},
                                            "sequence": {"type": "integer"},
                                            "niiCode": {"type": "keyword"}
                                        }
                                    }
                                }
                            },
                            "member": {
                                "type": "nested",
                                "properties": {
                                    "sequence": {"type": "integer"},
                                    "role": {
                                        "type": "nested",
                                        "properties": {
                                            "code:roleInProject:kakenhi": {"type": "keyword"}
                                        }
                                    },
                                    "id:person:erad": {"type": "keyword"},
                                    "institution:name": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                            "lang": {"type": "keyword"}
                                        }
                                    },
                                    "department:name": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                            "lang": {"type": "keyword"}
                                        }
                                    },
                                    "jobTitle": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                            "lang": {"type": "keyword"}
                                        }
                                    },
                                    "person:name": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                            "lang": {"type": "keyword"}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "work:product": {
                        "type": "nested",
                        "properties": {
                            "accn": {"type": "keyword"},
                            "recordSource": {
                                "type": "object",
                                "properties": {
                                    "id:product:kakenhi": {"type": "keyword"}
                                }
                            },
                            "relation:relatedResource": {
                                "type": "nested",
                                "properties": {
                                    "id:project:kakenhi": {"type": "keyword"}
                                }
                            },
                            "resourceType": {"type": "keyword"},
                            "attribute:invited": {"type": "boolean"},
                            "attribute:jointInternationalResearch": {"type": "boolean"},
                            "title:main": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                    "lang": {"type": "keyword"}
                                }
                            },
                            "date:publicationDate": {
                                "type": "object",
                                "properties": {
                                    "humanReadableValue": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "keyword"}
                                        }
                                    },
                                    "commonEra:year": {"type": "integer"}
                                }
                            },
                            "contributor:organizer:unparsed": {
                                "type": "nested",
                                "properties": {
                                    "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                    "lang": {"type": "keyword"}
                                }
                            },
                            "creator:unparsed": {
                                "type": "nested",
                                "properties": {
                                    "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                    "lang": {"type": "keyword"}
                                }
                            },
                            "attribute:creator:candidate": {
                                "type": "nested",
                                "properties": {
                                    "estimated": {"type": "boolean"},
                                    "list": {
                                        "type": "nested",
                                        "properties": {
                                            "sequence": {"type": "integer"},
                                            "person:name": {
                                                "type": "nested",
                                                "properties": {
                                                    "text": {"type": "text", "analyzer": "kuromoji_analyzer"},
                                                    "lang": {"type": "keyword"}
                                                }
                                            },
                                            "accn": {"type": "keyword"}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "search_text": {
                        "type": "text",
                        "analyzer": "kuromoji_analyzer"
                    }
                    }
                }
            }
        }

    def index_researcher(self, researcher_data: Dict, document_id: str = None,
                        update_timestamp: str = None) -> bool:
        """
        Index a single researcher document

        Args:
            researcher_data: Researcher data dictionary
            document_id: Document ID (defaults to accn)
            update_timestamp: ISO timestamp for last update (if None, always update)

        Returns:
            True if indexing was successful
        """
        doc_id = document_id or researcher_data.get('accn')
        if not doc_id:
            logger.error("No document ID provided and no 'accn' field in data")
            return False

        # Create a copy to avoid modifying the original data
        data_to_index = researcher_data.copy()

        # Add last_updated timestamp to document
        if update_timestamp:
            data_to_index['_last_updated'] = update_timestamp

        # For Elasticsearch 6.x, use doc_type
        response = self.client.index(
            index=self.index_name,
            doc_type='doc',
            id=doc_id,
            body=data_to_index
        )

        logger.debug(f"Indexed document {doc_id}: {response['result']}")
        return True

    def delete_researcher(self, document_id: str) -> bool:
        """
        Delete a researcher document

        Args:
            document_id: Document ID to delete

        Returns:
            True if deletion was successful
        """
        try:
            response = self.client.delete(
                index=self.index_name,
                id=document_id
            )

            logger.debug(f"Deleted document {document_id}: {response['result']}")
            return True

        except NotFoundError:
            logger.warning(f"Document {document_id} not found for deletion")
            return True  # Consider not found as success

    def bulk_index(self, researchers: List[Dict], batch_size: int = 100,
                  update_timestamp: str = None) -> Dict:
        """
        Bulk index multiple researcher documents

        Args:
            researchers: List of researcher data dictionaries
            batch_size: Number of documents to process in each batch
            update_timestamp: ISO timestamp for last update (if None, always update)

        Returns:
            Dictionary with indexing results
        """
        results = {
            'success': 0,
            'errors': 0,
            'error_details': []
        }

        # Process in batches
        for i in range(0, len(researchers), batch_size):
            batch = researchers[i:i + batch_size]
            actions = []

            for researcher in batch:
                doc_id = researcher.get('accn')
                if not doc_id:
                    # If any document in batch is invalid, fail entire batch
                    error_msg = "No 'accn' field found in batch"
                    results['errors'] += len(batch)
                    results['error_details'].append(error_msg)
                    logger.error(f"Invalid document in batch: {error_msg}")
                    raise ValueError(error_msg)

                # Create a copy to avoid modifying the original data
                data_to_index = researcher.copy()

                # Add last_updated timestamp to document
                if update_timestamp:
                    data_to_index['_last_updated'] = update_timestamp

                actions.append({
                    '_index': self.index_name,
                    '_type': 'doc',  # For Elasticsearch 6.x
                    '_id': doc_id,
                    '_source': data_to_index
                })

            if actions:
                from elasticsearch.helpers import bulk
                success_count, error_details = bulk(
                    self.client,
                    actions,
                    index=self.index_name,
                    raise_on_error=False
                )

                # If any errors occurred in this batch, fail entire batch
                if len(error_details) > 0:
                    error_msg = f"Bulk indexing failed for batch {i//batch_size + 1}: {len(error_details)} errors"
                    results['errors'] += len(batch)
                    results['error_details'].extend(error_details)
                    logger.error(f"{error_msg}: {error_details}")
                    raise RuntimeError(error_msg)

                results['success'] += success_count
                logger.info(f"Bulk indexed batch {i//batch_size + 1}: {success_count} success")

        logger.info(f"Bulk indexing completed: {results['success']} success, {results['errors']} errors")
        return results

    def search_researchers(self, query: Dict, size: int = 10, from_: int = 0) -> Dict:
        """
        Search researchers using Elasticsearch query

        Args:
            query: Elasticsearch query dictionary
            size: Number of results to return
            from_: Starting offset

        Returns:
            Search results
        """
        # Warn and return empty results if index doesn't exist
        if not self.index_exists():
            logger.warning(f"KAKEN index '{self.index_name}' does not exist. Run data synchronization to create it.")
            return {'hits': {'total': 0, 'hits': []}}

        response = self.client.search(
            index=self.index_name,
            body=query,
            size=size,
            from_=from_
        )
        return response

    def get_researcher_by_accn(self, accn: str) -> Optional[Dict]:
        """
        Get researcher by accn (document ID)

        Args:
            accn: Researcher accn

        Returns:
            Researcher data or None if not found
        """
        try:
            response = self.client.get(
                index=self.index_name,
                id=accn,
                ignore=[404]  # Don't log 404 as warning
            )
            # Check if response is valid and has _source
            if response and '_source' in response:
                return response['_source']
            else:
                return None

        except NotFoundError:
            # This is expected when document doesn't exist
            return None

    def get_researcher_by_erad(self, erad_id: str) -> Optional[Dict]:
        """
        Get researcher by ERAD ID

        Args:
            erad_id: ERAD ID

        Returns:
            Researcher data or None if not found
        """
        query = {
            "query": {
                "term": {
                    "id:person:erad": erad_id
                }
            }
        }

        response = self.search_researchers(query, size=1)
        hits = response.get('hits', {}).get('hits', [])

        if hits:
            return hits[0]['_source']
        return None

    def refresh_index(self):
        """Refresh the index to make changes visible"""
        self.client.indices.refresh(index=self.index_name)
        logger.debug(f"Index {self.index_name} refreshed")

    def get_index_stats(self) -> Dict:
        """Get index statistics"""
        response = self.client.indices.stats(index=self.index_name)
        return response

    def close(self):
        """Close Elasticsearch client"""
        # Elasticsearch client doesn't need explicit closing
        pass