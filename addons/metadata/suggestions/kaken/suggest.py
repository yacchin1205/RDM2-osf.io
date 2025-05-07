"""
KAKEN suggestion functions using Elasticsearch
"""
import logging
from typing import List, Dict, Any

from ..utils import to_msfullname
from .elasticsearch import KakenElasticsearchService
from addons.metadata import settings

logger = logging.getLogger(__name__)


def suggest_kaken(key: str, keyword: str, node) -> List[Dict[str, Any]]:
    """
    Main suggestion function for KAKEN data using Elasticsearch

    Args:
        key: The suggestion key (e.g., 'kaken:kenkyusha_shimei')
        keyword: Search keyword for filtering
        node: OSF node object containing contributors with ERAD IDs

    Returns:
        List of suggestion dictionaries with 'key' and 'value' fields
    """
    # Check if KAKEN functionality is enabled
    if settings.KAKEN_ELASTIC_URI is None:
        logger.debug("KAKEN functionality disabled (KAKEN_ELASTIC_URI is None)")
        return []

    if not key.startswith('kaken:'):
        logger.warning(f"Invalid key format: {key}")
        return []

    filter_field_name = key[6:]  # Remove 'kaken:' prefix
    candidates = _kaken_candidates_for_node(node, **{filter_field_name: keyword})

    res = []
    for candidate in candidates:
        res.append({
            'key': key,
            'value': candidate,
        })
    return res


def kaken_candidates(user_erad: str, **pred) -> List[Dict[str, Any]]:
    """
    Get KAKEN candidates for a specific user's ERAD ID using Elasticsearch

    Args:
        user_erad: User's ERAD ID
        **pred: Additional filtering predicates (e.g., kenkyusha_shimei='keyword')

    Returns:
        List of candidate dictionaries with researcher/project data
    """
    # Check if KAKEN functionality is enabled
    if settings.KAKEN_ELASTIC_URI is None:
        logger.debug("KAKEN functionality disabled (KAKEN_ELASTIC_URI is None)")
        return []

    if not user_erad:
        logger.warning("Empty user_erad provided")
        return []

    logger.info(f"Searching KAKEN Elasticsearch with user_erad: {user_erad}, pred: {pred}")

    # Initialize Elasticsearch service
    es_service = KakenElasticsearchService(
        hosts=[settings.KAKEN_ELASTIC_URI],
        index_name=settings.KAKEN_ELASTIC_INDEX,
        analyzer_config=settings.KAKEN_ELASTIC_ANALYZER_CONFIG,
        **settings.KAKEN_ELASTIC_KWARGS
    )

    try:
        # Search for researcher by ERAD ID
        researcher_data = es_service.get_researcher_by_erad(user_erad)
        if not researcher_data:
            logger.info(f"No researcher found for ERAD ID: {user_erad}")
            return []

        # Transform researcher data to candidates
        candidates = _transform_researcher_to_candidates(researcher_data)

        # Apply filtering predicates
        filtered_candidates = []
        for candidate in candidates:
            target = True
            for filter_field_name, keyword in pred.items():
                if filter_field_name in candidate:
                    candidate_value = candidate[filter_field_name]
                    # Handle different types of values
                    if candidate_value is None:
                        target = False
                        break
                    elif isinstance(candidate_value, str):
                        if keyword.lower() not in candidate_value.lower():
                            target = False
                            break
                    elif isinstance(candidate_value, list):
                        # Check if keyword matches any item in the list
                        found = False
                        for item in candidate_value:
                            if isinstance(item, str) and keyword.lower() in item.lower():
                                found = True
                                break
                        if not found:
                            target = False
                            break
                    else:
                        # For other types, convert to string and check
                        if keyword.lower() not in str(candidate_value).lower():
                            target = False
                            break
                else:
                    logger.warning(f"Filter field {filter_field_name} not found in candidate: {candidate}")
                    target = False
                    break

            if target:
                filtered_candidates.append(candidate)

        logger.info(f"Found {len(filtered_candidates)} candidates for user_erad: {user_erad}")
        return filtered_candidates

    finally:
        es_service.close()


