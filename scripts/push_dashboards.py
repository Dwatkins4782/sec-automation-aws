#!/usr/bin/env python3
"""
Push Grafana dashboards and alerts to Grafana instance.

Usage:
    python scripts/push_dashboards.py --grafana-url http://localhost:3000
    python scripts/push_dashboards.py --grafana-url $GRAFANA_URL --api-key $GRAFANA_API_KEY
    python scripts/push_dashboards.py --namespace monitoring --service grafana
"""

import argparse
import glob
import json
import os
import sys
import time
from typing import Dict, List, Optional, Any
import urllib.request
import urllib.error
from urllib.parse import urljoin


class GrafanaClient:
    """Client for interacting with Grafana API."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, 
                 username: str = "admin", password: str = "admin"):
        """
        Initialize Grafana client.
        
        Args:
            base_url: Base URL of Grafana instance (e.g., http://localhost:3000)
            api_key: Grafana API key (preferred)
            username: Username for basic auth (fallback)
            password: Password for basic auth (fallback)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.username = username
        self.password = password
        self.session_headers = {}
        
        if api_key:
            self.session_headers['Authorization'] = f'Bearer {api_key}'
        
        self.session_headers['Content-Type'] = 'application/json'
    
    def _make_request(self, endpoint: str, method: str = 'GET', 
                     data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make HTTP request to Grafana API.
        
        Args:
            endpoint: API endpoint (e.g., '/api/dashboards/db')
            method: HTTP method
            data: Request payload for POST/PUT
        
        Returns:
            Response JSON
        """
        url = urljoin(self.base_url, endpoint)
        
        headers = self.session_headers.copy()
        
        # Prepare request
        if data:
            payload = json.dumps(data).encode('utf-8')
        else:
            payload = None
        
        req = urllib.request.Request(url, data=payload, headers=headers, method=method)
        
        # Add basic auth if no API key
        if not self.api_key:
            import base64
            credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            req.add_header('Authorization', f'Basic {credentials}')
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else "No error body"
            raise Exception(f"HTTP {e.code} Error: {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"URL Error: {e.reason}")
    
    def health_check(self) -> bool:
        """Check if Grafana is accessible."""
        try:
            response = self._make_request('/api/health')
            return response.get('database', '') == 'ok'
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    def create_or_update_dashboard(self, dashboard: Dict[str, Any], 
                                   folder_id: int = 0, overwrite: bool = True) -> Dict[str, Any]:
        """
        Create or update a dashboard.
        
        Args:
            dashboard: Dashboard JSON definition
            folder_id: Folder ID to place dashboard in (0 = General)
            overwrite: Whether to overwrite existing dashboard
        
        Returns:
            API response
        """
        payload = {
            'dashboard': dashboard,
            'folderId': folder_id,
            'overwrite': overwrite,
            'message': 'Updated by push_dashboards.py script'
        }
        
        return self._make_request('/api/dashboards/db', method='POST', data=payload)
    
    def get_or_create_folder(self, folder_name: str) -> int:
        """
        Get folder ID by name, create if doesn't exist.
        
        Args:
            folder_name: Name of the folder
        
        Returns:
            Folder ID
        """
        # Search for existing folder
        try:
            folders = self._make_request('/api/folders')
            for folder in folders:
                if folder.get('title') == folder_name:
                    return folder['id']
        except Exception as e:
            print(f"Warning: Could not search folders: {e}")
        
        # Create folder if not found
        try:
            response = self._make_request(
                '/api/folders',
                method='POST',
                data={'title': folder_name}
            )
            return response['id']
        except Exception as e:
            print(f"Warning: Could not create folder '{folder_name}': {e}")
            return 0  # Return General folder
    
    def create_datasource(self, datasource: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update a datasource.
        
        Args:
            datasource: Datasource configuration
        
        Returns:
            API response
        """
        # Check if datasource exists
        try:
            existing = self._make_request(f"/api/datasources/name/{datasource['name']}")
            # Update existing datasource
            datasource['id'] = existing['id']
            return self._make_request(
                f"/api/datasources/{existing['id']}",
                method='PUT',
                data=datasource
            )
        except:
            # Create new datasource
            return self._make_request('/api/datasources', method='POST', data=datasource)
    
    def upload_alert_rules(self, rules_yaml: str, folder_name: str = "Security") -> bool:
        """
        Upload Prometheus alert rules to Grafana.
        
        Note: This requires Grafana with Prometheus datasource and alerting enabled.
        
        Args:
            rules_yaml: YAML content of alert rules
            folder_name: Folder name for alert rules
        
        Returns:
            Success status
        """
        # This is a simplified version - actual implementation depends on Grafana version
        # and whether you're using Grafana-managed alerts or external Prometheus
        print(f"Note: Alert rules should be applied directly to Prometheus or via Grafana's provisioning.")
        print(f"Alert rules file content available at: {rules_yaml}")
        return True


class DashboardPusher:
    """Push dashboards from local files to Grafana."""
    
    def __init__(self, grafana_client: GrafanaClient, dashboards_dir: str = "dashboards"):
        """
        Initialize dashboard pusher.
        
        Args:
            grafana_client: Grafana client instance
            dashboards_dir: Directory containing dashboard JSON files
        """
        self.client = grafana_client
        self.dashboards_dir = dashboards_dir
    
    def find_dashboard_files(self) -> List[str]:
        """Find all dashboard JSON files in the dashboards directory."""
        pattern = os.path.join(self.dashboards_dir, "*.json")
        return glob.glob(pattern)
    
    def load_dashboard(self, filepath: str) -> Dict[str, Any]:
        """Load dashboard JSON from file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            dashboard = json.load(f)
        
        # Remove id if present (will be assigned by Grafana)
        if 'id' in dashboard:
            dashboard['id'] = None
        
        return dashboard
    
    def push_dashboard(self, filepath: str, folder_name: str = "Security") -> bool:
        """
        Push a single dashboard to Grafana.
        
        Args:
            filepath: Path to dashboard JSON file
            folder_name: Folder name to organize dashboards
        
        Returns:
            Success status
        """
        try:
            # Load dashboard
            dashboard = self.load_dashboard(filepath)
            dashboard_name = dashboard.get('title', os.path.basename(filepath))
            
            print(f"Pushing dashboard: {dashboard_name}")
            
            # Get or create folder
            folder_id = self.client.get_or_create_folder(folder_name)
            
            # Push dashboard
            response = self.client.create_or_update_dashboard(
                dashboard=dashboard,
                folder_id=folder_id,
                overwrite=True
            )
            
            print(f"  ✓ Successfully pushed: {dashboard_name}")
            print(f"    URL: {response.get('url', 'N/A')}")
            print(f"    Status: {response.get('status', 'N/A')}")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Failed to push {filepath}: {e}")
            return False
    
    def push_all_dashboards(self, folder_name: str = "Security") -> Dict[str, int]:
        """
        Push all dashboards to Grafana.
        
        Args:
            folder_name: Folder name to organize dashboards
        
        Returns:
            Dictionary with success and failure counts
        """
        dashboard_files = self.find_dashboard_files()
        
        if not dashboard_files:
            print(f"No dashboard files found in {self.dashboards_dir}/")
            return {'success': 0, 'failed': 0}
        
        print(f"\nFound {len(dashboard_files)} dashboard(s) to push:\n")
        
        results = {'success': 0, 'failed': 0}
        
        for filepath in dashboard_files:
            if self.push_dashboard(filepath, folder_name):
                results['success'] += 1
            else:
                results['failed'] += 1
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        return results


def setup_default_datasources(client: GrafanaClient) -> None:
    """Set up default Prometheus and Loki datasources."""
    
    # Prometheus datasource
    prometheus_ds = {
        "name": "Prometheus",
        "type": "prometheus",
        "url": "http://kube-prom-stack-prometheus.monitoring.svc.cluster.local:9090",
        "access": "proxy",
        "isDefault": True,
        "jsonData": {
            "timeInterval": "30s",
            "queryTimeout": "60s"
        }
    }
    
    # Loki datasource
    loki_ds = {
        "name": "Loki",
        "type": "loki",
        "url": "http://loki.monitoring.svc.cluster.local:3100",
        "access": "proxy",
        "jsonData": {}
    }
    
    try:
        print("\nSetting up datasources...")
        client.create_datasource(prometheus_ds)
        print("  ✓ Prometheus datasource configured")
        
        client.create_datasource(loki_ds)
        print("  ✓ Loki datasource configured")
    except Exception as e:
        print(f"  ⚠ Warning: Could not configure datasources: {e}")
        print("    You may need to configure datasources manually")


def get_grafana_url_from_k8s(namespace: str = "monitoring", service: str = "grafana") -> Optional[str]:
    """
    Get Grafana URL from Kubernetes service (if available).
    
    Args:
        namespace: Kubernetes namespace
        service: Service name
    
    Returns:
        Grafana URL or None
    """
    try:
        import subprocess
        
        # Try to get service via kubectl port-forward
        print(f"Attempting to detect Grafana service in namespace '{namespace}'...")
        
        result = subprocess.run(
            ['kubectl', 'get', 'svc', service, '-n', namespace, '-o', 'json'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            svc_info = json.loads(result.stdout)
            port = svc_info['spec']['ports'][0]['port']
            
            # Check if LoadBalancer and has external IP
            if svc_info['spec']['type'] == 'LoadBalancer':
                external_ip = svc_info['status'].get('loadBalancer', {}).get('ingress', [{}])[0].get('hostname') or \
                             svc_info['status'].get('loadBalancer', {}).get('ingress', [{}])[0].get('ip')
                if external_ip:
                    return f"http://{external_ip}:{port}"
            
            print(f"  Service found but no external IP. Use 'kubectl port-forward' to access:")
            print(f"  kubectl port-forward -n {namespace} svc/{service} 3000:{port}")
            
    except Exception as e:
        print(f"  Could not detect Kubernetes service: {e}")
    
    return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Push Grafana dashboards and configure datasources',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Push dashboards to local Grafana
  python push_dashboards.py --grafana-url http://localhost:3000
  
  # Use API key for authentication
  python push_dashboards.py --grafana-url http://grafana.example.com --api-key $GRAFANA_API_KEY
  
  # Auto-detect Grafana in Kubernetes
  python push_dashboards.py --namespace monitoring --service grafana
  
  # Custom credentials and folder
  python push_dashboards.py --grafana-url http://localhost:3000 --username admin --password secret --folder "My Dashboards"
        """
    )
    
    parser.add_argument(
        '--grafana-url',
        help='Grafana base URL (e.g., http://localhost:3000)'
    )
    parser.add_argument(
        '--api-key',
        help='Grafana API key (preferred auth method)'
    )
    parser.add_argument(
        '--username',
        default='admin',
        help='Grafana username for basic auth (default: admin)'
    )
    parser.add_argument(
        '--password',
        default='admin',
        help='Grafana password for basic auth (default: admin)'
    )
    parser.add_argument(
        '--dashboards-dir',
        default='dashboards',
        help='Directory containing dashboard JSON files (default: dashboards)'
    )
    parser.add_argument(
        '--folder',
        default='Security',
        help='Grafana folder name for dashboards (default: Security)'
    )
    parser.add_argument(
        '--setup-datasources',
        action='store_true',
        help='Set up default Prometheus and Loki datasources'
    )
    parser.add_argument(
        '--namespace',
        default='monitoring',
        help='Kubernetes namespace for Grafana service (default: monitoring)'
    )
    parser.add_argument(
        '--service',
        default='grafana',
        help='Kubernetes service name for Grafana (default: grafana)'
    )
    parser.add_argument(
        '--skip-health-check',
        action='store_true',
        help='Skip Grafana health check'
    )
    
    args = parser.parse_args()
    
    # Determine Grafana URL
    grafana_url = args.grafana_url
    
    if not grafana_url:
        # Try to detect from environment
        grafana_url = os.environ.get('GRAFANA_URL')
    
    if not grafana_url:
        # Try to detect from Kubernetes
        grafana_url = get_grafana_url_from_k8s(args.namespace, args.service)
    
    if not grafana_url:
        print("Error: Grafana URL not provided and could not be auto-detected.")
        print("Please specify --grafana-url or set GRAFANA_URL environment variable.")
        print("\nTo access Grafana via kubectl port-forward:")
        print(f"  kubectl port-forward -n {args.namespace} svc/{args.service} 3000:80")
        print("Then run:")
        print("  python push_dashboards.py --grafana-url http://localhost:3000")
        sys.exit(1)
    
    # Get API key from environment if not provided
    api_key = args.api_key or os.environ.get('GRAFANA_API_KEY')
    
    print(f"Grafana URL: {grafana_url}")
    print(f"Auth method: {'API Key' if api_key else 'Basic Auth'}")
    print(f"Dashboards directory: {args.dashboards_dir}")
    print(f"Target folder: {args.folder}\n")
    
    # Initialize client
    client = GrafanaClient(
        base_url=grafana_url,
        api_key=api_key,
        username=args.username,
        password=args.password
    )
    
    # Health check
    if not args.skip_health_check:
        print("Checking Grafana health...")
        if not client.health_check():
            print("Warning: Grafana health check failed. Continuing anyway...")
        else:
            print("✓ Grafana is healthy\n")
    
    # Set up datasources if requested
    if args.setup_datasources:
        setup_default_datasources(client)
    
    # Push dashboards
    pusher = DashboardPusher(client, args.dashboards_dir)
    results = pusher.push_all_dashboards(folder_name=args.folder)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Successfully pushed: {results['success']}")
    print(f"  Failed: {results['failed']}")
    print(f"{'='*60}")
    
    if results['failed'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
