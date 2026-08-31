terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "vault-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "Vault"
      Environment = var.environment
      ManagedBy = "Terraform"
    }
  }
}

# ---------------------------------------------------------------------------
# VPC & Networking
# ---------------------------------------------------------------------------

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.5.1"

  name = "vault-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "production"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

# ---------------------------------------------------------------------------
# RDS PostgreSQL
# ---------------------------------------------------------------------------

resource "aws_db_subnet_group" "vault" {
  name       = "vault-db-subnet"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_security_group" "rds" {
  name   = "vault-rds-sg"
  vpc_id = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "vault" {
  identifier = "vault-db-${var.environment}"

  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.db_instance_class

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = true

  db_name  = "vault_db"
  username = "vault_admin"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.vault.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az            = var.environment == "production"
  backup_retention_period = 7
  skip_final_snapshot = var.environment != "production"

  tags = {
    Name = "vault-database"
  }
}

# ---------------------------------------------------------------------------
# ElastiCache Redis
# ---------------------------------------------------------------------------

resource "aws_elasticache_subnet_group" "vault" {
  name       = "vault-cache-subnet"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_security_group" "redis" {
  name   = "vault-redis-sg"
  vpc_id = module.vpc.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_elasticache_cluster" "vault" {
  cluster_id           = "vault-redis-${var.environment}"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.redis_node_type
  num_cache_nodes      = var.environment == "production" ? 3 : 1
  port                 = 6379
  subnet_group_name     = aws_elasticache_subnet_group.vault.name
  security_group_ids   = [aws_security_group.redis.id]
  parameter_group_name = "default.redis7"
}

# ---------------------------------------------------------------------------
# S3 Bucket
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "assets" {
  bucket = "vault-assets-${var.environment}"
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket                  = aws_s3_bucket.assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------------------------------------------------------------------
# ECS Cluster
# ---------------------------------------------------------------------------

resource "aws_security_group" "ecs" {
  name   = "vault-ecs-sg"
  vpc_id = module.vpc.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecs_cluster" "vault" {
  name = "vault-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/vault-${var.environment}"
  retention_in_days = 30
}

# ---------------------------------------------------------------------------
# ECS Task Definitions (per service)
# ---------------------------------------------------------------------------

variable "services" {
  default = {
    api-gateway          = { port = 8000, cpu = 256, memory = 512 }
    usage-intelligence   = { port = 8001, cpu = 256, memory = 512 }
    trust-verification   = { port = 8002, cpu = 256, memory = 512 }
    market-matching      = { port = 8003, cpu = 256, memory = 512 }
    financial-orchestration = { port = 8004, cpu = 256, memory = 512 }
    compliance-risk      = { port = 8005, cpu = 256, memory = 512 }
  }
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "rds_endpoint" {
  value = aws_db_instance.vault.endpoint
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.vault.cache_nodes[0].address
}

output "s3_bucket" {
  value = aws_s3_bucket.assets.id
}

output "ecs_cluster" {
  value = aws_ecs_cluster.vault.name
}
