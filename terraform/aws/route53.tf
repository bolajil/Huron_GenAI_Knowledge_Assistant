# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE 53 — DNS Configuration
# ═══════════════════════════════════════════════════════════════════════════════
# Requires: route53_zone_id and domain_name variables to be set
# ═══════════════════════════════════════════════════════════════════════════════

# ── Create Hosted Zone (if managing DNS in AWS) ───────────────────────────────
# Uncomment if you want Terraform to create the hosted zone
# Otherwise, create it manually and provide the zone_id

# resource "aws_route53_zone" "main" {
#   count = var.create_hosted_zone ? 1 : 0
#   name  = var.domain_name
#   
#   tags = { Name = "${local.prefix}-zone" }
# }

# ── Primary Domain → ALB ──────────────────────────────────────────────────────

resource "aws_route53_record" "root" {
  count   = var.route53_zone_id != "" && var.domain_name != "" ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# ── WWW Subdomain → ALB ───────────────────────────────────────────────────────

resource "aws_route53_record" "www" {
  count   = var.route53_zone_id != "" && var.domain_name != "" ? 1 : 0
  zone_id = var.route53_zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# ── API Subdomain → ALB (optional, for api.domain.com) ────────────────────────

resource "aws_route53_record" "api" {
  count   = var.route53_zone_id != "" && var.domain_name != "" ? 1 : 0
  zone_id = var.route53_zone_id
  name    = "api.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# ── Health Check for Primary Domain ───────────────────────────────────────────

resource "aws_route53_health_check" "main" {
  count             = var.route53_zone_id != "" && var.domain_name != "" ? 1 : 0
  fqdn              = var.domain_name
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health"
  failure_threshold = 3
  request_interval  = 30

  tags = { Name = "${local.prefix}-health-check" }
}

# ── ACM Certificate Validation (if using ACM) ─────────────────────────────────
# This creates DNS validation records for ACM certificates

resource "aws_route53_record" "cert_validation" {
  for_each = var.route53_zone_id != "" && var.certificate_arn != "" ? {} : {}
  # Certificate validation records would go here if creating cert via Terraform
  # For now, assume certificate is pre-created in ACM
  zone_id = var.route53_zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUTS — DNS
# ═══════════════════════════════════════════════════════════════════════════════

output "domain_url" {
  description = "Primary domain URL"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "No custom domain configured"
}

output "api_url" {
  description = "API endpoint URL"
  value       = var.domain_name != "" ? "https://api.${var.domain_name}" : "https://${aws_lb.main.dns_name}/api"
}

output "route53_nameservers" {
  description = "Route 53 nameservers (if zone managed by Terraform)"
  value       = "Configure in your domain registrar"
}
