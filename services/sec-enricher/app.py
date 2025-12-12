#!/usr/bin/env python3
"""
Security Event Enricher Service
Enriches events with baseline behavior, threat intelligence, and risk scoring.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Add framework to path
sys.path.insert(0, '/app/framework')
from core.models import SecurityEvent, RiskAssessment

# Prometheus metrics
events_received = Counter('sec_enricher_received_events_total', 'Total events received')
events_enriched = Counter('sec_enricher_enriched_events_total', 'Total events enriched')
enrichment_duration = Histogram('sec_enricher_enrichment_duration_seconds', 'Enrichment duration')
threat_intel_failures = Counter('sec_enricher_threat_intel_failures_total', 'Threat intel failures')
geoip_failures = Counter('sec_enricher_geoip_failures_total', 'GeoIP lookup failures')
risk_score_gauge = Gauge('sec_enricher_risk_score', 'Current risk score', ['entity_id'])

logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger('enricher')


class MockBaseline:
    """Mock baseline behavior analyzer."""
    
    def __init__(self):
        self.normal_geos = {
            'alice@example.com': ['US', 'CA'],
            'bob@example.com': ['US'],
            'admin@example.com': ['US', 'UK'],
        }
        self.normal_actions = {
            'alice@example.com': ['GetObject', 'PutObject', 'DescribeInstances'],
            'bob@example.com': ['ListBuckets', 'GetUser'],
        }
    
    def allowed_geo(self, entity_id: str) -> List[str]:
        """Get allowed geolocation countries for entity."""
        return self.normal_geos.get(entity_id, ['US'])
    
    def is_anomalous(self, entity_id: str, attributes: Dict) -> bool:
        """Check if event attributes are anomalous for entity."""
        normal_actions = self.normal_actions.get(entity_id, [])
        action = attributes.get('action', '')
        return action not in normal_actions if normal_actions else False


class MockThreatIntel:
    """Mock threat intelligence service."""
    
    def __init__(self):
        self.malicious_ips = {
            '185.220.101.1': 95,  # Tor exit node
            '45.142.120.10': 98,  # Known malicious
        }
    
    def reputation(self, indicators: List[str]) -> int:
        """Get reputation score for indicators (0-100, higher = more suspicious)."""
        if not indicators:
            return 0
        
        max_score = 0
        for indicator in indicators:
            score = self.malicious_ips.get(indicator, 0)
            max_score = max(max_score, score)
        
        return max_score


def score(event: Dict, baseline: MockBaseline, intel: MockThreatIntel) -> RiskAssessment:
    """
    Calculate risk score for an event.
    
    Args:
        event: Security event dictionary
        baseline: Baseline behavior analyzer
        intel: Threat intelligence service
    
    Returns:
        RiskAssessment with score and reasons
    """
    reasons, score = [], 0
    
    # Check for privileged actions
    if event.get('action') in {'CreateAccessKey', 'AttachUserPolicy', 'PutUserPolicy', 
                                'DeleteTrail', 'StopLogging', 'DeleteBucket'}:
        score += 35
        reasons.append('Privileged IAM action')
    
    # Check threat intelligence
    indicators = event.get('indicators', [])
    ip_address = event.get('attributes', {}).get('geo', '')
    if ip_address:
        indicators.append(ip_address)
    
    reputation_score = intel.reputation(indicators)
    if reputation_score > 80:
        score += 25
        reasons.append(f'High reputation indicators ({reputation_score})')
    elif reputation_score > 50:
        score += 15
        reasons.append(f'Medium reputation indicators ({reputation_score})')
    
    # Check behavioral anomaly
    if baseline.is_anomalous(event.get('entity_id', ''), event.get('attributes', {})):
        score += 25
        reasons.append('Behavioral anomaly')
    
    # Check geolocation
    geo = event.get('attributes', {}).get('geo', '')
    allowed_geos = baseline.allowed_geo(event.get('entity_id', ''))
    if geo and geo not in allowed_geos:
        score += 15
        reasons.append(f'Unusual geolocation: {geo}')
    
    return RiskAssessment(score=min(score, 100), reasons=reasons)


def enrich_event(event_data: Dict, baseline: MockBaseline, intel: MockThreatIntel) -> Dict:
    """
    Enrich a security event with risk scoring and additional context.
    
    Args:
        event_data: Raw event data
        baseline: Baseline behavior analyzer
        intel: Threat intelligence service
    
    Returns:
        Enriched event with risk assessment
    """
    events_received.inc()
    
    with enrichment_duration.time():
        try:
            # Calculate risk score
            assessment = score(event_data, baseline, intel)
            
            # Add enrichment
            enriched = {
                **event_data,
                'enrichment': {
                    'risk_score': assessment.score,
                    'risk_reasons': assessment.reasons,
                    'enriched_at': datetime.utcnow().isoformat() + 'Z'
                }
            }
            
            # Update metrics
            events_enriched.inc()
            entity_id = event_data.get('entity_id', 'unknown')
            risk_score_gauge.labels(entity_id=entity_id).set(assessment.score)
            
            return enriched
            
        except Exception as e:
            log.error(f"Enrichment failed: {e}")
            threat_intel_failures.inc()
            return event_data


def main():
    """Main service loop."""
    log.info("Starting Security Enricher Service")
    
    # Start metrics server
    port = int(os.environ.get('METRICS_PORT', '8000'))
    start_http_server(port)
    log.info(f"Metrics server started on port {port}")
    
    # Initialize services
    baseline = MockBaseline()
    intel = MockThreatIntel()
    
    log.info("Enricher service ready")
    
    # In a real implementation, this would consume from a queue/stream
    # For now, simulate processing
    while True:
        try:
            # Simulate event processing
            # In production, this would consume from Kafka/SQS/etc
            time.sleep(10)
            log.debug("Enricher service running...")
            
        except KeyboardInterrupt:
            log.info("Shutting down enricher service")
            break
        except Exception as e:
            log.error(f"Error in main loop: {e}")
            time.sleep(5)


if __name__ == '__main__':
    main()
