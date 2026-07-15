#!/bin/bash
# Build script for IBM Storage Protect MCP Server wheel distribution
# This script creates a wheel file for easy installation

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}IBM Storage Protect MCP Server Builder${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: pyproject.toml not found. Please run this script from the project root.${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo -e "${RED}Error: Python 3.10 or higher is required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python version check passed: $PYTHON_VERSION${NC}"

# Clean previous builds
echo ""
echo -e "${YELLOW}Cleaning previous build artifacts...${NC}"
rm -rf build/ dist/ *.egg-info src/*.egg-info

# Install/upgrade build tools
echo ""
echo -e "${YELLOW}Installing/upgrading build tools...${NC}"
python3 -m pip install --upgrade pip build wheel setuptools

# Build the wheel
echo ""
echo -e "${YELLOW}Building wheel distribution...${NC}"
python3 -m build --wheel

# Check if build was successful
if [ ! -d "dist" ] || [ -z "$(ls -A dist/*.whl 2>/dev/null)" ]; then
    echo -e "${RED}Error: Wheel build failed. No wheel file found in dist/${NC}"
    exit 1
fi

# Display results
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Generated wheel file(s):${NC}"
ls -lh dist/*.whl

# Get the wheel filename
WHEEL_FILE=$(ls dist/*.whl | head -n 1)
WHEEL_NAME=$(basename "$WHEEL_FILE")

echo ""
echo -e "${GREEN}Installation instructions:${NC}"
echo -e "${YELLOW}1. Copy the wheel file to your target system:${NC}"
echo "   scp $WHEEL_FILE user@target-host:/tmp/"
echo ""
echo -e "${YELLOW}2. On the target system, install the wheel:${NC}"
echo "   pip install /tmp/$WHEEL_NAME"
echo ""
echo -e "${YELLOW}3. Or install directly from this location:${NC}"
echo "   pip install $WHEEL_FILE"
echo ""
echo -e "${GREEN}For distribution, upload to PyPI or share the wheel file directly.${NC}"
echo ""
