# AWS Security Automation Pipeline

A comprehensive, production-ready security automation platform built on AWS EKS that ingests CloudTrail events, enriches them with threat intelligence and behavioral analysis, automatically responds to security incidents, and provides compliance reporting.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup Guide](#detailed-setup-guide)
- [File Descriptions](#file-descriptions)
- [Testing](#testing)
- [Monitoring & Observability](#monitoring--observability)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Architecture Overview

```
CloudTrail Events → EventBridge → SQS → Collector → Enricher → Responder
                                            ↓          ↓          ↓
                                        Prometheus ← Metrics ← Reporter
                                            ↓
                                        Grafana Dashboards
```

**Data Flow:**
1. **CloudTrail** logs AWS API calls
2. **EventBridge** filters high-risk IAM events
3. **SQS** queues events for processing
4. **Collector** normalizes and ingests events
5. **Enricher** adds risk scoring and threat intelligence
6. **Responder** executes automated response playbooks
7. **Reporter** generates compliance reports
8. **Prometheus** collects metrics from all services
9. **Grafana** visualizes security posture

---

## Project Structure

```
sec-automation-aws/
├─ framework/                    # Shared Python libraries
│   └─ core/
│       └─ models.py            # Pydantic models for events and risk assessments
├─ services/                     # Microservices
│   ├─ sec-collector/           # SQS consumer, event normalizer
│   │   ├─ app.py               # Main application
│   │   ├─ Dockerfile           # Container image
│   │   └─ requirements.txt     # Python dependencies
│   ├─ sec-enricher/            # Risk scoring and enrichment
│   │   ├─ app.py               # Main application
│   │   ├─ score.py             # Risk scoring logic
│   │   ├─ Dockerfile           # Container image
│   │   └─ requirements.txt     # Python dependencies
│   ├─ sec-responder/           # Automated response orchestration
│   │   ├─ app.py               # Main application
│   │   ├─ playbook.py          # Response playbooks
│   │   ├─ Dockerfile           # Container image
│   │   └─ requirements.txt     # Python dependencies
│   └─ sec-reporter/            # Compliance reporting
│       ├─ app.py               # Main application
│       ├─ Dockerfile           # Container image
│       └─ requirements.txt     # Python dependencies
├─ charts/                       # Helm charts for Kubernetes
│   ├─ sec-collector/           # Collector Helm chart
│   ├─ sec-enricher/            # Enricher Helm chart
│   ├─ sec-responder/           # Responder Helm chart
│   ├─ sec-reporter/            # Reporter Helm chart
│   ├─ networkpolicies/         # Network policies
│   └─ namespaces.yaml          # Kubernetes namespaces
├─ dashboards/                   # Grafana dashboards and alerts
│   ├─ iam_posture.json         # IAM security dashboard
│   └─ alerts.yaml              # Prometheus alert rules
├─ policies/                     # Policy as code
│   └─ gatekeeper/
│       └─ constraint.yaml      # OPA Gatekeeper constraints
├─ infra/                        # Infrastructure as code
│   └─ terraform/
│       └─ main.tf              # AWS infrastructure (VPC, EKS, SQS, IRSA)
├─ scripts/                      # Utility scripts
│   ├─ seed_events.py           # Generate test security events
│   └─ push_dashboards.py       # Upload Grafana dashboards
├─ .gitlab-ci.yml               # CI/CD pipeline
├─ Makefile                     # Automation commands
└─ README.md                    # This file
```

---

## Prerequisites

### Required Tools
- **AWS CLI** v2.x - [Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- **Terraform** v1.5+ - [Install Guide](https://learn.hashicorp.com/tutorials/terraform/install-cli)
- **kubectl** v1.28+ - [Install Guide](https://kubernetes.io/docs/tasks/tools/)
- **Helm** v3.12+ - [Install Guide](https://helm.sh/docs/intro/install/)
- **Docker** v24+ - [Install Guide](https://docs.docker.com/get-docker/)
- **Python** 3.11+ - [Install Guide](https://www.python.org/downloads/)
- **Make** (Windows only) - Install via `winget install GnuWin32.Make` or use direct commands from Makefile

### AWS Requirements
- AWS Account with administrative access
- AWS Profile configured (`aws configure`)
- Sufficient quota for:
  - 1 VPC
  - 2 NAT Gateways
  - 1 EKS Cluster
  - 2-4 EC2 instances (t3.large)
  - 1 SQS Queue
  - CloudTrail enabled

### Estimated Costs
Running this infrastructure will cost approximately **$150-250/month** depending on:
- EKS cluster ($72/month)
- EC2 worker nodes ($100-150/month)
- NAT Gateways ($32/month)
- Data transfer and storage (variable)

### Windows Setup

If you're on Windows, install Make using winget:

```powershell
# Install Make
winget install GnuWin32.Make

# Add to PATH (for current session)
$env:Path += ";C:\Program Files (x86)\GnuWin32\bin"

# Verify installation
make --version
```

**Note:** Some Makefile commands may have issues on Windows due to `echo` differences. You can either:
1. Use the direct commands from the Makefile (shown in each section below)
2. Use Git Bash or WSL2 for full Make compatibility
3. Install MSYS2 for better POSIX compatibility

---

## Quick Start

### 1. Clone Repository

### 1. Clone Repository

```bash
git clone https://github.com/your-org/sec-automation-aws.git
cd sec-automation-aws
```

### 2. Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and default region (us-east-1)
```

### 3. Deploy Infrastructure

```bash
# Initialize Terraform
make init

# Review the infrastructure plan
cd infra/terraform && terraform plan

# Deploy AWS infrastructure (VPC, EKS, SQS, IAM roles)
make infra-up
```

**This will create:**
- VPC with public and private subnets
- EKS cluster with managed node group
- SQS queue for security events
- EventBridge rule to route CloudTrail events
- IAM roles with IRSA for pod authentication

### 4. Configure kubectl

```bash
# Update kubeconfig to connect to EKS
make kubeconfig

# Verify connectivity
kubectl get nodes
```

### 5. Deploy Observability Stack

```bash
# Deploy Prometheus, Loki, and Grafana
make observability

# Wait for pods to be ready
kubectl get pods -n monitoring -w
```

### 6. Build and Push Container Images

```bash
# Login to container registry
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Build all service images
docker build -t ghcr.io/your-org/sec-automation-aws/sec-collector:latest services/sec-collector
docker build -t ghcr.io/your-org/sec-automation-aws/sec-enricher:latest services/sec-enricher
docker build -t ghcr.io/your-org/sec-automation-aws/sec-responder:latest services/sec-responder
docker build -t ghcr.io/your-org/sec-automation-aws/sec-reporter:latest services/sec-reporter

# Push images to registry
docker push ghcr.io/your-org/sec-automation-aws/sec-collector:latest
docker push ghcr.io/your-org/sec-automation-aws/sec-enricher:latest
docker push ghcr.io/your-org/sec-automation-aws/sec-responder:latest
docker push ghcr.io/your-org/sec-automation-aws/sec-reporter:latest
```

### 7. Update Helm Values

Edit each Helm chart's `values.yaml` to use your actual AWS account ID and container registry:

```bash
# Update IRSA role ARNs in values.yaml files
# Replace 123456789012 with your actual AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Update collector values
sed -i "s/123456789012/${AWS_ACCOUNT_ID}/g" charts/sec-collector/values.yaml

# Update enricher values
sed -i "s/123456789012/${AWS_ACCOUNT_ID}/g" charts/sec-enricher/values.yaml

# Update responder values
sed -i "s/123456789012/${AWS_ACCOUNT_ID}/g" charts/sec-responder/values.yaml

# Update reporter values
sed -i "s/123456789012/${AWS_ACCOUNT_ID}/g" charts/sec-reporter/values.yaml
```

### 8. Deploy Microservices

```bash
# Create namespaces
kubectl apply -f charts/namespaces.yaml

# Deploy all security services
make deploy
```

### 9. Verify Deployment

```bash
# Check pod status
kubectl get pods -n sec-data

# Check logs
kubectl logs -n sec-data deploy/sec-collector-sec-collector

# Port-forward to check metrics
kubectl port-forward -n sec-data deploy/sec-collector-sec-collector 8000:8000
curl http://localhost:8000/metrics
```

### 10. Seed Test Events

```bash
# Get SQS queue URL
export SQS_URL=$(aws sqs get-queue-url --queue-name sec-iam-events --query 'QueueUrl' --output text)

# Generate and send test security events
python scripts/seed_events.py --queue-url $SQS_URL --count 100 --scenario mixed

# Watch collector logs to see events being processed
kubectl logs -n sec-data -f deploy/sec-collector-sec-collector
```

### 11. Access Grafana Dashboards

```bash
# Get Grafana admin password
export GRAFANA_PASSWORD=$(kubectl get secret -n monitoring kube-prom-stack-grafana -o jsonpath="{.data.admin-password}" | base64 --decode)

# Port-forward Grafana
kubectl port-forward -n monitoring svc/kube-prom-stack-grafana 3000:80

# Open http://localhost:3000
# Username: admin
# Password: (from $GRAFANA_PASSWORD)

# Push custom dashboards
python scripts/push_dashboards.py --grafana-url http://localhost:3000 --username admin --password $GRAFANA_PASSWORD
```

---

## Detailed Setup Guide

### Infrastructure Provisioning (Terraform)

The Terraform configuration creates the foundational AWS infrastructure:

#### What Gets Created:
1. **VPC** - Isolated network with public and private subnets across 2 AZs
2. **EKS Cluster** - Kubernetes v1.29 with managed node groups
3. **SQS Queue** - Message queue for security events (24-hour retention)
4. **EventBridge Rule** - Filters CloudTrail events for high-risk IAM actions
5. **IAM Roles with IRSA** - Pod-level AWS permissions using OIDC

#### Step-by-Step:

```bash
cd infra/terraform

# Initialize Terraform (downloads providers)
terraform init

# Review what will be created
terraform plan

# Create infrastructure (takes 15-20 minutes)
terraform apply -auto-approve

# Save outputs for later use
terraform output -json > outputs.json
```

#### IRSA Configuration
IRSA (IAM Roles for Service Accounts) allows Kubernetes pods to assume AWS IAM roles without static credentials:

```
EKS OIDC Provider → IAM Trust Policy → IAM Role → Pod Service Account
```

Each service has its own IAM role with least-privilege permissions:
- **Collector**: SQS read/delete permissions
- **Enricher**: None (reads from Collector)
- **Responder**: IAM write permissions (revoke, disable)
- **Reporter**: S3 write permissions (export reports)

---

### Container Image Building

Each microservice has a Dockerfile that:
1. Uses Python 3.11 slim base image
2. Installs dependencies from requirements.txt
3. Copies application code
4. Creates non-root user (security best practice)
5. Exposes metrics port (8000)
6. Runs application with `-u` (unbuffered output for logs)

**Build locally:**
```bash
cd services/sec-collector
docker build -t sec-collector:test .
docker run -e SQS_URL=test sec-collector:test
```

---

### Helm Chart Deployment

Helm charts define Kubernetes resources for each service:

#### Chart Structure (example: sec-collector):
```
charts/sec-collector/
├─ Chart.yaml              # Metadata (name, version)
├─ values.yaml             # Configuration values
└─ templates/
   ├─ deployment.yaml      # Kubernetes Deployment
   ├─ serviceaccount.yaml  # Service Account with IRSA
   └─ _helpers.tpl         # Template helpers
```

#### Key Configuration (values.yaml):
- `image.repository` - Container image location
- `image.tag` - Version to deploy
- `serviceAccount.annotations` - IRSA role ARN
- `resources` - CPU/memory limits
- `env` - Environment variables

#### Deploy with Helm:
```bash
# Install/upgrade collector
helm upgrade --install sec-collector charts/sec-collector \
  --set image.tag=v1.0.0 \
  --namespace sec-data \
  --create-namespace

# View deployed resources
helm list -n sec-data
kubectl get all -n sec-data
```

---

## File Descriptions

### Core Services

#### `services/sec-collector/app.py`
**Purpose:** Ingests security events from SQS and normalizes CloudTrail data

**Key Functions:**
- Polls SQS queue every 10 seconds
- Normalizes CloudTrail events to standard format
- Tags events with risk level (high/low)
- Exposes Prometheus metrics (events_total, sqs_lag)
- Deletes messages after processing

**Why this design:**
- Long polling (WaitTimeSeconds=10) reduces empty receives
- Batch processing (MaxNumberOfMessages=10) improves throughput
- Prometheus metrics enable real-time monitoring
- Structured logging (JSON) for centralized log analysis

**Environment Variables:**
- `SQS_URL` - SQS queue URL (required)
- `LOG_LEVEL` - Logging verbosity (default: INFO)

---

#### `services/sec-enricher/app.py`
**Purpose:** Enriches events with risk scoring and threat intelligence

**Key Components:**
- `MockBaseline` - Behavioral baseline analyzer
- `MockThreatIntel` - Threat intelligence lookup
- `score()` - Risk scoring algorithm (0-100)

**Risk Scoring Logic:**
- Privileged action (+35): CreateAccessKey, AttachUserPolicy, etc.
- High reputation indicators (+25): Known malicious IPs
- Behavioral anomaly (+25): Action outside normal baseline
- Unusual geolocation (+15): Login from unexpected country

**Why this design:**
- Modular scoring allows easy rule additions
- Mock services can be replaced with real APIs (VirusTotal, IPinfo, etc.)
- Prometheus metrics track enrichment performance
- Risk score enables automated decision-making

**Metrics Exposed:**
- `sec_enricher_enriched_events_total` - Events enriched
- `sec_enricher_enrichment_duration_seconds` - Processing latency
- `sec_enricher_risk_score` - Current risk scores by entity

---

#### `services/sec-responder/app.py`
**Purpose:** Executes automated response playbooks for incidents

**Playbooks:**
1. **user_lockdown** - Revokes sessions, disables keys, creates ticket
2. **isolate_resource** - Quarantines EC2/RDS, creates forensic snapshot

**Auto-Approval Logic:**
- Events with risk_score >= 75 are auto-approved
- Lower scores are deferred to manual review
- Approval threshold is configurable via env var

**Why this design:**
- Playbook pattern allows extensible response actions
- Auto-approval prevents alert fatigue for high-confidence detections
- Simulated AWS actions can be replaced with real boto3 calls
- Metrics track response effectiveness

**Metrics Exposed:**
- `sec_responder_actions_total{playbook, status}` - Actions by result
- `sec_responder_action_failures_total` - Failed responses
- `sec_responder_unresolved_incidents{severity}` - Backlog

---

#### `services/sec-reporter/app.py`
**Purpose:** Generates compliance reports and security posture snapshots

**Report Types:**
1. **CIS Compliance** - CIS AWS Foundations Benchmark checks
2. **IAM Posture** - User hygiene (MFA, key rotation, unused creds)
3. **Incident Summary** - 7-day incident statistics

**Why this design:**
- Periodic report generation (default: hourly)
- Mock compliance checks can be replaced with real AWS Config queries
- Reports can be exported to S3, SIEM, or ticketing systems
- Metrics enable tracking compliance drift over time

**Metrics Exposed:**
- `sec_reporter_compliance_score{standard}` - Compliance percentage
- `sec_reporter_policy_violations{severity}` - Current violations

---

### Infrastructure

#### `infra/terraform/main.tf`
**Purpose:** Defines AWS infrastructure as code

**Resources Created:**
- VPC with public/private subnets (terraform-aws-modules/vpc)
- EKS cluster v1.29 with managed nodes (terraform-aws-modules/eks)
- SQS queue with 24-hour retention
- EventBridge rule filtering IAM API calls
- IAM roles with IRSA trust policies

**Why Terraform:**
- Infrastructure versioning and audit trail
- Reproducible deployments across environments
- State management prevents resource drift
- Module reuse (community VPC/EKS modules)

**Variables:**
- `region` - AWS region (default: us-east-1)
- `cluster_name` - EKS cluster name (default: sec-eks)

---

### Observability

#### `dashboards/iam_posture.json`
**Purpose:** Grafana dashboard for IAM security visualization

**Panels:**
- Root account usage (stat panel, critical threshold)
- MFA compliance percentage (gauge)
- Access key age (table with color coding)
- Role assumptions over time (time series)

**Alerts Embedded:**
- Root usage detected (critical)
- MFA compliance < 80% (warning)
- Access keys > 90 days old (warning)

**Why JSON format:**
- Portable across Grafana instances
- Version-controlled dashboard definitions
- Can be pushed via API (scripts/push_dashboards.py)

---

#### `dashboards/alerts.yaml`
**Purpose:** Prometheus alert rules for security monitoring

**Alert Groups:**
1. **security_services** - Service availability, errors, latency
2. **sqs_monitoring** - Queue backlog, message age, DLQ
3. **iam_security** - Root usage, MFA, stale keys
4. **cloudtrail_monitoring** - Trail disabled, suspicious APIs
5. **resource_utilization** - Memory, CPU, disk
6. **enrichment_quality** - Enrichment success rate
7. **response_automation** - Playbook failures, timeouts

**Why alert-as-code:**
- Version-controlled alerting rules
- Consistent across environments
- CI/CD testable (promtool validate)

---

### Network Security

#### `policies/gatekeeper/constraint.yaml`
**Purpose:** OPA Gatekeeper policies for Kubernetes admission control

**Constraints:**
- Require labels (app, version) on workloads
- Block privileged containers
- Enforce resource limits
- Require readiness probes
- Block NodePort services
- Enforce security context (non-root, no privilege escalation)

**Why Gatekeeper:**
- Policy-as-code for Kubernetes security
- Prevents misconfigurations before deployment
- Audit mode for gradual enforcement

---

#### `charts/networkpolicies/sec-enricher-egress.yaml`
**Purpose:** Kubernetes NetworkPolicy for micro-segmentation

**Rules:**
- Allow DNS (kube-dns on port 53)
- Allow HTTPS to AWS services (VPC endpoints)
- Allow communication with other security services
- Allow Prometheus scraping
- Deny all other egress (default-deny)

**Why network policies:**
- Defense-in-depth (limits blast radius)
- Prevents lateral movement
- Compliance requirement (PCI-DSS, NIST)

---

### CI/CD

#### `.gitlab-ci.yml`
**Purpose:** Automated build, test, and deployment pipeline

**Stages:**
1. **test** - Unit tests, linting, security scans
2. **build** - Docker image builds and registry push
3. **scan** - Trivy vulnerability scanning
4. **deploy** - Helm deployments to dev/staging/prod
5. **cleanup** - Resource cleanup

**Why GitLab CI:**
- Integrated with version control
- Parallel test execution
- Environment promotion (dev → staging → prod)
- Manual gates for production

---

### Automation Scripts

#### `scripts/seed_events.py`
**Purpose:** Generate realistic test security events for pipeline validation

**Event Scenarios:**
- **normal** - Routine AWS operations (GetObject, DescribeInstances)
- **suspicious** - Elevated privilege actions (CreateAccessKey)
- **attack** - Malicious activity (DeleteTrail, StopLogging)
- **mixed** - Combination of all types

**Why needed:**
- Test pipeline without real security events
- Validate detection logic
- Load testing
- Demo/training purposes

**Usage:**
```bash
python scripts/seed_events.py \
  --queue-url $SQS_URL \
  --scenario attack \
  --count 50
```

---

#### `scripts/push_dashboards.py`
**Purpose:** Automate Grafana dashboard deployment via API

**Features:**
- Auto-detects Grafana from Kubernetes service
- Creates folders for organization
- Configures Prometheus/Loki datasources
- Uploads all dashboard JSON files
- Supports API key or basic auth

**Why needed:**
- Dashboard-as-code deployment
- Consistent across environments
- No manual clicking in Grafana UI

**Usage:**
```bash
export GRAFANA_API_KEY=<key>
python scripts/push_dashboards.py \
  --grafana-url http://localhost:3000 \
  --setup-datasources
```

---

## Testing

### Unit Tests
Test each service individually:

```bash
# Test collector
cd services/sec-collector
export SQS_URL=https://sqs.us-east-1.amazonaws.com/123456789012/test-queue
python -m pytest tests/ -v

# Test enricher
cd services/sec-enricher
python -m pytest tests/ -v --cov=. --cov-report=html

# Test responder
cd services/sec-responder
python -m pytest tests/ -v
```

### Integration Tests

Test the full pipeline end-to-end:

```bash
# 1. Seed test events
python scripts/seed_events.py --queue-url $SQS_URL --count 10 --scenario suspicious

# 2. Verify collector processes events
kubectl logs -n sec-data deploy/sec-collector-sec-collector --tail=50 | grep "high"

# 3. Check metrics
kubectl port-forward -n sec-data deploy/sec-collector-sec-collector 8000:8000 &
curl http://localhost:8000/metrics | grep iam_events_total
```

### Validate Helm Charts

```bash
# Lint all charts
helm lint charts/sec-collector
helm lint charts/sec-enricher
helm lint charts/sec-responder
helm lint charts/sec-reporter

# Dry-run deployment
helm install sec-collector charts/sec-collector --dry-run --debug
```

### Security Scanning

```bash
# Scan Docker images for vulnerabilities
trivy image ghcr.io/your-org/sec-automation-aws/sec-collector:latest

# Scan Python dependencies
pip install safety
safety check -r services/sec-collector/requirements.txt
```

---

## Monitoring & Observability

### Prometheus Metrics

Each service exposes metrics on port 8000:

**Collector Metrics:**
- `iam_events_total{risk}` - Counter of events by risk level
- `sqs_lag` - Approximate messages in queue

**Enricher Metrics:**
- `sec_enricher_enriched_events_total` - Enrichment success count
- `sec_enricher_enrichment_duration_seconds` - Latency histogram
- `sec_enricher_risk_score{entity_id}` - Current risk scores

**Responder Metrics:**
- `sec_responder_actions_total{playbook, status}` - Action outcomes
- `sec_responder_action_failures_total{playbook}` - Failures by playbook
- `sec_responder_unresolved_incidents{severity}` - Backlog gauge

**Reporter Metrics:**
- `sec_reporter_compliance_score{standard}` - Compliance percentage
- `sec_reporter_policy_violations{severity}` - Violation counts

### Accessing Metrics

```bash
# Port-forward to each service
kubectl port-forward -n sec-data deploy/sec-collector-sec-collector 8001:8000
kubectl port-forward -n sec-data deploy/sec-enricher-sec-enricher 8002:8000
kubectl port-forward -n sec-data deploy/sec-responder-sec-responder 8003:8000
kubectl port-forward -n sec-data deploy/sec-reporter-sec-reporter 8004:8000

# Curl metrics endpoints
curl http://localhost:8001/metrics
curl http://localhost:8002/metrics
curl http://localhost:8003/metrics
curl http://localhost:8004/metrics
```

### Grafana Dashboards

Access Grafana:
```bash
kubectl port-forward -n monitoring svc/kube-prom-stack-grafana 3000:80
# Open http://localhost:3000
# Login: admin / <password from secret>
```

**Available Dashboards:**
- IAM Security Posture - User hygiene, access key age, MFA compliance
- Service Metrics - Request rates, latencies, error rates
- Kubernetes Resources - CPU, memory, pod status

### Logs

View aggregated logs with Loki:

```bash
# Query logs in Grafana → Explore → Loki datasource
{namespace="sec-data"} |= "error"
{app="sec-collector"} | json | risk="high"
```

Or directly via kubectl:
```bash
kubectl logs -n sec-data -l app=sec-collector --tail=100 -f
kubectl logs -n sec-data -l app=sec-enricher --tail=100 -f
```

---

## Windows PowerShell Command Reference

If Make isn't working properly on Windows, use these PowerShell equivalents:

```powershell
# Initialize Terraform
cd infra\terraform; terraform init; cd ..\..

# Deploy infrastructure
cd infra\terraform; terraform apply -auto-approve; cd ..\..

# Destroy infrastructure
cd infra\terraform; terraform destroy -auto-approve; cd ..\..

# Update kubeconfig
aws eks update-kubeconfig --name sec-eks --region us-east-1

# Deploy services
kubectl apply -f charts\namespaces.yaml
helm upgrade --install sec-collector charts\sec-collector -n sec-data --create-namespace
helm upgrade --install sec-enricher charts\sec-enricher -n sec-data
helm upgrade --install sec-responder charts\sec-responder -n sec-data
helm upgrade --install sec-reporter charts\sec-reporter -n sec-data

# Deploy observability (requires Prometheus Operator)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack -n monitoring --create-namespace

# Upload Grafana dashboards
python scripts\push_dashboards.py

# Seed test events
python scripts\seed_events.py --queue-url $QUEUE_URL --count 100 --scenario mixed

# Run tests
foreach ($service in @('sec-collector', 'sec-enricher', 'sec-responder', 'sec-reporter')) {
    cd services\$service
    python -m pytest tests\ -v
    cd ..\..
}

# Lint Helm charts
foreach ($chart in @('sec-collector', 'sec-enricher', 'sec-responder', 'sec-reporter')) {
    helm lint charts\$chart
}

# Build Docker images
$ORG = "your-org"
foreach ($service in @('sec-collector', 'sec-enricher', 'sec-responder', 'sec-reporter')) {
    docker build -t ghcr.io/$ORG/sec-automation-aws/${service}:v1.0.0 services\$service
}

# Push Docker images
foreach ($service in @('sec-collector', 'sec-enricher', 'sec-responder', 'sec-reporter')) {
    docker push ghcr.io/$ORG/sec-automation-aws/${service}:v1.0.0
}

# Check deployment status
kubectl get all -n sec-data
kubectl get all -n monitoring

# View logs
kubectl logs -n sec-data -l app=sec-collector --tail=100 -f

# Clean up deployments
foreach ($chart in @('sec-collector', 'sec-enricher', 'sec-responder', 'sec-reporter')) {
    helm uninstall $chart -n sec-data
}
helm uninstall kube-prometheus-stack -n monitoring
kubectl delete namespace sec-data monitoring
```

---

## Troubleshooting

### Pods Not Starting

**Symptom:** Pods stuck in `Pending` or `CrashLoopBackOff`

**Diagnosis:**
```bash
kubectl get pods -n sec-data
kubectl describe pod <pod-name> -n sec-data
kubectl logs <pod-name> -n sec-data
```

**Common Causes:**
- Image pull failure → Check registry credentials
- Resource limits → Check node capacity
- IRSA misconfiguration → Verify role ARN in annotations
- Environment variable missing → Check values.yaml

### Make Not Working on Windows

**Symptom:** `make: The term 'make' is not recognized...` or `CreateProcess(NULL, echo., ...) failed`

**Solution 1: Install Make**
```powershell
# Install via winget
winget install GnuWin32.Make

# Add to PATH
$env:Path += ";C:\Program Files (x86)\GnuWin32\bin"

# Verify
make --version
```

**Solution 2: Use Direct Commands**
See [Windows PowerShell Command Reference](#windows-powershell-command-reference) section above for all equivalent commands.

**Solution 3: Use Git Bash or WSL2**
```bash
# In Git Bash or WSL2, Make works natively
make help
```

### SQS Permission Errors

**Symptom:** Collector logs show `AccessDenied` errors

**Fix:**
```bash
# Verify IRSA role has SQS permissions
aws iam get-role-policy \
  --role-name sec-collector-irsa \
  --policy-name sec-collector-sqs

# Check pod service account annotation
kubectl get sa collector-sa -n sec-data -o yaml | grep eks.amazonaws.com/role-arn
```

### Events Not Processing

**Symptom:** No events in collector logs despite seeding

**Diagnosis:**
```bash
# Check SQS queue has messages
aws sqs get-queue-attributes \
  --queue-url $SQS_URL \
  --attribute-names ApproximateNumberOfMessages

# Check EventBridge rule is active
aws events describe-rule --name iam-high-risk-rule

# Check CloudTrail is logging
aws cloudtrail get-trail-status --name <trail-name>
```

### Grafana Dashboard Not Loading

**Symptom:** Dashboard shows "No data"

**Fix:**
```bash
# Verify Prometheus datasource is configured
kubectl get svc -n monitoring kube-prom-stack-prometheus

# Check Prometheus is scraping metrics
kubectl port-forward -n monitoring svc/kube-prom-stack-prometheus 9090:9090
# Open http://localhost:9090/targets

# Ensure ServiceMonitor exists for each service
kubectl get servicemonitor -n sec-data
```

### High Memory Usage

**Symptom:** Pods OOMKilled or high memory alerts

**Fix:**
```bash
# Check current resource usage
kubectl top pods -n sec-data

# Increase memory limits in values.yaml
resources:
  limits:
    memory: 1Gi  # Increase from 512Mi
  requests:
    memory: 512Mi

# Redeploy
helm upgrade sec-collector charts/sec-collector -n sec-data
```

---

## Security Best Practices

### Implemented Security Controls

✅ **Network Segmentation**
- NetworkPolicies restrict pod-to-pod communication
- Private subnets for worker nodes
- NAT Gateways for outbound traffic

✅ **Least Privilege Access**
- IRSA roles with minimal permissions
- No static AWS credentials in pods
- Service accounts per microservice

✅ **Container Security**
- Non-root containers (USER 1000)
- Read-only root filesystem
- Dropped capabilities
- Vulnerability scanning (Trivy)

✅ **Policy as Code**
- Gatekeeper constraints for Kubernetes
- Terraform for infrastructure
- Helm for application deployment

✅ **Observability**
- Centralized logging (Loki)
- Metrics collection (Prometheus)
- Security dashboards (Grafana)
- Alert rules for incidents

### Additional Hardening Recommendations

🔒 **Enable Pod Security Standards**
```bash
kubectl label namespace sec-data \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```

🔒 **Encrypt SQS Messages**
- Use AWS KMS for encryption at rest
- Enable encryption in transit (HTTPS only)

🔒 **Enable EKS Encryption**
- Encrypt Kubernetes secrets with KMS
- Enable envelope encryption for etcd

🔒 **Implement GitOps**
- Use ArgoCD or Flux for deployment
- Git as single source of truth
- Automated sync and rollback

---

## Cost Optimization

### Reduce Infrastructure Costs

**Right-Size Worker Nodes:**
```hcl
# In infra/terraform/main.tf
eks_managed_node_groups = {
  default = {
    instance_types = ["t3.medium"]  # Down from t3.large
    desired_size = 2
    min_size = 1  # Allow scaling to 1 during low usage
    max_size = 3
  }
}
```

**Use Spot Instances:**
```hcl
eks_managed_node_groups = {
  spot = {
    instance_types = ["t3.medium", "t3a.medium"]
    capacity_type = "SPOT"
    desired_size = 2
  }
}
```

**Enable Cluster Autoscaler:**
```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --set autoDiscovery.clusterName=sec-eks \
  --namespace kube-system
```

### Development Environment

For testing/development, use a minimal setup:

```bash
# Use local Kind cluster instead of EKS
kind create cluster --name sec-dev

# Deploy services locally without AWS dependencies
helm install sec-collector charts/sec-collector \
  --set env[0].name=SQS_URL \
  --set env[0].value=mock-queue
```

---

## Contributing

### Development Workflow

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/sec-automation-aws.git
   cd sec-automation-aws
   git checkout -b feature/my-new-feature
   ```

2. **Make Changes**
   - Add tests for new functionality
   - Update documentation
   - Follow Python PEP 8 style guide

3. **Test Locally**
   ```bash
   # Run tests
   pytest services/sec-collector/tests/
   
   # Lint code
   flake8 services/
   black services/
   
   # Build Docker image
   docker build -t sec-collector:dev services/sec-collector
   ```

4. **Commit and Push**
   ```bash
   git add .
   git commit -m "feat: add new enrichment rule for privilege escalation"
   git push origin feature/my-new-feature
   ```

5. **Create Pull Request**
   - Describe changes and motivation
   - Link related issues
   - Ensure CI passes

### Code Style

- Python: PEP 8, type hints, docstrings
- Terraform: Standard formatting (terraform fmt)
- YAML: 2-space indentation
- Commit messages: Conventional Commits format

---

## License

MIT License - See LICENSE file for details

---

## Support

For issues, questions, or contributions:
- **GitHub Issues:** https://github.com/your-org/sec-automation-aws/issues
- **Documentation:** https://github.com/your-org/sec-automation-aws/wiki
- **Slack:** #security-automation

---

## Acknowledgments

This project uses:
- [Terraform AWS VPC Module](https://github.com/terraform-aws-modules/terraform-aws-vpc)
- [Terraform AWS EKS Module](https://github.com/terraform-aws-modules/terraform-aws-eks)
- [Prometheus Operator](https://github.com/prometheus-operator/prometheus-operator)
- [Grafana](https://grafana.com/)
- [OPA Gatekeeper](https://open-policy-agent.github.io/gatekeeper/)

---

**Built with ❤️ for Security Teams**
