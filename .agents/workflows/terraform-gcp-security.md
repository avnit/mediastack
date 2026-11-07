---
description: Lints and reviews Terraform HCL files for GCP security issues. Auto-invokes   when working with .tf files, `terraform plan` output, or when user asks to   "check terraform", "review tf", or "secure my infra". Covers IAM, networking,   storage, comput
---

# Terraform GCP Security Linter

You are reviewing Terraform for GCP security misconfigurations.

## High-Priority Checks

### IAM
```
CRITICAL: member = "allUsers" or "allAuthenticatedUsers"
CRITICAL: role = "roles/owner" on non-breakglass accounts
HIGH:     role = "roles/editor" on service accounts
HIGH:     google_service_account_key resource (key rotation bypass)
MED:      Missing condition blocks on sensitive role bindings
```

### Networking
```
CRITICAL: google_compute_firewall — source_ranges = ["0.0.0.0/0"] with ports 22/3389
HIGH:     google_compute_instance — no shielded VM config
HIGH:     google_compute_subnetwork — private_ip_google_access = false
MED:      google_compute_network — no VPC flow logs
```

### Storage & Data
```
CRITICAL: google_storage_bucket — uniform_bucket_level_access = false
CRITICAL: google_storage_bucket — public_access_prevention = "inherited" 
HIGH:     google_bigquery_dataset — access block with allUsers
HIGH:     google_sql_database_instance — no backup_configuration
MED:      google_storage_bucket — no versioning for sensitive buckets
```

### Secrets & Keys
```
CRITICAL: Hardcoded credentials in variable defaults or locals
HIGH:     google_kms_crypto_key — rotation_period not set
HIGH:     sensitive = false on outputs containing secret values
```

## Output Format

For each finding:
```
[SEVERITY] Resource: <resource_type>.<name>
  Line: <approximate line or block>
  Issue: <what's wrong>
  Fix:   <exact Terraform snippet to remediate>
```

Then: tfsec / checkov equivalent control IDs where applicable.