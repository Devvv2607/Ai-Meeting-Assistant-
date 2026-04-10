#!/bin/bash
# Setup and run AI Meeting Intelligence Platform

echo "🚀 AI Meeting Intelligence Platform - Setup Script"
echo "=================================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose are installed${NC}"

# Create environment file
echo -e "\n${YELLOW}Setting up environment...${NC}"

if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ Created .env file${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env with your AWS credentials and other settings${NC}"
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
fi

# Create required directories
echo -e "\n${YELLOW}Creating required directories...${NC}"
mkdir -p tmp
mkdir -p uploads
echo -e "${GREEN}✅ Directories created${NC}"

# Build images
echo -e "\n${YELLOW}Building Docker images...${NC}"
docker-compose build

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to build images${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Images built successfully${NC}"

# Start services
echo -e "\n${YELLOW}Starting services...${NC}"
docker-compose up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to start services${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Services started${NC}"

# Wait for services to be ready
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Check service health
echo -e "\n${YELLOW}Checking service health...${NC}"

echo -e "\nService Status:"
docker-compose ps

# Test API
echo -e "\n${YELLOW}Testing API...${NC}"
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)

if [ "$API_RESPONSE" == "200" ]; then
    echo -e "${GREEN}✅ Backend API is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Backend API is not responding yet (will be ready in a moment)${NC}"
fi

# Print next steps
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}📍 Access Your Application:${NC}"
echo -e "  Frontend:  ${GREEN}http://localhost:3000${NC}"
echo -e "  Backend:   ${GREEN}http://localhost:8000${NC}"
echo -e "  API Docs:  ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  Database:  localhost:5432"
echo -e "  Redis:     localhost:6379"

echo -e "\n${YELLOW}📚 Documentation:${NC}"
echo -e "  Quick Start:   ${GREEN}QUICKSTART.md${NC}"
echo -e "  Development:   ${GREEN}DEVELOPMENT.md${NC}"
echo -e "  API Docs:      ${GREEN}API.md${NC}"
echo -e "  Deployment:    ${GREEN}DEPLOYMENT.md${NC}"

echo -e "\n${YELLOW}🎯 Next Steps:${NC}"
echo -e "  1. Read QUICKSTART.md"
echo -e "  2. Create a test user account at http://localhost:3000"
echo -e "  3. Upload a meeting audio file"
echo -e "  4. Monitor processing in docker logs"

echo -e "\n${YELLOW}📊 Monitor Services:${NC}"
echo -e "  View Logs:     ${GREEN}docker-compose logs -f${NC}"
echo -e "  View Status:   ${GREEN}docker-compose ps${NC}"
echo -e "  Stop Services: ${GREEN}docker-compose down${NC}"

echo -e "\n${GREEN}Happy meeting intelligence! 🚀${NC}\n"
