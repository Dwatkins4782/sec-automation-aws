#!/usr/bin/env python3
"""
Seed test security events into SQS for testing the security automation pipeline.

Usage:
    python scripts/seed_events.py --queue-url <SQS_URL> --count 100
    python scripts/seed_events.py --profile default --region us-east-1 --scenario suspicious
"""

import argparse
import boto3
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any


class EventGenerator:
    """Generate realistic CloudTrail-like security events for testing."""
    
    NORMAL_EVENTS = [
        "DescribeInstances",
        "ListBuckets",
        "GetObject",
        "PutObject",
        "DescribeSecurityGroups",
        "DescribeVolumes",
        "ListUsers",
        "GetUser",
        "AssumeRole",
        "GetCallerIdentity",
    ]
    
    SUSPICIOUS_EVENTS = [
        "DeleteTrail",
        "StopLogging",
        "PutBucketPolicy",
        "CreateAccessKey",
        "DeleteBucket",
        "ModifyInstanceAttribute",
        "AuthorizeSecurityGroupIngress",
        "CreateUser",
        "AttachUserPolicy",
        "PutUserPolicy",
    ]
    
    HIGH_RISK_EVENTS = [
        "DeleteTrail",
        "StopLogging",
        "DeleteBucket",
        "DisableRegion",
        "DeleteFlowLogs",
        "DeleteLogGroup",
    ]
    
    AWS_SERVICES = [
        "ec2.amazonaws.com",
        "s3.amazonaws.com",
        "iam.amazonaws.com",
        "cloudtrail.amazonaws.com",
        "logs.amazonaws.com",
        "guardduty.amazonaws.com",
    ]
    
    USER_AGENTS = [
        "aws-cli/2.13.0 Python/3.11.4 Linux/5.15.0",
        "Boto3/1.28.0 Python/3.9.0 Linux/5.10.0",
        "aws-sdk-go/1.44.0",
        "APN/1.0 HashiCorp/1.0 Terraform/1.5.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    ]
    
    SOURCE_IPS = [
        "192.168.1.100",
        "10.0.1.50",
        "172.16.0.20",
        "203.0.113.45",  # Normal corporate IP
        "198.51.100.88",  # Normal corporate IP
        "185.220.101.1",  # Tor exit node (suspicious)
        "45.142.120.10",  # Known malicious IP
    ]
    
    PRINCIPALS = [
        "alice@example.com",
        "bob@example.com",
        "charlie@example.com",
        "admin@example.com",
        "service-account@example.com",
        "contractor@external.com",
        "AIDAI234567890EXAMPLE",
        "AROAI234567890EXAMPLE",
    ]
    
    AWS_REGIONS = [
        "us-east-1",
        "us-west-2",
        "eu-west-1",
        "ap-southeast-1",
    ]
    
    ERROR_CODES = [
        "AccessDenied",
        "UnauthorizedOperation",
        "InvalidPermission.NotFound",
        "Client.UnauthorizedOperation",
    ]
    
    def __init__(self, scenario: str = "mixed"):
        """
        Initialize event generator.
        
        Args:
            scenario: Type of events to generate - "normal", "suspicious", "mixed", or "attack"
        """
        self.scenario = scenario
    
    def generate_event(self) -> Dict[str, Any]:
        """Generate a single CloudTrail-like event."""
        
        # Select event type based on scenario
        if self.scenario == "normal":
            event_name = random.choice(self.NORMAL_EVENTS)
        elif self.scenario == "suspicious":
            event_name = random.choice(self.SUSPICIOUS_EVENTS)
        elif self.scenario == "attack":
            event_name = random.choice(self.HIGH_RISK_EVENTS)
        else:  # mixed
            all_events = self.NORMAL_EVENTS + self.SUSPICIOUS_EVENTS
            event_name = random.choice(all_events)
        
        # Determine if this should be an error event
        is_error = random.random() < 0.15  # 15% error rate
        
        # Select source IP (use suspicious IPs more for suspicious scenarios)
        if self.scenario in ["suspicious", "attack"]:
            source_ip = random.choice(self.SOURCE_IPS[-2:])  # Use suspicious IPs
        else:
            source_ip = random.choice(self.SOURCE_IPS[:5])  # Use normal IPs
        
        # Determine principal
        principal = random.choice(self.PRINCIPALS)
        
        # Check for root account usage (rare but critical)
        is_root = random.random() < 0.02 if self.scenario in ["suspicious", "attack"] else False
        if is_root:
            principal = "root"
        
        # Build event
        event_time = datetime.utcnow() - timedelta(seconds=random.randint(0, 300))
        
        event = {
            "eventVersion": "1.08",
            "eventID": str(uuid.uuid4()),
            "eventTime": event_time.isoformat() + "Z",
            "eventType": "AwsApiCall",
            "eventName": event_name,
            "awsRegion": random.choice(self.AWS_REGIONS),
            "sourceIPAddress": source_ip,
            "userAgent": random.choice(self.USER_AGENTS),
            "requestParameters": self._generate_request_params(event_name),
            "responseElements": None if is_error else self._generate_response_elements(event_name),
            "requestID": str(uuid.uuid4()),
            "eventSource": random.choice(self.AWS_SERVICES),
            "userIdentity": {
                "type": "Root" if is_root else random.choice(["IAMUser", "AssumedRole"]),
                "principalId": "AIDAI234567890EXAMPLE",
                "arn": f"arn:aws:iam::123456789012:{'root' if is_root else 'user/' + principal}",
                "accountId": "123456789012",
                "userName": principal,
            },
            "recipientAccountId": "123456789012",
        }
        
        # Add error code if this is an error event
        if is_error:
            event["errorCode"] = random.choice(self.ERROR_CODES)
            event["errorMessage"] = f"User: {principal} is not authorized to perform: {event_name}"
        
        # Add MFA info (or lack thereof for suspicious events)
        mfa_used = random.random() > 0.3 if self.scenario == "normal" else False
        if event_name == "ConsoleLogin":
            event["additionalEventData"] = {
                "MFAUsed": "Yes" if mfa_used else "No"
            }
        
        return event
    
    def _generate_request_params(self, event_name: str) -> Dict[str, Any]:
        """Generate realistic request parameters based on event type."""
        params = {}
        
        if event_name in ["CreateAccessKey", "DeleteAccessKey"]:
            params["userName"] = random.choice(self.PRINCIPALS)
        elif event_name in ["PutBucketPolicy", "DeleteBucket"]:
            params["bucketName"] = f"security-logs-{random.randint(1, 100)}"
        elif event_name == "AuthorizeSecurityGroupIngress":
            params["groupId"] = f"sg-{uuid.uuid4().hex[:8]}"
            params["ipPermissions"] = {
                "fromPort": 22,
                "toPort": 22,
                "ipProtocol": "tcp",
                "ipRanges": ["0.0.0.0/0"]  # Suspicious open to world
            }
        elif event_name in ["DeleteTrail", "StopLogging"]:
            params["name"] = "CloudTrail-SecurityLogs"
        
        return params
    
    def _generate_response_elements(self, event_name: str) -> Dict[str, Any]:
        """Generate realistic response elements based on event type."""
        response = {}
        
        if event_name == "CreateAccessKey":
            response["accessKey"] = {
                "accessKeyId": f"AKIA{uuid.uuid4().hex[:16].upper()}",
                "status": "Active",
                "createDate": datetime.utcnow().isoformat() + "Z"
            }
        elif event_name == "AssumeRole":
            response["credentials"] = {
                "accessKeyId": f"ASIA{uuid.uuid4().hex[:16].upper()}",
                "sessionToken": "FwoGZXIvYXdzEBMaD...",
                "expiration": (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
            }
        
        return response if response else None
    
    def generate_batch(self, count: int) -> List[Dict[str, Any]]:
        """Generate a batch of events."""
        return [self.generate_event() for _ in range(count)]


class SQSSeeder:
    """Send generated events to SQS."""
    
    def __init__(self, queue_url: str, region: str = "us-east-1", profile: str = None):
        """
        Initialize SQS seeder.
        
        Args:
            queue_url: SQS queue URL
            region: AWS region
            profile: AWS profile name
        """
        session = boto3.Session(profile_name=profile, region_name=region)
        self.sqs = session.client('sqs')
        self.queue_url = queue_url
    
    def send_events(self, events: List[Dict[str, Any]], batch_size: int = 10) -> int:
        """
        Send events to SQS in batches.
        
        Args:
            events: List of events to send
            batch_size: Number of events per batch (max 10 for SQS)
        
        Returns:
            Number of events sent successfully
        """
        sent_count = 0
        
        # Process in batches
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            entries = [
                {
                    'Id': str(idx),
                    'MessageBody': json.dumps(event),
                    'MessageAttributes': {
                        'EventName': {
                            'StringValue': event.get('eventName', 'Unknown'),
                            'DataType': 'String'
                        },
                        'EventSource': {
                            'StringValue': event.get('eventSource', 'Unknown'),
                            'DataType': 'String'
                        }
                    }
                }
                for idx, event in enumerate(batch)
            ]
            
            try:
                response = self.sqs.send_message_batch(
                    QueueUrl=self.queue_url,
                    Entries=entries
                )
                
                sent_count += len(response.get('Successful', []))
                
                if 'Failed' in response:
                    for failed in response['Failed']:
                        print(f"Failed to send message {failed['Id']}: {failed['Message']}")
            
            except Exception as e:
                print(f"Error sending batch: {e}")
        
        return sent_count


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Seed test security events into SQS queue',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send 100 mixed events to SQS
  python seed_events.py --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/security-events --count 100
  
  # Send suspicious events for testing detection
  python seed_events.py --queue-url $SQS_URL --scenario suspicious --count 50
  
  # Simulate an attack scenario
  python seed_events.py --queue-url $SQS_URL --scenario attack --count 20
  
  # Use specific AWS profile
  python seed_events.py --queue-url $SQS_URL --profile prod --region us-west-2 --count 200
        """
    )
    
    parser.add_argument(
        '--queue-url',
        required=True,
        help='SQS queue URL to send events to'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=100,
        help='Number of events to generate (default: 100)'
    )
    parser.add_argument(
        '--scenario',
        choices=['normal', 'suspicious', 'mixed', 'attack'],
        default='mixed',
        help='Type of events to generate (default: mixed)'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--profile',
        help='AWS profile name to use'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Batch size for SQS sends (max 10, default: 10)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate events but do not send to SQS'
    )
    
    args = parser.parse_args()
    
    # Validate batch size
    if args.batch_size > 10:
        print("Warning: SQS batch size cannot exceed 10, setting to 10")
        args.batch_size = 10
    
    # Generate events
    print(f"Generating {args.count} {args.scenario} events...")
    generator = EventGenerator(scenario=args.scenario)
    events = generator.generate_batch(args.count)
    print(f"✓ Generated {len(events)} events")
    
    if args.dry_run:
        print("\nDry run mode - sample event:")
        print(json.dumps(events[0], indent=2))
        print(f"\nWould send {len(events)} events to {args.queue_url}")
        return
    
    # Send to SQS
    print(f"\nSending events to SQS queue: {args.queue_url}")
    seeder = SQSSeeder(
        queue_url=args.queue_url,
        region=args.region,
        profile=args.profile
    )
    
    sent_count = seeder.send_events(events, batch_size=args.batch_size)
    
    print(f"✓ Successfully sent {sent_count}/{len(events)} events to SQS")
    
    # Print summary
    event_types = {}
    for event in events:
        event_name = event.get('eventName', 'Unknown')
        event_types[event_name] = event_types.get(event_name, 0) + 1
    
    print("\nEvent type summary:")
    for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {event_type}: {count}")


if __name__ == '__main__':
    main()
