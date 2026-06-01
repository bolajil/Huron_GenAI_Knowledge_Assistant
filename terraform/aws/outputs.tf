output "aws_region" {
  description = "AWS region where resources are deployed"
  value       = var.aws_region
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS name (use this if no custom domain)"
  value       = "http://${aws_lb.main.dns_name}"
}

output "frontend_url" {
  description = "Frontend application URL"
  value       = var.certificate_arn != "" ? "https://${aws_lb.main.dns_name}" : "http://${aws_lb.main.dns_name}"
}

output "backend_url" {
  description = "Backend API URL"
  value       = var.certificate_arn != "" ? "https://${aws_lb.main.dns_name}/api" : "http://${aws_lb.main.dns_name}/api"
}

output "api_docs_url" {
  description = "Swagger UI - interactive API documentation"
  value       = var.certificate_arn != "" ? "https://${aws_lb.main.dns_name}/docs" : "http://${aws_lb.main.dns_name}/docs"
}

output "ecr_backend_url" {
  description = "ECR repository URL for the backend image"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  description = "ECR repository URL for the frontend image"
  value       = aws_ecr_repository.frontend.repository_url
}

output "ecr_push_commands" {
  description = "Commands to push images to ECR"
  value = <<-EOT
    aws ecr get-login-password --region ${var.aws_region} | \
      docker login --username AWS --password-stdin ${aws_ecr_repository.backend.repository_url}

    # Backend
    docker build -t ${aws_ecr_repository.backend.repository_url}:latest ./backend
    docker push ${aws_ecr_repository.backend.repository_url}:latest

    # Frontend
    docker build -t ${aws_ecr_repository.frontend.repository_url}:latest ./frontend
    docker push ${aws_ecr_repository.frontend.repository_url}:latest

    # Restart ECS services to pick up new images
    aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${aws_ecs_service.backend.name} --force-new-deployment
    aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${aws_ecs_service.frontend.name} --force-new-deployment
  EOT
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "s3_bucket_name" {
  description = "S3 bucket for document storage"
  value       = aws_s3_bucket.documents.bucket
}

output "secrets_manager_arn" {
  description = "Secrets Manager ARN for app secrets"
  value       = aws_secretsmanager_secret.app_secrets.arn
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "cloudwatch_backend_log_group" {
  description = "CloudWatch log group for backend"
  value       = aws_cloudwatch_log_group.backend.name
}
