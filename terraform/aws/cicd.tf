# ═══════════════════════════════════════════════════════════════════════════════
# CI/CD PIPELINE — CodePipeline + CodeBuild + CodeDeploy (Blue/Green)
# ═══════════════════════════════════════════════════════════════════════════════
# Enable with: enable_cicd = true
# Blue/Green with: enable_blue_green = true
# ═══════════════════════════════════════════════════════════════════════════════

# ── Data Source for AWS Account ID ────────────────────────────────────────────

data "aws_caller_identity" "current" {}

# ── S3 Bucket for Pipeline Artifacts ──────────────────────────────────────────

resource "aws_s3_bucket" "pipeline_artifacts" {
  count  = var.enable_cicd ? 1 : 0
  bucket = "${local.prefix}-pipeline-artifacts"
  
  tags = { Name = "${local.prefix}-pipeline-artifacts" }
}

resource "aws_s3_bucket_versioning" "pipeline_artifacts" {
  count  = var.enable_cicd ? 1 : 0
  bucket = aws_s3_bucket.pipeline_artifacts[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

# ── CodeBuild IAM Role ────────────────────────────────────────────────────────

resource "aws_iam_role" "codebuild" {
  count = var.enable_cicd ? 1 : 0
  name  = "${local.prefix}-codebuild-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "codebuild.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "codebuild" {
  count = var.enable_cicd ? 1 : 0
  name  = "${local.prefix}-codebuild-policy"
  role  = aws_iam_role.codebuild[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.pipeline_artifacts[0].arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.app_secrets.arn
      }
    ]
  })
}

# ── CodeBuild Project — Backend ───────────────────────────────────────────────

resource "aws_codebuild_project" "backend" {
  count        = var.enable_cicd ? 1 : 0
  name         = "${local.prefix}-backend-build"
  description  = "Build Huron backend Docker image"
  service_role = aws_iam_role.codebuild[0].arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type                        = "LINUX_CONTAINER"
    privileged_mode             = true  # Required for Docker builds
    image_pull_credentials_type = "CODEBUILD"

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }
    environment_variable {
      name  = "AWS_REGION"
      value = var.aws_region
    }
    environment_variable {
      name  = "ECR_REPO_URL"
      value = aws_ecr_repository.backend.repository_url
    }
    environment_variable {
      name  = "IMAGE_TAG"
      value = "latest"
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = <<-BUILDSPEC
      version: 0.2
      phases:
        pre_build:
          commands:
            - echo Logging in to Amazon ECR...
            - aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
            - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
            - IMAGE_TAG=$${COMMIT_HASH:=latest}
        build:
          commands:
            - echo Building Docker image...
            - docker build -f Dockerfile.production -t $ECR_REPO_URL:latest -t $ECR_REPO_URL:$IMAGE_TAG .
        post_build:
          commands:
            - echo Pushing Docker image...
            - docker push $ECR_REPO_URL:latest
            - docker push $ECR_REPO_URL:$IMAGE_TAG
            - printf '[{"name":"backend","imageUri":"%s"}]' $ECR_REPO_URL:$IMAGE_TAG > imagedefinitions.json
      artifacts:
        files:
          - imagedefinitions.json
          - appspec.yaml
          - taskdef.json
    BUILDSPEC
  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.backend.name
      stream_name = "codebuild"
    }
  }

  tags = { Name = "${local.prefix}-backend-build" }
}

# ── CodeBuild Project — Frontend ──────────────────────────────────────────────

resource "aws_codebuild_project" "frontend" {
  count        = var.enable_cicd ? 1 : 0
  name         = "${local.prefix}-frontend-build"
  description  = "Build Huron frontend Docker image"
  service_role = aws_iam_role.codebuild[0].arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type                        = "LINUX_CONTAINER"
    privileged_mode             = true
    image_pull_credentials_type = "CODEBUILD"

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }
    environment_variable {
      name  = "AWS_REGION"
      value = var.aws_region
    }
    environment_variable {
      name  = "ECR_REPO_URL"
      value = aws_ecr_repository.frontend.repository_url
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = <<-BUILDSPEC
      version: 0.2
      phases:
        pre_build:
          commands:
            - echo Logging in to Amazon ECR...
            - aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
            - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
            - IMAGE_TAG=$${COMMIT_HASH:=latest}
        build:
          commands:
            - cd frontend
            - docker build -f Dockerfile.production -t $ECR_REPO_URL:latest -t $ECR_REPO_URL:$IMAGE_TAG .
        post_build:
          commands:
            - docker push $ECR_REPO_URL:latest
            - docker push $ECR_REPO_URL:$IMAGE_TAG
            - printf '[{"name":"frontend","imageUri":"%s"}]' $ECR_REPO_URL:$IMAGE_TAG > ../imagedefinitions-frontend.json
      artifacts:
        files:
          - imagedefinitions-frontend.json
    BUILDSPEC
  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.frontend.name
      stream_name = "codebuild"
    }
  }

  tags = { Name = "${local.prefix}-frontend-build" }
}

