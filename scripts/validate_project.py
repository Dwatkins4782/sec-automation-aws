#!/usr/bin/env python3
"""
Project validation script - verifies all files are in place and properly configured.
"""

import os
import sys
import json
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

def check_file_exists(filepath, description):
    """Check if a file exists."""
    if os.path.exists(filepath):
        print(f"{Colors.GREEN}✓{Colors.END} {description}: {filepath}")
        return True
    else:
        print(f"{Colors.RED}✗{Colors.END} {description} missing: {filepath}")
        return False

def check_docker_images():
    """Verify Dockerfiles exist for all services."""
    print(f"\n{Colors.BLUE}=== Checking Docker Images ==={Colors.END}")
    services = ['sec-collector', 'sec-enricher', 'sec-responder', 'sec-reporter']
    all_good = True
    
    for service in services:
        dockerfile = f"services/{service}/Dockerfile"
        requirements = f"services/{service}/requirements.txt"
        app_file = f"services/{service}/app.py"
        
        all_good &= check_file_exists(dockerfile, f"{service} Dockerfile")
        all_good &= check_file_exists(requirements, f"{service} requirements")
        all_good &= check_file_exists(app_file, f"{service} app file")
    
    return all_good

def check_helm_charts():
    """Verify Helm charts are properly structured."""
    print(f"\n{Colors.BLUE}=== Checking Helm Charts ==={Colors.END}")
    services = ['sec-collector', 'sec-enricher', 'sec-responder', 'sec-reporter']
    all_good = True
    
    for service in services:
        chart_yaml = f"charts/{service}/Chart.yaml"
        values_yaml = f"charts/{service}/values.yaml"
        deployment = f"charts/{service}/templates/deployment.yaml"
        sa = f"charts/{service}/templates/serviceaccount.yaml"
        helpers = f"charts/{service}/templates/_helpers.tpl"
        
        all_good &= check_file_exists(chart_yaml, f"{service} Chart.yaml")
        all_good &= check_file_exists(values_yaml, f"{service} values.yaml")
        all_good &= check_file_exists(deployment, f"{service} deployment")
        all_good &= check_file_exists(sa, f"{service} serviceaccount")
        all_good &= check_file_exists(helpers, f"{service} helpers")
    
    # Check namespaces
    all_good &= check_file_exists("charts/namespaces.yaml", "Namespaces file")
    
    return all_good

def check_infrastructure():
    """Verify infrastructure code exists."""
    print(f"\n{Colors.BLUE}=== Checking Infrastructure ==={Colors.END}")
    all_good = True
    
    all_good &= check_file_exists("infra/terraform/main.tf", "Terraform main")
    all_good &= check_file_exists("Makefile", "Makefile")
    
    return all_good

def check_observability():
    """Verify observability configs exist."""
    print(f"\n{Colors.BLUE}=== Checking Observability ==={Colors.END}")
    all_good = True
    
    all_good &= check_file_exists("dashboards/iam_posture.json", "IAM dashboard")
    all_good &= check_file_exists("dashboards/alerts.yaml", "Alert rules")
    
    return all_good

def check_scripts():
    """Verify utility scripts exist."""
    print(f"\n{Colors.BLUE}=== Checking Scripts ==={Colors.END}")
    all_good = True
    
    all_good &= check_file_exists("scripts/seed_events.py", "Event seeder")
    all_good &= check_file_exists("scripts/push_dashboards.py", "Dashboard pusher")
    
    return all_good

def check_policies():
    """Verify policy files exist."""
    print(f"\n{Colors.BLUE}=== Checking Policies ==={Colors.END}")
    all_good = True
    
    all_good &= check_file_exists("policies/gatekeeper/constraint.yaml", "Gatekeeper constraints")
    all_good &= check_file_exists("charts/networkpolicies/sec-enricher-egress.yaml", "Network policy")
    
    return all_good

def check_cicd():
    """Verify CI/CD pipeline exists."""
    print(f"\n{Colors.BLUE}=== Checking CI/CD ==={Colors.END}")
    all_good = True
    
    all_good &= check_file_exists(".gitlab-ci.yml", "GitLab CI pipeline")
    
    return all_good

def check_documentation():
    """Verify documentation exists."""
    print(f"\n{Colors.BLUE}=== Checking Documentation ==={Colors.END}")
    all_good = True
    
    all_good &= check_file_exists("README.md", "README")
    
    # Check README has key sections
    if os.path.exists("README.md"):
        with open("README.md", 'r', encoding='utf-8') as f:
            content = f.read()
            sections = [
                "Architecture Overview",
                "Quick Start",
                "File Descriptions",
                "Testing",
                "Troubleshooting"
            ]
            for section in sections:
                if section in content:
                    print(f"{Colors.GREEN}✓{Colors.END} README contains '{section}' section")
                else:
                    print(f"{Colors.YELLOW}!{Colors.END} README missing '{section}' section")
                    all_good = False
    
    return all_good

def check_framework():
    """Verify framework code exists."""
    print(f"\n{Colors.BLUE}=== Checking Framework ==={Colors.END}")
    all_good = True
    
    all_good &= check_file_exists("framework/core/models.py", "Core models")
    
    return all_good

def main():
    """Run all validation checks."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Security Automation AWS - Project Validation{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    results = []
    results.append(("Framework", check_framework()))
    results.append(("Docker Images", check_docker_images()))
    results.append(("Helm Charts", check_helm_charts()))
    results.append(("Infrastructure", check_infrastructure()))
    results.append(("Observability", check_observability()))
    results.append(("Scripts", check_scripts()))
    results.append(("Policies", check_policies()))
    results.append(("CI/CD", check_cicd()))
    results.append(("Documentation", check_documentation()))
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Validation Summary{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    all_passed = True
    for category, passed in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if passed else f"{Colors.RED}FAIL{Colors.END}"
        print(f"{category:.<40} {status}")
        all_passed &= passed
    
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    if all_passed:
        print(f"{Colors.GREEN}✓ All validation checks passed!{Colors.END}")
        print(f"\n{Colors.BLUE}Next steps:{Colors.END}")
        print("  1. Update image repositories in Helm values.yaml files")
        print("  2. Update AWS account ID in Terraform and Helm charts")
        print("  3. Run 'make init' to initialize Terraform")
        print("  4. Run 'make infra-up' to provision infrastructure")
        print("  5. Run 'make deploy' to deploy services")
        return 0
    else:
        print(f"{Colors.RED}✗ Some validation checks failed{Colors.END}")
        print(f"Please review the errors above and ensure all files are in place.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
