# ============================================================
# Example Terraform — AWS Web Application Stack
# Used to demonstrate Cost-Oracle analysis on PR changes.
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
  default     = "staging"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"  # Try changing to m5.xlarge to trigger Cost-Oracle
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"  # Try changing to db.r6g.xlarge
}

# ── EC2 Instance ─────────────────────────────────────────────

resource "aws_instance" "web" {
  ami           = "ami-0c02fb55956c7d316"  # Amazon Linux 2023
  instance_type = var.instance_type

  root_block_device {
    volume_size = 30   # Try changing to 500 to see Cost-Oracle flag it
    volume_type = "gp3"
  }

  tags = {
    Name        = "${var.environment}-web-server"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ── RDS Database ─────────────────────────────────────────────

resource "aws_db_instance" "main" {
  identifier     = "${var.environment}-postgres"
  engine         = "postgres"
  engine_version = "15.4"

  instance_class        = var.db_instance_class
  allocated_storage     = 100
  max_allocated_storage = 500
  storage_type          = "gp3"

  db_name  = "appdb"
  username = "dbadmin"
  password = "change-me-in-secrets-manager"  # Cost-Oracle will flag this too

  multi_az            = var.environment == "production" ? true : false
  skip_final_snapshot = true

  tags = {
    Name        = "${var.environment}-postgres"
    Environment = var.environment
  }
}

# ── S3 Bucket ────────────────────────────────────────────────

resource "aws_s3_bucket" "assets" {
  bucket = "${var.environment}-app-assets-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "${var.environment}-assets"
    Environment = var.environment
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_lifecycle_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 180
      storage_class = "GLACIER"
    }
  }
}

# ── NAT Gateway (common cost anti-pattern) ───────────────────

resource "aws_eip" "nat" {
  domain = "vpc"
  tags = {
    Name = "${var.environment}-nat-eip"
  }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = "subnet-placeholder"  # Replace with real subnet

  tags = {
    Name = "${var.environment}-nat-gateway"
  }
}

# ── Outputs ──────────────────────────────────────────────────

output "web_instance_id" {
  value = aws_instance.web.id
}

output "db_endpoint" {
  value = aws_db_instance.main.endpoint
}

output "monthly_cost_note" {
  value = "Run 'infracost breakdown --path=.' to estimate costs"
}
