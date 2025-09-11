#!/bin/bash

# List of target branches
branches=("cuda-dev" "feat/openvino-cpu-opt" "feat/openvino-opti-cpu" "feat/ov-epyc-4vcpu")

# Store current branch
current_branch=$(git branch --show-current)

# Loop through each branch
for branch in "${branches[@]}"; do
  echo "Processing branch: $branch"
  
  # Checkout the branch
  git checkout "$branch"
  
  # Check if the entry already exists in .gitignore
  if ! grep -q "models/AlphaPose/detector/nms/build" .gitignore; then
    echo "Adding entry to .gitignore"
    echo "models/AlphaPose/detector/nms/build" >> .gitignore
    git add .gitignore
    git commit -m "Add nms build to gitignore"
  else
    echo "Entry already exists in .gitignore, skipping"
  fi
done

# Return to the original branch
echo "Returning to original branch: $current_branch"
git checkout "$current_branch"