# ── CodePipeline IAM Role ─────────────────────────────────────────────────────

resource "aws_iam_role" "codepipeline" {
  count = var.enable_cicd ? 1 : 0
  name  = "${local.prefix}-codepipeline-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "codepipeline.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "codepipeline" {
  count = var.enable_cicd ? 1 : 0
  name  = "${local.prefix}-codepipeline-policy"
  role  = aws_iam_role.codepipeline[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject",
          "s3:GetBucketVersioning"
        ]
        Resource = [
          aws_s3_bucket.pipeline_artifacts[0].arn,
          "${aws_s3_bucket.pipeline_artifacts[0].arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "codebuild:BatchGetBuilds",
          "codebuild:StartBuild"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:DescribeTasks",
          "ecs:ListTasks",
          "ecs:RegisterTaskDefinition",
          "ecs:UpdateService"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "codedeploy:CreateDeployment",
          "codedeploy:GetDeployment",
          "codedeploy:GetApplication",
          "codedeploy:GetApplicationRevision",
          "codedeploy:RegisterApplicationRevision",
          "codedeploy:GetDeploymentConfig"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = "codestar-connections:UseConnection"
        Resource = var.github_connection_arn
      },
      {
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = [
          aws_iam_role.ecs_task_execution.arn,
          aws_iam_role.ecs_task.arn
        ]
      }
    ]
  })
}

# ── CodePipeline — Main Pipeline ──────────────────────────────────────────────

resource "aws_codepipeline" "main" {
  count    = var.enable_cicd && var.github_connection_arn != "" ? 1 : 0
  name     = "${local.prefix}-pipeline"
  role_arn = aws_iam_role.codepipeline[0].arn

  artifact_store {
    location = aws_s3_bucket.pipeline_artifacts[0].bucket
    type     = "S3"
  }

  # Stage 1: Source from GitHub
  stage {
    name = "Source"

    action {
      name             = "GitHub"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        ConnectionArn    = var.github_connection_arn
        FullRepositoryId = var.github_repo
        BranchName       = var.github_branch
      }
    }
  }

  # Stage 2: Build Docker images
  stage {
    name = "Build"

    action {
      name             = "BuildBackend"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["backend_build_output"]
      version          = "1"

      configuration = {
        ProjectName = aws_codebuild_project.backend[0].name
      }
    }

    action {
      name             = "BuildFrontend"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["frontend_build_output"]
      version          = "1"

      configuration = {
        ProjectName = aws_codebuild_project.frontend[0].name
      }
    }
  }

  # Stage 3: Deploy to ECS
  stage {
    name = "Deploy"

    action {
      name            = "DeployBackend"
      category        = "Deploy"
      owner           = "AWS"
      provider        = var.enable_blue_green ? "CodeDeployToECS" : "ECS"
      input_artifacts = ["backend_build_output"]
      version         = "1"

      configuration = var.enable_blue_green ? {
        ApplicationName                = aws_codedeploy_app.backend[0].name
        DeploymentGroupName            = aws_codedeploy_deployment_group.backend[0].deployment_group_name
        TaskDefinitionTemplateArtifact = "backend_build_output"
        TaskDefinitionTemplatePath     = "taskdef.json"
        AppSpecTemplateArtifact        = "backend_build_output"
        AppSpecTemplatePath            = "appspec.yaml"
      } : {
        ClusterName = aws_ecs_cluster.main.name
        ServiceName = aws_ecs_service.backend.name
        FileName    = "imagedefinitions.json"
      }
    }

    action {
      name            = "DeployFrontend"
      category        = "Deploy"
      owner           = "AWS"
      provider        = "ECS"  # Frontend uses rolling update
      input_artifacts = ["frontend_build_output"]
      version         = "1"

      configuration = {
        ClusterName = aws_ecs_cluster.main.name
        ServiceName = aws_ecs_service.frontend.name
        FileName    = "imagedefinitions-frontend.json"
      }
    }
  }

  tags = { Name = "${local.prefix}-pipeline" }
}

