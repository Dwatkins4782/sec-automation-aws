AWS Security Automation Pipeline Quickstart Guide

🚀 Quickstart

This section provides the exact commands to fork, clone, and deploy the pipeline quickly.

1. Fork and Clone Repository

git clone https://github.com/your-org/sec-automation-aws.git
cd sec-automation-aws

2. Provision Infrastructure with Terraform

make init
make infra-up

3. Configure kubectl for EKS

make kubeconfig

4. Create Kubernetes Namespaces

kubectl apply -f charts/namespaces.yaml

5. Deploy Observability Stack (Prometheus, Loki, Grafana)

make observability

6. Deploy Microservices (Collector, Enricher, Responder, Reporter)

make deploy

7. Seed Test Events into SQS

export SQS_URL=$(aws sqs get-queue-url --queue-name sec-iam-events --query 'QueueUrl' --output text)
make seed

8. Push Grafana Dashboards

export GRAFANA_URL=http://<grafana-hostname>
export GRAFANA_TOKEN=<api-token>
make dashboards

9. Validate Metrics and Alerts

Collector metrics:

kubectl -n sec-data port-forward deploy/sec-collector 8000:8000
curl localhost:8000/metrics

Enricher latency:

kubectl -n sec-enricher port-forward deploy/sec-enricher 8000:8000
curl localhost:8000/metrics

Responder actions:

kubectl -n sec-response port-forward deploy/sec-responder 8000:8000
curl localhost:8000/metrics

10. Cleanup

helm uninstall sec-collector sec-enricher sec-responder sec-reporter
helm uninstall kube-prom-stack loki promtail -n monitoring
make infra-down