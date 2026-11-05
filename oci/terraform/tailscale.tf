# One policy owner for the whole existing tailnet; import before any update.
# Provider 0.29.3 validates policy syntax/tests during plan, but updates have no
# ETag guard. Serialize writers and invalidate ALL saved plans after console
# recovery edits; follow the policy recovery procedure in docs/operations.md.
resource "tailscale_acl" "tailnet" {
  acl                        = file("${path.module}/../ansible/tailscale/policy.hujson")
  overwrite_existing_content = false
  reset_acl_on_destroy       = false

  lifecycle {
    prevent_destroy = true
  }
}
