# ============================================================
# AGENTIC COST-ORACLE: EXTREME COST DEMO
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

# ── EC2 GPU CLUSTER (The Big Money Spender) ──────────────────

resource "aws_instance" "ml_worker" {
  ami           = "ami-0c02fb55956c7d316"
  # We are using the most expensive GPU instance available
  instance_type = "p3.16xlarge" 

  root_block_device {
    volume_size = 2000    # 2 Terabytes
    volume_type = "io2"   # Provisioned IOPS (Very expensive)
    iops        = 32000   # Max performance = Max Cost
  }

  tags = {
    Name        = "Costly-ML-Worker"
    Environment = "production"
  }
}

# ── DATABASE (Multi-AZ Enterprise Storage) ───────────────────

resource "aws_db_instance" "enterprise_db" {
  identifier        = "oracle-test-db"
  engine            = "postgres"
  instance_class    = "db.r6g.8xlarge" # Massive memory instance
  allocated_storage = 3000             # 3 Terabytes
  storage_type      = "io2"
  iops              = 40000

  multi_az          = true  # This instantly doubles the monthly bill
  
  db_name  = "proddb"
  username = "admin"
  password = "HardcodedPassword123!" # AI Agent should flag this security risk

  skip_final_snapshot = true
}

# ── HIGH-TRAFFIC DATA STORAGE ───────────────────────────────

resource "aws_s3_bucket" "massive_storage" {
  bucket = "expensive-data-bucket-oracle-demo"
}

# (Notice: We removed the NAT Gateway placeholders to ensure Infracost runs perfectly)
