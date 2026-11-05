resource "oci_budget_budget" "credits" {
  provider       = oci.home
  compartment_id = var.tenancy_ocid
  display_name   = "homelab-oci-credits"
  amount         = 250 * var.billing_units_per_eur
  reset_period   = "MONTHLY"
  target_type    = "COMPARTMENT"
  targets        = [var.tenancy_ocid]
  description    = "Tenancy-wide monthly alerts; not a spending cap or cumulative trial-credit meter."
}
resource "oci_budget_alert_rule" "credits" {
  provider       = oci.home
  for_each       = toset(["200", "225", "240"])
  budget_id      = oci_budget_budget.credits.id
  display_name   = "actual-eur-${each.value}"
  type           = "ACTUAL"
  threshold_type = "ABSOLUTE"
  threshold      = tonumber(each.value) * var.billing_units_per_eur
  recipients     = var.budget_recipients
}
