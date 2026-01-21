#!/usr/bin/env bash
# cleanup.sh - DQF Project Cleanup & Backup
# Usage: 
#   ./cleanup.sh          → Clean + backup
#   ./cleanup.sh restore  → Restore last backup

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BACKUP_DIR="../dqf-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Git tag for versioning
GIT_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v4.8.3")

echo -e "${BLUE}🧹 DQF CLEANUP & BACKUP${NC}"
echo "========================================"
echo ""

# Function: Create backup
backup_project() {
    echo -e "${YELLOW}📦 Creating backup...${NC}"
    
    mkdir -p "$BACKUP_DIR"
    
    BACKUP_PATH="${BACKUP_DIR}/dqf_${GIT_TAG}_${TIMESTAMP}"
    
    # Create backup (exclude .git, _work, __pycache__)
    rsync -a \
        --exclude='.git' \
        --exclude='_work' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache' \
        --exclude='result' \
        --exclude='result-*' \
        --exclude='htmlcov' \
        --exclude='.coverage' \
        "$PROJECT_ROOT/" \
        "$BACKUP_PATH/"
    
    echo -e "${GREEN}✅ Backup created: $BACKUP_PATH${NC}"
    echo ""
}

# Function: Clean Python artifacts
clean_python() {
    echo -e "${YELLOW}🗑️  Cleaning Python artifacts...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Remove __pycache__
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    
    # Remove .pyc files
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    find . -type f -name "*.pyd" -delete 2>/dev/null || true
    
    # Remove pytest cache
    rm -rf .pytest_cache
    
    # Remove coverage
    rm -rf htmlcov .coverage
    
    echo -e "${GREEN}✅ Python artifacts cleaned${NC}"
}

# Function: Clean backup files
clean_backups() {
    echo -e "${YELLOW}🗑️  Cleaning backup files (.bak, .bkp)...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Find and remove .bak/.bkp files
    BAK_FILES=$(find . -type f \( -name "*.bak" -o -name "*.bkp" \) 2>/dev/null || true)
    
    if [ -n "$BAK_FILES" ]; then
        echo "$BAK_FILES" | while read -r file; do
            echo "  Removing: $file"
            rm "$file"
        done
        echo -e "${GREEN}✅ Backup files cleaned${NC}"
    else
        echo -e "${GREEN}✅ No backup files found${NC}"
    fi
}

# Function: Clean temporary scripts
clean_temp_scripts() {
    echo -e "${YELLOW}🗑️  Cleaning temporary scripts...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Move utility scripts to proper location
    if [ -f "tests/clean_non_ascii.sh" ]; then
        echo "  Moving: tests/clean_non_ascii.sh → scripts/utils/"
        mkdir -p scripts/utils
        mv "tests/clean_non_ascii.sh" "scripts/utils/"
    fi
    
    if [ -f "tests/check_test_structure.py" ]; then
        echo "  Moving: tests/check_test_structure.py → scripts/utils/"
        mkdir -p scripts/utils
        mv "tests/check_test_structure.py" "scripts/utils/"
    fi
    
    # Clean tests/ artifacts
    if [ -d "tests/checks" ] && [ -z "$(ls -A tests/checks)" ]; then
        rmdir tests/checks
    fi
    
    echo -e "${GREEN}✅ Utility scripts organized${NC}"
}

# Function: Clean work directory
clean_work() {
    echo -e "${YELLOW}🗑️  Cleaning _work directory...${NC}"
    
    if [ -d "_work" ]; then
        rm -rf _work/*
        echo -e "${GREEN}✅ _work directory cleaned${NC}"
    else
        echo -e "${GREEN}✅ No _work directory${NC}"
    fi
}

# Function: Clean docs output files
clean_docs() {
    echo -e "${YELLOW}🗑️  Cleaning docs output files...${NC}"
    
    cd "$PROJECT_ROOT/docs"
    
    # Remove generated HTML/Quarto files (keep source .md)
    rm -rf DQF_PROJECT_files/ DQF_PROJECT.html 2>/dev/null || true
    
    # Archive mif_output_*.txt
    if ls mif_output_*.txt 1> /dev/null 2>&1; then
        mkdir -p archive
        mv mif_output_*.txt archive/ 2>/dev/null || true
        echo -e "${GREEN}✅ Output files archived${NC}"
    else
        echo -e "${GREEN}✅ No output files to clean${NC}"
    fi
}

# Function: Clean empty directories
clean_empty_dirs() {
    echo -e "${YELLOW}🗑️  Cleaning empty directories...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Find and remove empty dirs (except .git)
    find . -type d -empty ! -path "./.git/*" -delete 2>/dev/null || true
    
    echo -e "${GREEN}✅ Empty directories cleaned${NC}"
}

# Function: Restore backup
restore_backup() {
    echo -e "${YELLOW}🔄 Restoring from backup...${NC}"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        echo -e "${RED}❌ No backups found in $BACKUP_DIR${NC}"
        exit 1
    fi
    
    # List available backups
    echo "Available backups:"
    ls -1t "$BACKUP_DIR" | head -10 | nl
    echo ""
    
    # Get latest backup
    LATEST_BACKUP=$(ls -1t "$BACKUP_DIR" | head -1)
    
    read -p "Restore from latest backup ($LATEST_BACKUP)? [y/N] " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Restoring from: $LATEST_BACKUP${NC}"
        
        # Safety: create pre-restore backup
        PRE_RESTORE_BACKUP="${BACKUP_DIR}/pre_restore_${TIMESTAMP}"
        rsync -a \
            --exclude='.git' \
            --exclude='_work' \
            --exclude='__pycache__' \
            "$PROJECT_ROOT/" \
            "$PRE_RESTORE_BACKUP/"
        
        echo -e "${GREEN}✅ Pre-restore backup created${NC}"
        
        # Restore
        rsync -a --delete \
            --exclude='.git' \
            "${BACKUP_DIR}/${LATEST_BACKUP}/" \
            "$PROJECT_ROOT/"
        
        echo -e "${GREEN}✅ Restored from: $LATEST_BACKUP${NC}"
        echo -e "${BLUE}ℹ️  Pre-restore backup: $PRE_RESTORE_BACKUP${NC}"
    else
        echo "Restore cancelled"
    fi
}

# Function: Summary
print_summary() {
    echo ""
    echo "========================================"
    echo -e "${GREEN}✅ CLEANUP COMPLETE${NC}"
    echo "========================================"
    echo ""
    echo "📋 Summary:"
    echo "   ✅ Python artifacts cleaned (__pycache__, .pyc)"
    echo "   ✅ Backup files removed (.bak, .bkp)"
    echo "   ✅ Temporary scripts archived"
    echo "   ✅ _work directory cleaned"
    echo "   ✅ Docs output archived"
    echo "   ✅ Empty directories removed"
    echo "   ✅ Backup created: ${BACKUP_DIR}/dqf_${GIT_TAG}_${TIMESTAMP}"
    echo ""
    echo "🔍 Next steps:"
    echo "   git status        # Review changes"
    echo "   just test         # Verify tests still pass"
    echo "   ./cleanup.sh restore  # Restore if needed"
    echo ""
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    if [ "${1:-}" = "restore" ]; then
        restore_backup
        exit 0
    fi
    
    # Perform cleanup
    backup_project
    clean_python
    clean_backups
    clean_temp_scripts
    clean_work
    clean_docs
    clean_empty_dirs
    print_summary
}

main "$@"