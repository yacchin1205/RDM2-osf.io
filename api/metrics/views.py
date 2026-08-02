import json

from django.http import Http404, JsonResponse
from rest_framework.exceptions import ValidationError
from rest_framework import permissions as drf_permissions
from rest_framework.generics import GenericAPIView
from elasticsearch6.exceptions import NotFoundError, RequestError
from elasticsearch_metrics.registry import djelme_registry

from framework.auth.oauth_scopes import CoreScopes
from api.base.permissions import TokenHasScope
from osf.metrics import PreprintDownload, PreprintView
from api.metrics.permissions import IsPreprintMetricsUser, IsRawMetricsUser
from api.metrics.serializers import PreprintMetricSerializer, RawMetricsSerializer
from api.metrics.utils import parse_datetimes
from api.base.views import JSONAPIBaseView
from api.base.waffle_decorators import require_switch
from elasticsearch6_dsl.connections import get_connection

from osf.features import ENABLE_RAW_METRICS


class PreprintMetricMixin(JSONAPIBaseView):
    permission_classes = (
        drf_permissions.IsAuthenticated,
        drf_permissions.IsAdminUser,
        IsPreprintMetricsUser,
        TokenHasScope,
    )

    required_read_scopes = [CoreScopes.METRICS_BASIC]
    required_write_scopes = [CoreScopes.METRICS_RESTRICTED]

    serializer_class = PreprintMetricSerializer

    @property
    def metric_type(self):
        raise NotImplementedError

    @property
    def metric(self):
        raise NotImplementedError

    def add_search(self, search, query_params, **kwargs):
        """
        get list of guids from the kwargs
        use that in a query to narrow down metrics results
        """
        preprint_guid_string = query_params.get('guids')
        if not preprint_guid_string:
            raise ValidationError(
                'To gather metrics for preprints, you must provide one or more preprint ' +
                'guids in the `guids` query parameter.',
            )
        preprint_guids = preprint_guid_string.split(',')

        return search.filter('terms', preprint_id=preprint_guids)

    def format_response(self, response, query_params):
        data = []
        if getattr(response, 'aggregations') and response.aggregations:
            for result in response.aggregations.dates.buckets:
                guid_results = {}
                for preprint_result in result.preprints.buckets:
                    guid_results[preprint_result['key']] = preprint_result['total']['value']
                    # return 0 for the guids with no results for consistent payloads
                guids = query_params['guids'].split(',')
                if guid_results.keys() != guids:
                    for guid in guids:
                        if not guid_results.get(guid):
                            guid_results[guid] = 0
                result_dict = {result.key_as_string: guid_results}
                data.append(result_dict)

        return {
            'metric_type': self.metric_type,
            'data': data,
        }

    def execute_search(self, search, query=None):
        try:
            # There's a bug in the ES python library the prevents us from updating the search object, so lets just make
            # the raw query. If we have it.
            if query:
                es = get_connection(search._using)
                response = search._response_class(
                    search,
                    es.search(
                        index=search._index,
                        body=query,
                    ),
                )
            else:
                response = search.execute()
        except NotFoundError:
            # _get_relevant_indices returned 1 or more indices
            # that doesn't exist. Fall back to unoptimized query
            search = search.index().index(self.metric._default_index())
            response = search.execute()
        return response

    def get(self, *args, **kwargs):
        query_params = getattr(self.request, 'query_params', self.request.GET)

        interval = query_params.get('interval', 'day')

        start_datetime, end_datetime = parse_datetimes(query_params)

        search = self.metric.search(after=start_datetime)
        search = search.filter('range', timestamp={'gte': start_datetime, 'lt': end_datetime})
        search.aggs.bucket('dates', 'date_histogram', field='timestamp', interval=interval) \
            .bucket('preprints', 'terms', field='preprint_id') \
            .metric('total', 'sum', field='count')
        search = self.add_search(search, query_params, **kwargs)
        response = self.execute_search(search)
        resp_dict = self.format_response(response, query_params)

        return JsonResponse(resp_dict)

    def post(self, request, *args, **kwargs):
        """
        For a bit of future proofing, accept custom elasticsearch aggregation queries in JSON form.
        Caution - this could be slow if a very large query is executed, so use with care!
        """
        search = self.metric.search()
        query = request.data.get('query')

        try:
            results = self.execute_search(search, query)
        except RequestError as e:
            if e.args:
                raise ValidationError(e.info['error']['root_cause'][0]['reason'])
            raise ValidationError('Malformed elasticsearch query.')

        return JsonResponse(results.to_dict())


class PreprintViewMetrics(PreprintMetricMixin):

    view_category = 'preprint-metrics'
    view_name = 'preprint-view-metrics'

    @property
    def metric_type(self):
        return 'views'

    @property
    def metric(self):
        return PreprintView


class PreprintDownloadMetrics(PreprintMetricMixin):

    view_category = 'preprint-metrics'
    view_name = 'preprint-download-metrics'

    @property
    def metric_type(self):
        return 'downloads'

    @property
    def metric(self):
        return PreprintDownload

class RawMetricsView(GenericAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticated,
        IsRawMetricsUser,
        TokenHasScope,
    )

    required_read_scopes = [CoreScopes.METRICS_BASIC]
    required_write_scopes = [CoreScopes.METRICS_RESTRICTED]

    view_category = 'raw-metrics'
    view_name = 'raw-metrics-view'

    serializer_class = RawMetricsSerializer

    @require_switch(ENABLE_RAW_METRICS)
    def delete(self, request, *args, **kwargs):
        raise ValidationError('DELETE not supported. Use GET/POST/PUT')

    @require_switch(ENABLE_RAW_METRICS)
    def get(self, request, *args, djelme_backend_name, url_path, **kwargs):
        return JsonResponse(
            self._do_es_request(
                djelme_backend_name,
                method='GET',
                path=url_path,
                query_params=request.GET,
            ),
        )

    @require_switch(ENABLE_RAW_METRICS)
    def post(self, request, *args, djelme_backend_name, url_path, **kwargs):
        return JsonResponse(
            self._do_es_request(
                djelme_backend_name,
                method='POST',
                path=url_path,
                query_params=request.GET,
                body=json.loads(request.body),
            ),
        )

    @require_switch(ENABLE_RAW_METRICS)
    def put(self, request, *args, djelme_backend_name, url_path, **kwargs):
        return JsonResponse(
            self._do_es_request(
                djelme_backend_name,
                method='PUT',
                path=url_path,
                query_params=request.GET,
                body=json.loads(request.body),
            ),
        )

    def _do_es_request(self, djelme_backend_name, method, path, query_params, body=None):
        client = self._get_es_client(djelme_backend_name)
        response = client.transport.perform_request(
            method,
            f'/{path}',
            params=query_params.dict(),
            body=body,
        )
        return response if isinstance(response, dict) else response.body

    def _get_es_client(self, djelme_backend_name):
        try:
            backend = djelme_registry.get_backend(djelme_backend_name)
        except LookupError:
            raise Http404
        return backend.elastic_client
