#!/bin/bash
# Run this on the GCP VM after SSH-ing in
# curl -sSL https://raw.githubusercontent.com/Kroszborg/hookiq/main/deploy/setup-gcp-vm.sh | bash

set -e

echo "=== HookIQ GCP VM Setup ==="

# 1. System deps
sudo apt-get update -qq
sudo apt-get install -y git curl

# 2. Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 3. Install Docker Compose plugin
sudo apt-get install -y docker-compose-plugin

# 4. Clone repo
if [ ! -d "hookiq" ]; then
  git clone https://github.com/Kroszborg/hookiq.git
fi
cd hookiq

# 5. Create .env (user must fill in API key)
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "=== ACTION REQUIRED ==="
  echo "Edit .env and add your GROQ_API_KEY:"
  echo "  nano .env"
  echo "Then run: docker compose up -d --build"
else
  echo ".env already exists"
fi

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "1. nano .env  (add GROQ_API_KEY and set FRONTEND_URL)"
echo "2. docker compose up -d --build"
echo "3. docker compose logs -f  (check logs)"
