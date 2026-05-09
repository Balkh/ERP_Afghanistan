"""
Observability Enhancement - Trend Analysis & Anomaly Detection.
Extends existing API observability with intelligence and trends.
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger('erp.observability_trends')


class EndpointIntelligence:
    """Analyze endpoint performance and usage patterns."""

    @staticmethod
    def get_top_endpoints(hours: int = 24, limit: int = 10):
        """Get most frequently called endpoints."""
        from core.operations.api_observability import get_metrics

        metrics = get_metrics()
        requests = metrics.get_bad_requests(hours, limit=1000) + metrics.get_slow_requests(hours, limit=1000)

        endpoint_counts = defaultdict(int)
        for req in requests:
            endpoint_counts[req.get('path', 'unknown')] += 1

        return [
            {'endpoint': ep, 'count': count}
            for ep, count in sorted(endpoint_counts.items(), key=lambda x: -x[1])[:limit]
        ]

    @staticmethod
    def get_error_prone_endpoints(hours: int = 24, limit: int = 10):
        """Get endpoints with highest error rates."""
        from core.operations.api_observability import get_metrics

        metrics = get_metrics()
        error_rates = metrics.get_error_rates()

        return error_rates[:limit]

    @staticmethod
    def get_slowest_endpoints(hours: int = 24, limit: int = 10):
        """Get slowest responding endpoints."""
        from core.operations.api_observability import get_metrics

        metrics = get_metrics()
        return metrics.get_top_slow_endpoints(hours, limit)


class TrendAnalyzer:
    """Analyze performance and error trends."""

    @staticmethod
    def get_error_rate_trend(hours: int = 24, bucket_minutes: int = 60):
        """Calculate error rate trend over time."""
        from core.operations.api_observability import get_metrics

        metrics = get_metrics()
        cutoff = timezone.now() - timedelta(hours=hours)

        buckets = defaultdict(lambda: {'total': 0, 'errors': 0})

        for req in metrics.get_bad_requests(hours):
            timestamp = datetime.fromisoformat(req['timestamp'])
            bucket_key = timestamp.replace(minute=0, second=0, microsecond=0)
            buckets[bucket_key]['errors'] += 1
            buckets[bucket_key]['total'] += 1

        trend = []
        for bucket_time in sorted(buckets.keys()):
            data = buckets[bucket_time]
            error_rate = (data['errors'] / max(data['total'], 1)) * 100
            trend.append({
                'time': bucket_time.isoformat(),
                'total_requests': data['total'],
                'errors': data['errors'],
                'error_rate_percent': round(error_rate, 2)
            })

        return trend[-24:]

    @staticmethod
    def get_latency_trend(hours: int = 24):
        """Calculate latency trend over time."""
        from core.operations.api_observability import get_metrics

        metrics = get_metrics()
        latencies = []

        for req in metrics.get_slow_requests(hours):
            latencies.append({
                'timestamp': req.get('timestamp'),
                'duration_ms': req.get('duration_ms'),
                'path': req.get('path')
            })

        if not latencies:
            return []

        avg_latency = sum(l['duration_ms'] for l in latencies) / len(latencies)
        max_latency = max(l['duration_ms'] for l in latencies)
        min_latency = min(l['duration_ms'] for l in latencies)

        return {
            'summary': {
                'avg_latency_ms': round(avg_latency, 2),
                'max_latency_ms': round(max_latency, 2),
                'min_latency_ms': round(min_latency, 2),
                'total_slow_requests': len(latencies)
            },
            'recent': latencies[-20:]
        }


class AnomalyClustering:
    """Detect and cluster anomalous patterns."""

    @staticmethod
    def get_repeated_failure_clusters(hours: int = 24):
        """Find repeated failure patterns."""
        from core.operations.api_observability import get_metrics

        metrics = get_metrics()
        bad_requests = metrics.get_bad_requests(hours)

        user_patterns = defaultdict(list)
        for req in bad_requests:
            user_id = req.get('user_id', 'anonymous')
            path = req.get('path', 'unknown')
            user_patterns[f"{user_id}:{path}"].append(req)

        clusters = []
        for pattern, requests in user_patterns.items():
            if len(requests) >= 3:
                clusters.append({
                    'user_id': pattern.split(':')[0],
                    'endpoint': pattern.split(':')[1],
                    'failure_count': len(requests),
                    'severity': 'high' if len(requests) > 10 else 'medium',
                    'first_occurrence': requests[0].get('timestamp'),
                    'last_occurrence': requests[-1].get('timestamp')
                })

        return sorted(clusters, key=lambda x: -x['failure_count'])

    @staticmethod
    def get_repeated_slow_clusters(hours: int = 24):
        """Find repeated slow query patterns."""
        from core.operations.api_observability import get_metrics

        metrics = get_metrics()
        slow_requests = metrics.get_slow_requests(hours)

        endpoint_patterns = defaultdict(list)
        for req in slow_requests:
            path = req.get('path', 'unknown')
            endpoint_patterns[path].append(req)

        clusters = []
        for endpoint, requests in endpoint_patterns.items():
            if len(requests) >= 3:
                avg_duration = sum(r.get('duration_ms', 0) for r in requests) / len(requests)
                clusters.append({
                    'endpoint': endpoint,
                    'slow_request_count': len(requests),
                    'avg_duration_ms': round(avg_duration, 2),
                    'max_duration_ms': max(r.get('duration_ms', 0) for r in requests)
                })

        return sorted(clusters, key=lambda x: -x['avg_duration_ms'])

    @staticmethod
    def get_suspicious_ips(hours: int = 24):
        """Detect IPs with suspicious activity."""
        from core.operations.api_observability import get_metrics

        metrics = get_metrics()
        bad_requests = metrics.get_bad_requests(hours)

        ip_patterns = defaultdict(lambda: {'count': 0, 'endpoints': set()})
        for req in bad_requests:
            ip = req.get('ip', 'unknown')
            if ip and ip != 'unknown':
                ip_patterns[ip]['count'] += 1
                ip_patterns[ip]['endpoints'].add(req.get('path', ''))

        suspicious = []
        for ip, data in ip_patterns.items():
            if data['count'] >= 10:
                suspicious.append({
                    'ip': ip,
                    'failed_request_count': data['count'],
                    'unique_endpoints': len(data['endpoints']),
                    'severity': 'high' if data['count'] > 20 else 'medium'
                })

        return sorted(suspicious, key=lambda x: -x['failed_request_count'])


class ObservabilityDashboard:
    """Comprehensive observability dashboard data."""

    @staticmethod
    def get_dashboard_data(hours: int = 24):
        """Get complete dashboard data."""
        return {
            'endpoint_intelligence': {
                'most_used': EndpointIntelligence.get_top_endpoints(hours),
                'error_prone': EndpointIntelligence.get_error_prone_endpoints(hours),
                'slowest': EndpointIntelligence.get_slowest_endpoints(hours)
            },
            'trends': {
                'error_rate': TrendAnalyzer.get_error_rate_trend(hours),
                'latency': TrendAnalyzer.get_latency_trend(hours)
            },
            'anomalies': {
                'repeated_failures': AnomalyClustering.get_repeated_failure_clusters(hours),
                'repeated_slow_queries': AnomalyClustering.get_repeated_slow_clusters(hours),
                'suspicious_ips': AnomalyClustering.get_suspicious_ips(hours)
            },
            'generated_at': timezone.now().isoformat()
        }