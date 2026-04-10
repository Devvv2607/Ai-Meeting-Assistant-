# Deployment Guide

## Production Deployment

This guide covers deploying the AI Meeting Intelligence Platform to production using AWS services and Docker.

## Architecture

```
┌─────────────┐
│   Route53   │ DNS
└──────┬──────┘
       │
┌──────▼──────────────┐
│   CloudFront        │ CDN
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│   ALB/NLB           │ Load Balancer
└──────┬──────────────┘
       │
┌──────▼─────────────────────────┐
│        ECS Fargate              │
├─────────────┬─────────────────┤
│  Frontend   │  Backend API    │
│  (Next.js)  │  (FastAPI)      │
└──────┬──────┴────────┬────────┘
       │                │
┌──────▼──────────────┐ │
│  RDS PostgreSQL     │ │
│  (Multi-AZ)         │ │
└─────────────────────┘ │
                        │
┌───────────────────────▼──────┐
│   ElastiCache Redis           │
│   (Cluster Mode Enabled)      │
└──────────────────────────────┘
       │
┌──────▼──────────────────┐
│   S3                    │
│   (Audio Storage)       │
└─────────────────────────┘
```

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- Docker
- Terraform (optional, for infrastructure as code)

## Step 1: Prepare AWS Infrastructure

### Create IAM User for Deployment

```bash
aws iam create-user --user-name ai-meeting-deployer
aws iam attach-user-policy --user-name ai-meeting-deployer \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess
aws iam attach-user-policy --user-name ai-meeting-deployer \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
aws iam attach-user-policy --user-name ai-meeting-deployer \
  --policy-arn arn:aws:iam::aws:policy/AWSRDSFullAccess
```

### Create S3 Bucket for Audio

```bash
aws s3 mb s3://ai-meeting-production-bucket --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket ai-meeting-production-bucket \
  --versioning-configuration Status=Enabled

# Configure lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket ai-meeting-production-bucket \
  --lifecycle-configuration file://s3-lifecycle.json
```

### Create RDS PostgreSQL Instance

```bash
aws rds create-db-instance \
  --db-instance-identifier ai-meeting-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15 \
  --master-username aiuser \
  --master-user-password $(openssl rand -base64 32) \
  --allocated-storage 100 \
  --storage-type gp3 \
  --backup-retention-period 30 \
  --multi-az \
  --storage-encrypted
```

### Create ElastiCache Redis Cluster

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id ai-meeting-redis \
  --cache-node-type cache.t3.medium \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 3 \
  --automatic-failover-enabled
```

### Create ECR Repositories

```bash
# Backend
aws ecr create-repository \
  --repository-name ai-meeting/backend \
  --region us-east-1

# Frontend
aws ecr create-repository \
  --repository-name ai-meeting/frontend \
  --region us-east-1

# Worker
aws ecr create-repository \
  --repository-name ai-meeting/worker \
  --region us-east-1
```

## Step 2: Build and Push Docker Images

### Get ECR Login Token

```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
```

### Build Backend Image

```bash
cd backend

docker build -t ai-meeting/backend:latest .

docker tag ai-meeting/backend:latest \
  <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-meeting/backend:latest

docker tag ai-meeting/backend:latest \
  <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-meeting/backend:$(git rev-parse --short HEAD)

docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-meeting/backend:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-meeting/backend:$(git rev-parse --short HEAD)
```

### Build Frontend Image

```bash
cd frontend

docker build -t ai-meeting/frontend:latest .

docker tag ai-meeting/frontend:latest \
  <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-meeting/frontend:latest

docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-meeting/frontend:latest
```

### Build Worker Image

```bash
cd backend

docker build -f Dockerfile.worker -t ai-meeting/worker:latest .

docker tag ai-meeting/worker:latest \
  <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-meeting/worker:latest

docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-meeting/worker:latest
```

## Step 3: Create ECS Cluster

```bash
aws ecs create-cluster \
  --cluster-name ai-meeting-production \
  --cluster-settings name=containerInsights,value=enabled
