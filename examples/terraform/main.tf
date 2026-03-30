# ============================================================
# EDITED: High-Cost Infrastructure for Cost-Oracle Testing
# ============================================================

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── Variables ────────────────────────────────────────────────

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production" # CHANGED: Switched to production to trigger Multi-AZ costs
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string 
  default     = "p3.8xlarge" # CHANGED: Switched from t3.medium to an expensive GPU instance
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r6g.4xlarge" # CHANGED: Switched to a high-memory database instance
}

# ── EC2 Instance ─────────────────────────────────────────────

resource "aws_instance" "web" {
  ami           = "ami-0c02fb55956c7d316" 
  instance_type = var.instance_type

  root_block_device {
    volume_size = 1000  # CHANGED: Increased from 30GB to 1TB (Huge cost jump)
    volume_type = "io2" # CHANGED: Switched to Provisioned IOPS (Very expensive)
    iops        = 10000 
  }

  tags = {
    Name        = "${var.environment}-web-server"
    Environment = var.environment
  }
}

# ── RDS Database ─────────────────────────────────────────────

resource "aws_db_instance" "main" {
  identifier     = "${var.environment}-postgres"
  engine         = "postgres"
  engine_version = "15.4"

  instance_class        = var.db_instance_class
  allocated_storage     = 2000 # CHANGED: Increased to 2TB
  storage_type          = "io2" # CHANGED: High-performance storage
  iops                  = 20000

  db_name  = "appdb"
  username = "dbadmin"
  password = "SuperSecretPassword123!" # Agent should flag hardcoded password

  multi_az            = true # Multi-AZ doubles the database cost
  skip_final_snapshot = true

  tags = {
    Name        = "${var.environment}-postgres"
    Environment = var.environment
  }
}

# ── S3 Bucket (No changes needed, lifecycle is good) ─────────

resource "aws_s3_bucket" "assets" {
  bucket = "${var.environment}-app-assets-${random_id.bucket_suffix.hex}"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# ── NAT Gateway ──────────────────────────────────────────────

resource "aws_nat_gateway" "main" {
  allocation_id = "eipalloc-placeholder"
  subnet_id     = "subnet-placeholder"

  tags = {
    Name = "${var.environment}-nat-gateway"
  }
}