def _kaken_candidates_for_node(node, **pred) -> List[Dict[str, Any]]:
    """
    Get KAKEN candidates for all contributors in a node

    Args:
        node: OSF node object
        **pred: Filtering predicates

    Returns:
        Flattened list of candidates from all contributors
    """
    all_candidates = []

    for user in node.contributors:
        if user.erad is not None and user.erad != '':
            user_candidates = kaken_candidates(user.erad, **pred)
            all_candidates.extend(user_candidates)

    return all_candidates


def _transform_researcher_to_candidates(researcher_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Transform Elasticsearch researcher data to candidate format

    Args:
        researcher_data: Researcher data from Elasticsearch

    Returns:
        List of candidate dictionaries
    """
    candidates = []

    # Extract basic researcher information
    accn = researcher_data.get('accn', '')
    erad_id = researcher_data.get('id:person:erad', '')

    # Process researcher name
    researcher_name_info = _extract_name_info(researcher_data)

    # Process institution information
    institution_info = _extract_institution_info(researcher_data)

    # Process projects
    work_projects = researcher_data.get('work:project', [])
    if not isinstance(work_projects, list):
        work_projects = []

    # If no projects, create a basic researcher candidate
    if not work_projects:
        candidate = {
            'erad': erad_id[0] if isinstance(erad_id, list) else erad_id,
            'kadai_id': '',
            'nendo': '',
            'japan_grant_number': '',
            'funding_stream_code': '',
            'haibunkikan_cd': 'JSPS',
            'haibunkikan_mei': '独立行政法人日本学術振興会',
            'program_name_ja': '科学研究費助成事業',
            'program_name_en': '',
            'bunya_cd': '',
            'bunya_mei': '',
        }
        candidate.update(researcher_name_info)
        candidate.update(institution_info)
        candidates.append(candidate)
        return candidates

    # Process each project
    for project in work_projects:
        if not isinstance(project, dict):
            continue

        # Extract project IDs (may be multiple)
        project_ids = _extract_project_ids(project)

        # If no project IDs found, create one candidate with empty ID
        if not project_ids:
            project_ids = ['']

        # Create a candidate for each project ID
        for project_id in project_ids:
            # Remove KAKENHI-PROJECT- prefix if present
            if project_id.startswith('KAKENHI-PROJECT-'):
                project_id = project_id[len('KAKENHI-PROJECT-'):]

            candidate = {
                'erad': erad_id[0] if isinstance(erad_id, list) else erad_id,
                'kadai_id': project_id,
                'nendo': _extract_project_year(project),
                'japan_grant_number': _format_japan_grant_number(project_id),
                'funding_stream_code': '',
                'haibunkikan_cd': 'JSPS',
                'haibunkikan_mei': '独立行政法人日本学術振興会',
                'program_name_ja': '科学研究費助成事業',
                'program_name_en': '',
                'bunya_cd': '',
                'bunya_mei': '',
            }

            # Add researcher name information
            candidate.update(researcher_name_info)

            # Add institution information
            candidate.update(institution_info)

            # Add project title information
            project_title_info = _extract_project_title_info(project)
            candidate.update(project_title_info)

            candidates.append(candidate)

    return candidates


def _extract_name_info(researcher_data: Dict[str, Any]) -> Dict[str, str]:
    """Extract and format name information from researcher data"""
    name_info = {
        'kenkyusha_shimei': '',
        'kenkyusha_shimei_ja': '',
        'kenkyusha_shimei_en': '',
        'kenkyusha_shimei_ja_msfullname': '',
        'kenkyusha_shimei_en_msfullname': '',
    }

    # Process main name
    main_name = researcher_data.get('name', {})
    if isinstance(main_name, dict):
        name_info.update(_process_name_object(main_name, 'main'))

    # Process names array
    names = researcher_data.get('names', [])
    if isinstance(names, list):
        for name_obj in names:
            if isinstance(name_obj, dict):
                processed_name = _process_name_object(name_obj, 'names')
                # Use the first valid name found
                for key, value in processed_name.items():
                    if value and not name_info[key]:
                        name_info[key] = value

    # Build combined name formats
    if name_info['kenkyusha_shimei_ja'] and name_info['kenkyusha_shimei_en']:
        name_info['kenkyusha_shimei'] = f"{name_info['kenkyusha_shimei_ja']}||{name_info['kenkyusha_shimei_en']}"
    elif name_info['kenkyusha_shimei_ja']:
        name_info['kenkyusha_shimei'] = f"{name_info['kenkyusha_shimei_ja']}||"
    elif name_info['kenkyusha_shimei_en']:
        name_info['kenkyusha_shimei'] = f"||{name_info['kenkyusha_shimei_en']}"

    return name_info


def _process_name_object(name_obj: Dict[str, Any], source: str) -> Dict[str, str]:
    """Process a single name object from researcher data"""
    processed = {
        'kenkyusha_shimei_ja': '',
        'kenkyusha_shimei_en': '',
        'kenkyusha_shimei_ja_msfullname': '',
        'kenkyusha_shimei_en_msfullname': '',
    }

    # Extract human readable values
    human_readable = name_obj.get('humanReadableValue', [])
    if not isinstance(human_readable, list):
        human_readable = []

    # Extract family and given names
    family_names = name_obj.get('name:familyName', [])
    given_names = name_obj.get('name:givenName', [])

    if not isinstance(family_names, list):
        family_names = []
    if not isinstance(given_names, list):
        given_names = []

    # Process by language
    for lang in ['ja', 'en']:
        family_name = ''
        given_name = ''

        # Find family name for this language
        for fn in family_names:
            if isinstance(fn, dict) and fn.get('lang') == lang:
                family_name = fn.get('text', '').strip()
                break

        # Find given name for this language
        for gn in given_names:
            if isinstance(gn, dict) and gn.get('lang') == lang:
                given_name = gn.get('text', '').strip()
                break

        # Build name string
        if family_name and given_name:
            name_str = f"{family_name}|{given_name}"
            processed[f'kenkyusha_shimei_{lang}'] = name_str

            # Create MSFullName format
            name_dict = {
                'last': family_name,
                'middle': '',
                'first': given_name,
            }
            try:
                msfullname = to_msfullname(name_dict, lang)
                processed[f'kenkyusha_shimei_{lang}_msfullname'] = msfullname
            except ValueError as e:
                logger.warning(f"Error creating MSFullName for {lang}: {e}")

    return processed


def _get_current_affiliation(affiliations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Select the most current affiliation based on sequence number

    Args:
        affiliations: List of affiliation objects

    Returns:
        dict: Affiliation with smallest sequence number (most recent) or None
    """
    if not affiliations:
        return None

    # Find affiliation with smallest sequence number (most recent)
    min_sequence = float('inf')
    current_affiliation = None

    for affiliation in affiliations:
        if not isinstance(affiliation, dict):
            continue

        sequence = affiliation.get('sequence', float('inf'))
        if sequence < min_sequence:
            min_sequence = sequence
            current_affiliation = affiliation

    return current_affiliation


def _extract_institution_info(researcher_data: Dict[str, Any]) -> Dict[str, str]:
    """Extract institution information from researcher data"""
    institution_info = {
        'kenkyukikan_mei': '',
        'kenkyukikan_mei_ja': '',
        'kenkyukikan_mei_en': '',
    }

    # Get current affiliation from affiliations:history
    affiliations = researcher_data.get('affiliations:history', [])
    if isinstance(affiliations, list) and affiliations:
        # Select the most current affiliation based on dates
        affiliation = _get_current_affiliation(affiliations)
        if isinstance(affiliation, dict):
            institution = affiliation.get('affiliation:institution', {})
            if isinstance(institution, dict):
                human_readable = institution.get('humanReadableValue', [])
                if isinstance(human_readable, list):
                    for hr in human_readable:
                        if isinstance(hr, dict):
                            lang = hr.get('lang', '')
                            text = hr.get('text', '').strip()
                            if lang == 'ja':
                                institution_info['kenkyukikan_mei_ja'] = text
                            elif lang == 'en':
                                institution_info['kenkyukikan_mei_en'] = text

    # Build combined institution format
    if institution_info['kenkyukikan_mei_ja'] and institution_info['kenkyukikan_mei_en']:
        institution_info['kenkyukikan_mei'] = f"{institution_info['kenkyukikan_mei_ja']}|{institution_info['kenkyukikan_mei_en']}"
    elif institution_info['kenkyukikan_mei_ja']:
        institution_info['kenkyukikan_mei'] = f"{institution_info['kenkyukikan_mei_ja']}|"
    elif institution_info['kenkyukikan_mei_en']:
        institution_info['kenkyukikan_mei'] = f"|{institution_info['kenkyukikan_mei_en']}"

    return institution_info


def _extract_project_ids(project: Dict[str, Any]) -> List[str]:
    """Extract project IDs from project data (may be multiple)"""
    record_source = project.get('recordSource', {})
    if isinstance(record_source, dict):
        project_ids = record_source.get('id:project:kakenhi', [])
        # Handle both string and list cases
        if isinstance(project_ids, str):
            return [project_ids] if project_ids else []
        elif isinstance(project_ids, list):
            return [pid for pid in project_ids if isinstance(pid, str) and pid]
    return []


def _extract_project_year(project: Dict[str, Any]) -> str:
    """Extract project year from project data"""
    # Try to get year from project status
    project_status = project.get('projectStatus', {})
    if isinstance(project_status, dict):
        fiscal_year = project_status.get('fiscal:year', {})
        if isinstance(fiscal_year, dict):
            common_era_year = fiscal_year.get('commonEra:year', '')
            if common_era_year:
                return str(common_era_year)

    # Try to get year from since/until dates
    for date_field in ['since', 'until']:
        date_obj = project.get(date_field, {})
        if isinstance(date_obj, dict):
            fiscal_year = date_obj.get('fiscal:year', {})
            if isinstance(fiscal_year, dict):
                common_era_year = fiscal_year.get('commonEra:year', '')
                if common_era_year:
                    return str(common_era_year)

    return ''


def _format_japan_grant_number(project_id: str) -> str:
    """Format project ID as Japan grant number"""
    if not project_id:
        return ''
    if project_id.startswith('JP'):
        return project_id
    else:
        return f"JP{project_id}"


def _extract_project_title_info(project: Dict[str, Any]) -> Dict[str, str]:
    """Extract project title information from project data"""
    title_info = {
        'kadai_mei': '',
        'kadai_mei_ja': '',
        'kadai_mei_en': '',
    }

    # Extract title information
    titles = project.get('title', [])
    if not isinstance(titles, list):
        titles = []

    for title in titles:
        if isinstance(title, dict):
            human_readable = title.get('humanReadableValue', [])
            if isinstance(human_readable, list):
                for hr in human_readable:
                    if isinstance(hr, dict):
                        lang = hr.get('lang', '')
                        text = hr.get('text', '').strip()
                        if lang == 'ja':
                            title_info['kadai_mei_ja'] = text
                        elif lang == 'en':
                            title_info['kadai_mei_en'] = text

    # Build combined title format
    if title_info['kadai_mei_ja'] and title_info['kadai_mei_en']:
        title_info['kadai_mei'] = f"{title_info['kadai_mei_ja']}|{title_info['kadai_mei_en']}"
    elif title_info['kadai_mei_ja']:
        title_info['kadai_mei'] = f"{title_info['kadai_mei_ja']}|"
    elif title_info['kadai_mei_en']:
        title_info['kadai_mei'] = f"|{title_info['kadai_mei_en']}"

    return title_info