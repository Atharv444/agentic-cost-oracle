# ============================================================
# AGENTIC COST-ORACLE: EXTREME COST DEMO (STAGING VS PROD)
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
  region = "us-east-1"
}

# ── EC2 GPU CLUSTER (The Massive Money Spender) ──────────────

resource "aws_instance" "ml_worker" {
  ami           = "ami-0c02fb55956c7d316"
  # Using the p3.16xlarge (roughly $24/hour)
  instance_type = "p3.16xlarge" 

  root_block_device {
    volume_size = 2000    # 2 Terabytes of storage
    volume_type = "io2"   # Provisioned IOPS (Extremely expensive)
    iops        = 50000   # Maxing out the IOPS to maximize the bill
  }

  tags = {
    Name        = "Enterprise-ML-Worker"
    Environment = "production"
  }
}

# ── ENTERPRISE DATABASE (Multi-AZ High Performance) ──────────

resource "aws_db_instance" "enterprise_db" {
  identifier        = "oracle-test-db-prod"
  engine            = "postgres"
  # Massive memory-optimized instance
  instance_class    = "db.r6g.8xlarge" 
  allocated_storage = 3000             # 3 Terabytes
  storage_type      = "io2"
  iops              = 60000            # Very high performance costs

  # This setting literally doubles the entire DB bill
  multi_az          = true  
  
  db_name  = "proddb"
  username = "admin"
  
  # Agentic Oracle should flag this hardcoded password as a security risk
  password = "SuperSecretAdminPassword123!" 

  skip_final_snapshot = true
}

# ── HIGH-CAPACITY STORAGE ────────────────────────────────────

resource "aws_s3_bucket" "massive_storage" {
  bucket = "expensive-data-lake-oracle-demo-001"
}

# NOTE: We have removed all NAT Gateway and Subnet placeholders 
# to ensure Infracost calculates the costs with 100% accuracy.
