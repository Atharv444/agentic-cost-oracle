# ============================================================
# Apply this file to simulate a cost-increasing PR:
#   terraform plan -var-file="cost-increase.tfvars"
#
# These values will trigger Cost-Oracle recommendations.
# ============================================================

environment    = "production"
instance_type  = "m5.2xlarge"       # Up from t3.medium  (~$280/mo vs ~$30/mo)
db_instance_class = "db.r6g.2xlarge"  # Up from db.t3.medium (~$830/mo vs ~$58/mo)