# ═══════════════════════════════════════════════════════════════════════════════
# BLUE/GREEN DEPLOYMENT — CodeDeploy for ECS
# ═══════════════════════════════════════════════════════════════════════════════

# ── CodeDeploy IAM Role ───────────────────────────────────────────────────────

resource "aws_iam_role" "codedeploy" {
  count = var.enable_blue_green ? 1 : 0
  name  = "${local.prefix}-codedeploy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "codedeploy.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "codedeploy_ecs" {
  count      = var.enable_blue_green ? 1 : 0
  role       = aws_iam_role.codedeploy[0].name
  policy_arn = "arn:aws:iam::aws:policy/AWSCodeDeployRoleForECS"
}

# ── Blue/Green Target Groups ──────────────────────────────────────────────────

resource "aws_lb_target_group" "backend_green" {
  count       = var.enable_blue_green ? 1 : 0
  name        = "${local.prefix}-backend-green"
  port        = 8004
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    matcher             = "200"
  }

  tags = { Name = "${local.prefix}-backend-green" }
}

# ── ALB Listener for Blue/Green (test traffic on port 8080) ──────────────────

resource "aws_lb_listener" "test" {
  count             = var.enable_blue_green ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = 8080
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend_green[0].arn
  }
}

# ── CodeDeploy Application ────────────────────────────────────────────────────

resource "aws_codedeploy_app" "backend" {
  count            = var.enable_blue_green ? 1 : 0
  name             = "${local.prefix}-backend"
  compute_platform = "ECS"
}

# ── CodeDeploy Deployment Group ───────────────────────────────────────────────

resource "aws_codedeploy_deployment_group" "backend" {
  count                  = var.enable_blue_green ? 1 : 0
  app_name               = aws_codedeploy_app.backend[0].name
  deployment_group_name  = "${local.prefix}-backend-dg"
  service_role_arn       = aws_iam_role.codedeploy[0].arn
  deployment_config_name = "CodeDeployDefault.ECSLinear10PercentEvery1Minutes"

  auto_rollback_configuration {
    enabled = true
    events  = ["DEPLOYMENT_FAILURE", "DEPLOYMENT_STOP_ON_ALARM"]
  }

  blue_green_deployment_config {
    deployment_ready_option {
      action_on_timeout = "CONTINUE_DEPLOYMENT"
    }

    terminate_blue_instances_on_deployment_success {
      action                           = "TERMINATE"
      termination_wait_time_in_minutes = 5
    }
  }

  deployment_style {
    deployment_option = "WITH_TRAFFIC_CONTROL"
    deployment_type   = "BLUE_GREEN"
  }

  ecs_service {
    cluster_name = aws_ecs_cluster.main.name
    service_name = aws_ecs_service.backend.name
  }

  load_balancer_info {
    target_group_pair_info {
      prod_traffic_route {
        listener_arns = [aws_lb_listener.http.arn]
      }

      test_traffic_route {
        listener_arns = [aws_lb_listener.test[0].arn]
      }

      target_group {
        name = aws_lb_target_group.backend.name
      }

      target_group {
        name = aws_lb_target_group.backend_green[0].name
      }
    }
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUTS — CI/CD
# ═══════════════════════════════════════════════════════════════════════════════

output "pipeline_url" {
  description = "CodePipeline console URL"
  value       = var.enable_cicd && var.github_connection_arn != "" ? "https://${var.aws_region}.console.aws.amazon.com/codesuite/codepipeline/pipelines/${local.prefix}-pipeline/view" : "CI/CD not enabled"
}

output "codedeploy_app" {
  description = "CodeDeploy application name"
  value       = var.enable_blue_green ? aws_codedeploy_app.backend[0].name : "Blue/Green not enabled"
}
