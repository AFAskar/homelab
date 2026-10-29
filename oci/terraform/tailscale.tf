# One policy owner for the whole existing tailnet; import before any update.
# Provider 0.29.3 validates policy syntax and tests with Tailscale during plan.
resource "tailscale_acl" "tailnet" {
  acl                        = file("${path.module}/../ansible/tailscale/policy.hujson")
  overwrite_existing_content = false
  reset_acl_on_destroy       = false

  lifecycle {
    prevent_destroy = true
  }
}
