"""
KAKEN ResourceSync Client Script

This script provides functionality for testing and running
KAKEN ResourceSync client operations.

Usage:
    python3 -m scripts.update_kaken                  # Perform actual synchronization
    python3 -m scripts.update_kaken --dry-run        # Test synchronization
"""

import argparse
import sys
import logging
import django
import requests
from scripts import utils as script_utils

django.setup()

from website.app import init_app
from addons.metadata.suggestions.kaken.client import ResourceSyncClient
from addons.metadata.suggestions.kaken.transformer import KakenToElasticsearchTransformer
from addons.metadata.suggestions.kaken.elasticsearch import KakenElasticsearchService
from addons.metadata.models import KakenSyncLog

logger = logging.getLogger(__name__)






def sync_kaken_data(client: ResourceSyncClient, transformer: KakenToElasticsearchTransformer,
                   es_service: KakenElasticsearchService, dry_run: bool = False) -> bool:
    """
    Execute KAKEN data synchronization (supports incremental updates only)

    Args:
        client: ResourceSync client instance
        transformer: Data transformer instance
        es_service: Elasticsearch service instance
        dry_run: If True, only analyze what would be updated without making changes

    Returns:
        True if sync successful, False otherwise
    """
    try:
        if dry_run:
            print("Performing dry run analysis of KAKEN data synchronization...")
        else:
            print("Starting KAKEN data synchronization...")
        print(f"ResourceSync URL: {client.resourcesync_url}")

        # Determine if this is a resumption or new sync
        last_sync_log = KakenSyncLog.get_last_sync_log()
        if last_sync_log and last_sync_log.status != 'completed':
            print(f"Resuming previous sync (ID: {last_sync_log.id})")
            sync_log = last_sync_log
            sync_type = sync_log.sync_type
            processed_records = 0  # Reset for this execution
            errors_count = sync_log.errors_count
        else:
            # Determine sync type for new sync
            last_successful_sync = KakenSyncLog.get_last_successful_sync()
            if last_successful_sync is None:
                sync_type = 'initial'
                print("No previous sync found - performing initial sync")
            else:
                sync_type = 'incremental'
                print(f"Last successful sync: {last_successful_sync.completed_at} - performing incremental sync")

            # Don't create sync log for dry-run
            sync_log = None
            if not dry_run:
                sync_log = KakenSyncLog.start_sync(sync_type=sync_type)
                print(f"Started sync log (ID: {sync_log.id}, Type: {sync_type})")

            processed_records = 0
            errors_count = 0

        # Check if Elasticsearch index exists and create if needed
        if not dry_run and not es_service.index_exists():
            print("Creating Elasticsearch index for KAKEN data...")
            es_service.create_index()
            print("Index created successfully")

        # Get capabilities
        capabilities = client.get_capability_list()
        resourcelists = capabilities.get('resourcelists', [])
        changelists = capabilities.get('changelists', [])

        would_update_count = 0
        would_create_count = 0

        # Get batch processing limits
        from addons.metadata import settings
        max_documents = settings.KAKEN_SYNC_MAX_DOCUMENTS_PER_EXECUTION

        try:
            if sync_type == 'initial':
                # Initial sync: get all data from resourcelists
                print(f"\nProcessing {len(resourcelists)} resource lists...")

                # Resume from previous position if continuing
                start_index = sync_log.current_resourcelist_index if sync_log else 0

                for i in range(start_index, len(resourcelists)):
                    resourcelist_info = resourcelists[i]
                    resourcelist_url = resourcelist_info['url']
                    resourcelist_lastmod = resourcelist_info.get('lastmod')
                    print(f"\n[{i+1}/{len(resourcelists)}] Processing resource list: {resourcelist_url}")
                    if resourcelist_lastmod:
                        print(f"  Resource list lastmod: {resourcelist_lastmod}")

                    # Update progress
                    if sync_log:
                        sync_log.current_resourcelist_index = i
                        sync_log.current_resourcelist_url = resourcelist_url
                        sync_log.save()

                    batch_data = []
                    batch_count = 0

                    # Get total count first
                    total_urls = []
                    print(f"  Counting total documents...", end="", flush=True)
                    for json_url in client.process_resource_list(resourcelist_url):
                        total_urls.append(json_url)
                    print(f" {len(total_urls)} documents found")

                    # Resume from previous position if continuing
                    start_progress = sync_log.current_resourcelist_progress if sync_log else 0

                    for j, json_url in enumerate(total_urls):
                        if j < start_progress:
                            continue  # Skip already processed items

                        # Check batch processing limits
                        if processed_records >= max_documents:
                            print(f"\nReached maximum documents per execution ({max_documents}), stopping...")
                            # Process remaining batch before stopping
                            if not dry_run and batch_data:
                                update_timestamp = resourcelist_lastmod.isoformat() if resourcelist_lastmod else None
                                try:
                                    result = es_service.bulk_index(batch_data, update_timestamp=update_timestamp)
                                    errors_count += result['errors']
                                except Exception as e:
                                    error_msg = f"ERROR: Elasticsearch connection failed during bulk index: {e}"
                                    print(error_msg, file=sys.stderr)
                                    logger.exception("Elasticsearch connection error")
                                    raise
                            if sync_log:
                                sync_log.current_resourcelist_progress = j
                                sync_log.save()
                            return True
                        try:
                            # Get researcher data
                            researcher_data = client.fetch_researcher_data(json_url)

                            # Transform data
                            es_doc = transformer.transform_researcher(researcher_data)

                            if dry_run:
                                # Compare with existing data in dry-run
                                accn = es_doc.get('accn')
                                if accn:
                                    existing_doc = es_service.get_researcher_by_accn(accn)
                                    if existing_doc:
                                        # Compare with existing data's update time
                                        existing_lastmod = existing_doc.get('_last_updated')
                                        if existing_lastmod and resourcelist_lastmod:
                                            from dateutil.parser import parse as parse_datetime
                                            existing_dt = parse_datetime(existing_lastmod)
                                            if resourcelist_lastmod > existing_dt:
                                                would_update_count += 1
                                        else:
                                            would_update_count += 1
                                    else:
                                        would_create_count += 1
                                if dry_run:
                                    print(f"\r  Progress: [{j+1}/{len(total_urls)}]", end="", flush=True)
                            else:
                                batch_data.append(es_doc)

                            batch_count += 1
                            processed_records += 1

                            # Update progress
                            if sync_log:
                                sync_log.current_resourcelist_progress = j + 1
                                sync_log.documents_processed_in_batch = sync_log.documents_processed_in_batch + 1
                                if batch_count % 50 == 0:  # Save every 50 items
                                    sync_log.save()

                            # Batch processing
                            if not dry_run and len(batch_data) >= 100:
                                update_timestamp = resourcelist_lastmod.isoformat() if resourcelist_lastmod else None
                                try:
                                    result = es_service.bulk_index(batch_data, update_timestamp=update_timestamp)
                                    # processed_records already updated above, don't use success
                                    errors_count += result['errors']

                                    if result['errors'] > 0:
                                        warning_msg = f"WARNING: {result['errors']} errors in batch"
                                        print(warning_msg, file=sys.stderr)
                                except Exception as e:
                                    error_msg = f"ERROR: Elasticsearch connection failed during bulk index: {e}"
                                    print(error_msg, file=sys.stderr)
                                    logger.exception("Elasticsearch connection error")
                                    raise

                                batch_data = []
                                print(f"  Processed {j+1}/{len(total_urls)} researchers from this list")

                        except Exception as e:
                            error_msg = f"ERROR: processing {json_url}: {e}"
                            logger.exception(error_msg)
                            print(error_msg, file=sys.stderr)

                            # Save current position and stop on any error
                            if sync_log:
                                sync_log.current_resourcelist_progress = j  # Save current position
                                sync_log.save()
                            raise

                    # Process remaining batch
                    if not dry_run and batch_data:
                        update_timestamp = resourcelist_lastmod.isoformat() if resourcelist_lastmod else None
                        try:
                            result = es_service.bulk_index(batch_data, update_timestamp=update_timestamp)
                            # processed_records already updated above, don't use success
                            errors_count += result['errors']
                        except Exception as e:
                            error_msg = f"ERROR: Elasticsearch connection failed during bulk index: {e}"
                            print(error_msg, file=sys.stderr)
                            logger.exception("Elasticsearch connection error")
                            raise

                    if dry_run:
                        print(f"\n  Completed resource list {i+1}: {batch_count}/{len(total_urls)} researchers checked")
                    else:
                        print(f"  Completed resource list {i+1}: {batch_count}/{len(total_urls)} researchers")

                    # Reset progress when list is completed
                    if sync_log:
                        sync_log.current_resourcelist_progress = 0
                        sync_log.save()

                    # Update progress
                    if sync_log:
                        sync_log.update_progress(
                            processed_records=processed_records,
                            errors_count=errors_count
                        )

            else:
                # Incremental sync: get change data from changelists
                print(f"\nProcessing {len(changelists)} change lists...")

                last_sync = KakenSyncLog.get_last_successful_sync()
                since_time = last_sync.completed_at if last_sync else None

                # Resume from previous position if continuing
                start_index = sync_log.current_changelist_index if sync_log else 0

                for i in range(start_index, len(changelists)):
                    changelist_info = changelists[i]
                    changelist_url = changelist_info['url']
                    changelist_lastmod = changelist_info.get('lastmod')
                    print(f"\n[{i+1}/{len(changelists)}] Processing change list: {changelist_url}")
                    if changelist_lastmod:
                        print(f"  Change list lastmod: {changelist_lastmod}")

                    # Update progress
                    if sync_log:
                        sync_log.current_changelist_index = i
                        sync_log.current_changelist_url = changelist_url
                        sync_log.save()

                    batch_data = []
                    batch_count = 0

                    # Get total count first
                    total_changes = []
                    print(f"  Counting total changes...", end="", flush=True)
                    for action, json_url, lastmod in client.process_change_list(changelist_url, since=since_time):
                        total_changes.append((action, json_url, lastmod))
                    print(f" {len(total_changes)} changes found")

                    # Resume from previous position if continuing
                    start_progress = sync_log.current_changelist_progress if sync_log else 0

                    for j, (action, json_url, lastmod) in enumerate(total_changes):
                        if j < start_progress:
                            continue  # Skip already processed items

                        # Check batch processing limits
                        if processed_records >= max_documents:
                            print(f"\nReached maximum documents per execution ({max_documents}), stopping...")
                            # Process remaining batch before stopping
                            if not dry_run and batch_data:
                                update_timestamp = changelist_lastmod.isoformat() if changelist_lastmod else None
                                try:
                                    result = es_service.bulk_index(batch_data, update_timestamp=update_timestamp)
                                    errors_count += result['errors']
                                except Exception as e:
                                    error_msg = f"ERROR: Elasticsearch connection failed during bulk index: {e}"
                                    print(error_msg, file=sys.stderr)
                                    logger.exception("Elasticsearch connection error")
                                    raise
                            if sync_log:
                                sync_log.current_changelist_progress = j
                                sync_log.save()
                            return True
                        try:
                            if action == 'deleted':
                                # Delete processing
                                doc_id = json_url.split('/')[-1].replace('.json', '')
                                if dry_run:
                                    # Only check existence for deletion in dry-run
                                    existing_doc = es_service.get_researcher_by_accn(doc_id)
                                    if existing_doc:
                                        would_update_count += 1
                                    print(f"\r  Progress: [{j+1}/{len(total_changes)}]", end="", flush=True)
                                else:
                                    try:
                                        if es_service.delete_researcher(doc_id):
                                            processed_records += 1
                                        else:
                                            errors_count += 1
                                    except Exception as e:
                                        error_msg = f"ERROR: Elasticsearch connection failed during delete: {e}"
                                        print(error_msg, file=sys.stderr)
                                        logger.exception("Elasticsearch connection error")
                                        raise
                            else:
                                # Create/update processing
                                researcher_data = client.fetch_researcher_data(json_url)
                                es_doc = transformer.transform_researcher(researcher_data)

                                if dry_run:
                                    # Compare with existing data in dry-run
                                    accn = es_doc.get('accn')
                                    if accn:
                                        existing_doc = es_service.get_researcher_by_accn(accn)
                                        if existing_doc:
                                            # Compare with existing data's update time
                                            existing_lastmod = existing_doc.get('_last_updated')
                                            if existing_lastmod and lastmod:
                                                from dateutil.parser import parse as parse_datetime
                                                existing_dt = parse_datetime(existing_lastmod)
                                                if lastmod > existing_dt:
                                                    would_update_count += 1
                                            else:
                                                would_update_count += 1
                                        else:
                                            would_create_count += 1
                                    print(f"\r  Progress: [{j+1}/{len(total_changes)}]", end="", flush=True)
                                else:
                                    batch_data.append((es_doc, lastmod))

                            batch_count += 1
                            processed_records += 1

                            # Update progress
                            if sync_log:
                                sync_log.current_changelist_progress = j + 1
                                sync_log.documents_processed_in_batch = sync_log.documents_processed_in_batch + 1
                                if batch_count % 50 == 0:  # Save every 50 items
                                    sync_log.save()

                            # Batch processing
                            if not dry_run and len(batch_data) >= 100:
                                # Use individual item's lastmod
                                docs_to_index = []
                                for doc, item_lastmod in batch_data:
                                    docs_to_index.append(doc)

                                # Use latest lastmod in batch
                                latest_lastmod = max((item_lastmod for _, item_lastmod in batch_data if item_lastmod), default=None)
                                update_timestamp = latest_lastmod.isoformat() if latest_lastmod else None
                                try:
                                    result = es_service.bulk_index(docs_to_index, update_timestamp=update_timestamp)
                                    # processed_records already updated above, don't use success
                                    errors_count += result['errors']

                                    if result['errors'] > 0:
                                        warning_msg = f"WARNING: {result['errors']} errors in batch"
                                        print(warning_msg, file=sys.stderr)
                                except Exception as e:
                                    error_msg = f"ERROR: Elasticsearch connection failed during bulk index: {e}"
                                    print(error_msg, file=sys.stderr)
                                    logger.exception("Elasticsearch connection error")
                                    raise

                                batch_data = []
                                print(f"  Processed {j+1}/{len(total_changes)} changes from this list")

                        except Exception as e:
                            error_msg = f"ERROR: processing change {action} {json_url}: {e}"
                            logger.exception(error_msg)
                            print(error_msg, file=sys.stderr)

                            # Save current position and stop on any error
                            if sync_log:
                                sync_log.current_changelist_progress = j  # Save current position
                                sync_log.save()
                            raise

                    # Process remaining batch
                    if not dry_run and batch_data:
                        # Use individual item's lastmod
                        docs_to_index = []
                        for doc, item_lastmod in batch_data:
                            docs_to_index.append(doc)

                        # Use latest lastmod in batch
                        latest_lastmod = max((item_lastmod for _, item_lastmod in batch_data if item_lastmod), default=None)
                        update_timestamp = latest_lastmod.isoformat() if latest_lastmod else None
                        try:
                            result = es_service.bulk_index(docs_to_index, update_timestamp=update_timestamp)
                            # processed_records already updated above, don't use success
                            errors_count += result['errors']
                        except Exception as e:
                            error_msg = f"ERROR: Elasticsearch connection failed during bulk index: {e}"
                            print(error_msg, file=sys.stderr)
                            logger.exception("Elasticsearch connection error")
                            raise

                    if dry_run:
                        print(f"\n  Completed change list {i+1}: {batch_count}/{len(total_changes)} changes checked")
                    else:
                        print(f"  Completed change list {i+1}: {batch_count}/{len(total_changes)} changes")

                    # Reset progress when list is completed
                    if sync_log:
                        sync_log.current_changelist_progress = 0
                        sync_log.save()

                    # Update progress
                    if sync_log:
                        sync_log.update_progress(
                            processed_records=processed_records,
                            errors_count=errors_count
                        )

            # Refresh index
            if not dry_run:
                try:
                    es_service.refresh_index()
                except Exception as e:
                    error_msg = f"ERROR: Elasticsearch connection failed during refresh: {e}"
                    print(error_msg, file=sys.stderr)
                    logger.exception("Elasticsearch connection error")
                    raise

            # Get final statistics
            try:
                stats = es_service.get_index_stats()
                total_docs = 0
                if stats:
                    total_docs = stats.get('_all', {}).get('total', {}).get('docs', {}).get('count', 0)
            except Exception as e:
                error_msg = f"ERROR: Elasticsearch connection failed during get stats: {e}"
                print(error_msg, file=sys.stderr)
                logger.exception("Elasticsearch connection error")
                raise

            # Complete sync
            if sync_log:
                sync_log.complete_sync(
                    processed_records=processed_records,
                    errors_count=errors_count,
                    total_records=total_docs
                )

            if dry_run:
                print(f"Dry run completed: {sync_type}, checked={processed_records + would_update_count + would_create_count}, would_update={would_update_count}, would_create={would_create_count}, errors={errors_count}, total_docs={total_docs}")
            else:
                print(f"Sync completed: {sync_type}, processed={processed_records}, errors={errors_count}, total_docs={total_docs}, duration={sync_log.duration}")

            # Return False if there were errors
            return errors_count == 0

        except Exception as e:
            # Sync failed
            error_msg = f"ERROR: Sync failed: {str(e)}"
            print(error_msg, file=sys.stderr)
            logger.exception("Sync failed")

            if sync_log:
                sync_log.fail_sync(
                    error_details=error_msg,
                    processed_records=processed_records,
                    errors_count=errors_count
                )
            return False

    except Exception as e:
        error_msg = f"ERROR: Failed to start sync: {e}"
        print(error_msg, file=sys.stderr)
        logger.exception("Failed to start sync")
        return False


