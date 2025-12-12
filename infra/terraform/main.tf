# infra/terraform/main.tf
provider "aws" { region = var.region }

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  name    = "sec-vpc"
  cidr    = "10.0.0.0/16"
  azs     = ["${var.region}a","${var.region}b"]
  public_subnets  = ["10.0.0.0/24","10.0.1.0/24"]
  private_subnets = ["10.0.10.0/24","10.0.11.0/24"]
}

module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  cluster_name    = var.cluster_name
  cluster_version = "1.29"
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets
  manage_aws_auth = true
  eks_managed_node_groups = {
    default = { instance_types = ["t3.large"], desired_size = 2, min_size = 2, max_size = 4 }
  }
}

resource "aws_sqs_queue" "iam_events" {
  name                      = "sec-iam-events"
  message_retention_seconds = 86400
}

resource "aws_cloudwatch_event_rule" "iam_high_risk" {
  name        = "iam-high-risk-rule"
  description = "Route privileged IAM actions to SQS"
  event_pattern = <<EOF
{
  "source": ["aws.iam"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventName": ["CreateAccessKey","AttachUserPolicy","PutUserPolicy","AddUserToGroup"]
  }
}
EOF
}

resource "aws_cloudwatch_event_target" "to_sqs" {
  rule      = aws_cloudwatch_event_rule.iam_high_risk.name
  target_id = "sqs"
  arn       = aws_sqs_queue.iam_events.arn
}

resource "aws_iam_role" "collector_irsa" {
  name = "sec-collector-irsa"
  assume_role_policy = data.aws_iam_policy_document.collector_assume.json
}

data "aws_iam_policy_document" "collector_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals { type = "Federated"; identifiers = [module.eks.oidc_provider_arn] }
    condition {
      test     = "StringEquals"
      variable = "${module.eks.oidc_provider}:sub"
      values   = ["system:serviceaccount:sec-data:collector-sa"]
    }
  }
}

resource "aws_iam_policy" "collector_sqs" {
  name   = "sec-collector-sqs"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = ["sqs:ReceiveMessage","sqs:DeleteMessage","sqs:GetQueueAttributes"],
      Resource = aws_sqs_queue.iam_events.arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "collector_attach" {
  role       = aws_iam_role.collector_irsa.name
  policy_arn = aws_iam_policy.collector_sqs.arn
}