```

## Step 4: Create ECS Task Definitions

### Backend Task Definition

Create `backend-task-def.json`:

```json
{
  "family": "ai-meeting-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-meeting/backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DEBUG",
          "value": "False"
        },
        {
          "name": "DEVICE",
          "value": "cpu"
        },
        {
          "name": "WHISPER_MODEL",
          "value": "base"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:ai-meeting/database-url"
        },
        {
          "name": "REDIS_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:ai-meeting/redis-url"
        },
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:ai-meeting/secret-key"
        },
        {
          "name": "AWS_ACCESS_KEY_ID",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:ai-meeting/aws-access-key"
        },
        {
          "name": "AWS_SECRET_ACCESS_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:ai-meeting/aws-secret-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ai-meeting-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 40
      }
    }
  ],
  "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskRole"
}
```

Register task definition:

```bash
aws ecs register-task-definition --cli-input-json file://backend-task-def.json
```

## Step 5: Create CloudWatch Log Groups

```bash
aws logs create-log-group --log-group-name /ecs/ai-meeting-backend
aws logs create-log-group --log-group-name /ecs/ai-meeting-frontend
aws logs create-log-group --log-group-name /ecs/ai-meeting-worker
```

## Step 6: Store Secrets in AWS Secrets Manager

```bash
# Generate secure random values
DB_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 32)

# Store database URL
aws secretsmanager create-secret \
  --name ai-meeting/database-url \
  --secret-string "postgresql://aiuser:$DB_PASSWORD@ai-meeting-db.c9akciq32.us-east-1.rds.amazonaws.com:5432/ai_meeting"

# Store Redis URL
aws secretsmanager create-secret \
  --name ai-meeting/redis-url \
  --secret-string "redis://ai-meeting-redis.c9akciq32.ng.0001.use1.cache.amazonaws.com:6379/0"

# Store secret key
aws secretsmanager create-secret \
  --name ai-meeting/secret-key \
  --secret-string "$SECRET_KEY"
```

## Step 7: Create ECS Services

### Backend Service

```bash
aws ecs create-service \
  --cluster ai-meeting-production \
  --service-name ai-meeting-backend \
  --task-definition ai-meeting-backend:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-zzz],assignPublicIp=DISABLED}" \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:<ACCOUNT_ID>:targetgroup/ai-meeting-backend/xxx,containerName=backend,containerPort=8000 \
  --enable-ecs-managed-tags \
  --enable-execute-command
```

### Frontend Service

```bash
aws ecs create-service \
  --cluster ai-meeting-production \
  --service-name ai-meeting-frontend \
  --task-definition ai-meeting-frontend:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-zzz],assignPublicIp=DISABLED}" \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:<ACCOUNT_ID>:targetgroup/ai-meeting-frontend/xxx,containerName=frontend,containerPort=3000
```

### Worker Service

```bash
aws ecs create-service \
  --cluster ai-meeting-production \
  --service-name ai-meeting-worker \
  --task-definition ai-meeting-worker:1 \
  --desired-count 3 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-zzz],assignPublicIp=DISABLED}"
```

## Step 8: Set Up Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name ai-meeting-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-zzz

# Create target groups
aws elbv2 create-target-group \
  --name ai-meeting-backend \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxx \
  --target-type ip \
  --health-check-enabled \
  --health-check-path /health

aws elbv2 create-target-group \
  --name ai-meeting-frontend \
  --protocol HTTP \
  --port 3000 \
  --vpc-id vpc-xxx \
  --target-type ip

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:<ACCOUNT_ID>:loadbalancer/app/ai-meeting-alb/xxx \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:<ACCOUNT_ID>:targetgroup/ai-meeting-frontend/xxx
```

## Step 9: Configure Auto Scaling

```bash
# Create auto scaling target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/ai-meeting-production/ai-meeting-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

# Create scaling policy
aws application-autoscaling put-scaling-policy \
  --policy-name ai-meeting-backend-scaling \
  --service-namespace ecs \
  --resource-id service/ai-meeting-production/ai-meeting-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

## Step 10: Set Up CloudFront Distribution

```bash
# For frontend CDN
aws cloudfront create-distribution \
  --distribution-config file://cloudfront-config.json
