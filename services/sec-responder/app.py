#!/usr/bin/env python3
"""
Security Response Service
Executes automated response playbooks for security incidents.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Prometheus metrics
actions_total = Counter('sec_responder_actions_total', 'Total response actions', ['playbook', 'status'])
action_failures = Counter('sec_responder_action_failures_total', 'Failed actions', ['playbook'])
action_duration = Histogram('sec_responder_action_duration_seconds', 'Action duration', ['playbook'])
unresolved_incidents = Gauge('sec_responder_unresolved_incidents', 'Unresolved incidents', ['severity'])
playbook_timeouts = Counter('sec_responder_playbook_timeouts_total', 'Playbook timeouts', ['playbook'])

logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger('responder')


class MockApprover:
    """Mock approval service for automated actions."""
    
    def __init__(self, auto_approve_threshold: int = 75):
        self.auto_approve_threshold = auto_approve_threshold
    
    def approve(self, evidence: Dict) -> bool:
        """
        Determine if action should be auto-approved.
        
        Args:
            evidence: Evidence dictionary with event and context
        
        Returns:
            True if approved, False otherwise
        """
        risk_score = evidence.get('event', {}).get('enrichment', {}).get('risk_score', 0)
        
        # Auto-approve high-risk events
        if risk_score >= self.auto_approve_threshold:
            log.info(f"Auto-approved action for risk score {risk_score}")
            return True
        
        # Defer to manual review for lower risk
        log.info(f"Deferred to manual review for risk score {risk_score}")
        return False


def user_lockdown(event: Dict, approver: MockApprover) -> Dict[str, Any]:
    """
    Execute user lockdown playbook.
    
    Args:
        event: Security event with enrichment
        approver: Approval service
    
    Returns:
        Action result dictionary
    """
    playbook_name = 'user_lockdown'
    
    with action_duration.labels(playbook=playbook_name).time():
        try:
            evidence = {
                'event': event,
                'timeline': ['ingest', 'enrich', 'respond'],
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            # Check approval
            if not approver.approve(evidence):
                actions_total.labels(playbook=playbook_name, status='deferred').inc()
                return {'status': 'deferred', 'reason': 'Below auto-approval threshold'}
            
            entity_id = event.get('entity_id', 'unknown')
            
            # Simulate AWS actions (in production, use boto3 with IRSA)
            log.info(f"Executing lockdown for entity: {entity_id}")
            log.info(f"  - Revoking active sessions for {entity_id}")
            log.info(f"  - Disabling access keys for {entity_id}")
            log.info(f"  - Creating incident ticket with evidence")
            
            # Simulate ticket creation
            ticket_id = f"INC-{int(time.time())}"
            log.info(f"  - Incident ticket created: {ticket_id}")
            
            actions_total.labels(playbook=playbook_name, status='completed').inc()
            
            return {
                'status': 'completed',
                'ticket_id': ticket_id,
                'actions_taken': [
                    'revoked_sessions',
                    'disabled_access_keys',
                    'created_ticket'
                ],
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
        except Exception as e:
            log.error(f"Playbook {playbook_name} failed: {e}")
            action_failures.labels(playbook=playbook_name).inc()
            actions_total.labels(playbook=playbook_name, status='failed').inc()
            return {'status': 'failed', 'error': str(e)}


def isolate_resource(event: Dict, approver: MockApprover) -> Dict[str, Any]:
    """
    Execute resource isolation playbook.
    
    Args:
        event: Security event with enrichment
        approver: Approval service
    
    Returns:
        Action result dictionary
    """
    playbook_name = 'isolate_resource'
    
    with action_duration.labels(playbook=playbook_name).time():
        try:
            evidence = {
                'event': event,
                'timeline': ['ingest', 'enrich', 'respond']
            }
            
            if not approver.approve(evidence):
                actions_total.labels(playbook=playbook_name, status='deferred').inc()
                return {'status': 'deferred'}
            
            resource_id = event.get('attributes', {}).get('resource_id', 'unknown')
            
            log.info(f"Isolating resource: {resource_id}")
            log.info(f"  - Applying quarantine security group")
            log.info(f"  - Creating snapshot for forensics")
            log.info(f"  - Notifying security team")
            
            actions_total.labels(playbook=playbook_name, status='completed').inc()
            
            return {
                'status': 'completed',
                'resource_id': resource_id,
                'actions_taken': ['quarantined', 'snapshot_created', 'team_notified']
            }
            
        except Exception as e:
            log.error(f"Playbook {playbook_name} failed: {e}")
            action_failures.labels(playbook=playbook_name).inc()
            return {'status': 'failed', 'error': str(e)}


def process_event(event: Dict, approver: MockApprover) -> Dict[str, Any]:
    """
    Process security event and execute appropriate playbook.
    
    Args:
        event: Enriched security event
        approver: Approval service
    
    Returns:
        Response result
    """
    risk_score = event.get('enrichment', {}).get('risk_score', 0)
    action = event.get('action', '')
    
    # Determine which playbook to execute
    if action in {'CreateAccessKey', 'AttachUserPolicy', 'PutUserPolicy'}:
        return user_lockdown(event, approver)
    elif action in {'AuthorizeSecurityGroupIngress', 'ModifyInstanceAttribute'}:
        return isolate_resource(event, approver)
    else:
        log.debug(f"No playbook matched for action: {action}")
        return {'status': 'no_action', 'reason': 'No matching playbook'}


def main():
    """Main service loop."""
    log.info("Starting Security Responder Service")
    
    # Start metrics server
    port = int(os.environ.get('METRICS_PORT', '8000'))
    start_http_server(port)
    log.info(f"Metrics server started on port {port}")
    
    # Initialize approver
    auto_approve_threshold = int(os.environ.get('AUTO_APPROVE_THRESHOLD', '75'))
    approver = MockApprover(auto_approve_threshold=auto_approve_threshold)
    
    log.info(f"Responder service ready (auto-approve threshold: {auto_approve_threshold})")
    
    # In a real implementation, this would consume from a queue/stream
    while True:
        try:
            # Simulate event processing
            # In production, consume from Kafka/SQS/etc
            time.sleep(10)
            log.debug("Responder service running...")
            
            # Update unresolved incidents gauge
            # In production, query from database/cache
            unresolved_incidents.labels(severity='high').set(0)
            unresolved_incidents.labels(severity='medium').set(0)
            unresolved_incidents.labels(severity='low').set(0)
            
        except KeyboardInterrupt:
            log.info("Shutting down responder service")
            break
        except Exception as e:
            log.error(f"Error in main loop: {e}")
            time.sleep(5)


if __name__ == '__main__':
    main()
