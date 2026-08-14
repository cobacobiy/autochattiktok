#!/usr/bin/env bash
# ==============================================================================
# GitHub Actions Self-Hosted Runner Setup Script for autochattiktok
# Target Repo: https://github.com/cobacobiy/autochattiktok
# ==============================================================================

set -e

REPO_URL="https://github.com/cobacobiy/autochattiktok"
DEFAULT_RUNNER_DIR="/home/gpu/actions-runner-autochat/runner-autochattiktok"
DEFAULT_RUNNER_NAME="runner-autochattiktok"
RUNNER_VERSION="2.322.0"

RUNNER_TOKEN="${1}"
RUNNER_DIR="${2:-$DEFAULT_RUNNER_DIR}"
RUNNER_NAME="${3:-$DEFAULT_RUNNER_NAME}"

if [ -z "$RUNNER_TOKEN" ]; then
  echo "================================================================="
  echo " Error: GitHub Actions Runner Token is required!"
  echo " Usage: ./scripts/setup_github_runner.sh <RUNNER_TOKEN> [RUNNER_DIR] [RUNNER_NAME]"
  echo ""
  echo " Obtain RUNNER_TOKEN from:"
  echo " https://github.com/cobacobiy/autochattiktok/settings/actions/runners/new"
  echo "================================================================="
  exit 1
fi

echo "================================================================="
echo " Setting up GitHub Actions Runner for: $REPO_URL"
echo " Target Directory : $RUNNER_DIR"
echo " Runner Name       : $RUNNER_NAME"
echo "================================================================="

mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

if [ ! -f "config.sh" ]; then
  echo "Downloading GitHub Actions Runner v${RUNNER_VERSION}..."
  curl -o actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz -L \
    "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
  
  tar xzf ./actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
  rm -f ./actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
fi

echo "Configuring GitHub Actions Runner..."
./config.sh \
  --url "$REPO_URL" \
  --token "$RUNNER_TOKEN" \
  --name "$RUNNER_NAME" \
  --labels "self-hosted,226node2,ginee,autochattiktok" \
  --work "$RUNNER_DIR/_work" \
  --unattended \
  --replace

echo "Installing and starting runner service..."
if [ -f "./svc.sh" ]; then
  sudo ./svc.sh install || true
  sudo ./svc.sh start || true
fi

echo "================================================================="
echo " GitHub Actions Runner setup completed successfully!"
echo " Status check: sudo ./svc.sh status"
echo "================================================================="