```

## Step 11: Configure Route53 DNS

```bash
# Create hosted zone (if not exists)
aws route53 create-hosted-zone \
  --name aiemeeting.com \
  --caller-reference $(date +%s)

# Create DNS records
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch file://dns-records.json
```

## Step 12: Enable Monitoring and Logging

### CloudWatch Dashboard

```bash
aws cloudwatch put-dashboard \
  --dashboard-name ai-meeting \
  --dashboard-body file://dashboard.json
```

### Set Up Alarms

```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name ai-meeting-backend-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:<ACCOUNT_ID>:ai-meeting-alerts

# Services health check
aws cloudwatch put-metric-alarm \
  --alarm-name ai-meeting-service-unhealthy \
  --alarm-description "Alert when service is unhealthy" \
  --metric-name HealthyHostCount \
  --namespace AWS/ELB \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator LessThanThreshold
```

## Step 13: Run Database Migrations

```bash
# Connect to RDS instance
aws ecs execute-command \
  --cluster ai-meeting-production \
  --task <task-id> \
  --container backend \
  --interactive \
  --command "/bin/bash"

# Inside container
python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

## Step 14: Enable SSL/TLS

```bash
# Request certificate
aws acm request-certificate \
  --domain-name aiemeeting.com \
  --subject-alternative-names '*.aiemeeting.com' \
  --validation-method DNS

# Update ALB listener to use HTTPS
aws elbv2 modify-listener \
  --listener-arn arn:aws:elasticloadbalancing:us-east-1:<ACCOUNT_ID>:listener/app/ai-meeting-alb/xxx/xxx \
  --protocol HTTPS \
  --certificates CertificateArn=arn:aws:acm:us-east-1:<ACCOUNT_ID>:certificate/xxx
```

## Monitoring and Maintenance

### View Logs

```bash
# Backend logs
aws logs tail /ecs/ai-meeting-backend --follow

# Frontend logs
aws logs tail /ecs/ai-meeting-frontend --follow

# Worker logs
aws logs tail /ecs/ai-meeting-worker --follow
```

### Scale Services

```bash
# Scale backend to 5 tasks
aws ecs update-service \
  --cluster ai-meeting-production \
  --service ai-meeting-backend \
  --desired-count 5
```

### Update Service

```bash
# Update to latest image
aws ecs update-service \
  --cluster ai-meeting-production \
  --service ai-meeting-backend \
  --force-new-deployment
```

## Performance Tuning

### Database Optimization

```sql
-- Create indexes
CREATE INDEX idx_meeting_user_id ON meetings(user_id);
CREATE INDEX idx_transcript_meeting_id ON transcripts(meeting_id);
CREATE INDEX idx_transcript_embedding ON transcripts USING ivfflat (embedding);
```

### Redis Monitoring

```bash
# Check Redis info
redis-cli -h ai-meeting-redis.c9akciq32.ng.0001.use1.cache.amazonaws.com info
```

## Disaster Recovery

### Backup Strategy

```bash
# Daily automated RDS backups
aws rds modify-db-instance \
  --db-instance-identifier ai-meeting-db \
  --backup-retention-period 30

# S3 lifecycle policies
# Keep backups for 90 days
```

### Recovery Procedure

```bash
# Restore from backup
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier ai-meeting-db-restored \
  --db-snapshot-identifier ai-meeting-db-snapshot-xxx

# Restore ECS configuration from code repository
```

## Cost Optimization

1. Use Fargate Spot instances for worker tasks (70% savings)
2. Set up Auto Scaling with target tracking
3. Use CloudFront for static assets
4. Set S3 lifecycle policies to move old data to Glacier
5. Monitor unused resources with AWS Cost Explorer

## Conclusion

Your AI Meeting Intelligence Platform is now deployed to production! 

### Next Steps

1. ✅ Monitor application in CloudWatch
2. ✅ Set up automated backups
3. ✅ Implement monitoring dashboards
4. ✅ Plan capacity based on usage

For support and updates, refer to the main README.md
