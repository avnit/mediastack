#!/bin/bash

# This script will remove sensitive files from git tracking while keeping them locally
# Run this ONCE before committing the .gitignore file

echo "Removing sensitive files from git tracking (files will remain on disk)..."

# Remove .env files from git tracking
git rm --cached .env 2>/dev/null && echo "✓ Removed .env from git tracking" || echo "ℹ .env not tracked"
git rm --cached .env-old 2>/dev/null && echo "✓ Removed .env-old from git tracking" || echo "ℹ .env-old not tracked"
git rm --cached homepage.env 2>/dev/null && echo "✓ Removed homepage.env from git tracking" || echo "ℹ homepage.env not tracked"

echo ""
echo "✓ Done! Your local files are safe."
echo ""
echo "Next steps:"
echo "1. git add .gitignore .env.template"
echo "2. git commit -m 'Add .gitignore and env template, remove sensitive files from tracking'"
echo "3. git push"
echo ""
echo "After this, 'git pull' will never touch your local .env files again."