def main():
    """Main CLI entry point"""
    init_app(routes=False)

    parser = argparse.ArgumentParser(description='KAKEN ResourceSync Client CLI')
    parser.add_argument('--dry-run', action='store_true',
                       help='Perform dry run of synchronization process')
    parser.add_argument('--url', type=str,
                       help='Override ResourceSync URL')
    parser.add_argument('--timeout', type=int, default=60,
                       help='Request timeout in seconds')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    # Configure logging
    script_utils.add_file_logger(logger, __file__)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.WARNING)

    # Initialize components
    from addons.metadata import settings

    # Check if KAKEN functionality is enabled
    if settings.KAKEN_ELASTIC_URI is None:
        print("KAKEN functionality disabled (KAKEN_ELASTIC_URI is None)")
        print("Please configure KAKEN_ELASTIC_URI in settings to enable KAKEN synchronization")
        sys.exit(1)

    client = ResourceSyncClient(
        resourcesync_url=args.url or settings.KAKEN_RESOURCESYNC_URL,
        timeout=args.timeout
    )
    transformer = KakenToElasticsearchTransformer()
    es_service = KakenElasticsearchService(
        hosts=[settings.KAKEN_ELASTIC_URI],
        index_name=settings.KAKEN_ELASTIC_INDEX,
        analyzer_config=settings.KAKEN_ELASTIC_ANALYZER_CONFIG,
        **settings.KAKEN_ELASTIC_KWARGS
    )

    success = True

    try:
        if args.dry_run:
            success = sync_kaken_data(client, transformer, es_service, dry_run=True)

        elif len(sys.argv) == 1:
            # No arguments = execute actual sync
            success = sync_kaken_data(client, transformer, es_service)

        else:
            print("Available options:")
            print("  (no arguments): Perform actual data synchronization")
            print("  --dry-run: Test the synchronization process")
            success = False

    finally:
        client.close()
        es_service.close()

    if success:
        sys.exit(0)
    else:
        if args.create_index:
            print("ERROR: Index creation failed", file=sys.stderr)
        elif args.dry_run:
            print("ERROR: Dry run failed", file=sys.stderr)
        else:
            print("ERROR: Data synchronization failed", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()