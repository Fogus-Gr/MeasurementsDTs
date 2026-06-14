# Contributing Guidelines

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [ONBOARDING.md](file://ONBOARDING.md)
- [.github/pull_request_template.md](file://.github/pull_request_template.md)
- [dev_tools/README.md](file://dev_tools/README.md)
- [tests/test_hpe_regressions.py](file://tests/test_hpe_regressions.py)
- [tests/contact_sheet_smoke/run_contact_sheet_smoke.py](file://tests/contact_sheet_smoke/run_contact_sheet_smoke.py)
- [unit_tests/images](file://unit_tests/images)
- [unit_tests/video](file://unit_tests/video)
- [utils/evaluator.py](file://utils/evaluator.py)
- [utils/log_parser.py](file://utils/log_parser.py)
- [utils/video_detection.py](file://utils/video_detection.py)
- [utils/visualizer.py](file://utils/visualizer.py)
- [models/AlphaPose/detector/yolox/tools/demo.py](file://models/AlphaPose/detector/yolox/tools/demo.py)
- [monitor_hpe/docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)
- [ffmpeg_hpe/docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [recent-dash/docker-compose.yml](file://recent-dash/docker-compose.yml)
- [Dockerfile.hpe](file://Dockerfile.hpe)
- [Makefile](file://Makefile)
- [requirements.txt](file://requirements.txt)
- [requirements_dev.txt](file://requirements_dev.txt)
- [setup.py](file://setup.py)
- [entrypoint.sh](file://entrypoint.sh)
- [dev_tools/install_from_readme.sh](file://dev_tools/install_from_readme.sh)
- [dev_tools/smoke_test.sh](file://dev_tools/smoke_test.sh)
</cite>

## Update Summary
**Changes Made**
- Updated Development Workflow section to reflect repository cleanup removing development artifacts
- Added new section on Repository Cleanup and Artifact Management
- Updated Troubleshooting Guide to include artifact cleanup procedures
- Enhanced Development Environment Setup with cleaner repository practices

## Table of Contents
1. [Introduction](#introduction)
2. [Repository Cleanup and Artifact Management](#repository-cleanup-and-artifact-management)
3. [Development Workflow](#development-workflow)
4. [Code Standards and Formatting](#code-standards-and-formatting)
5. [Review Process](#review-process)
6. [Pull Request Procedure](#pull-request-procedure)
7. [Issue Reporting and Feature Requests](#issue-reporting-and-feature-requests)
8. [Documentation Standards](#documentation-standards)
9. [Example Submission Requirements](#example-submission-requirements)
10. [Recognition Procedures](#recognition-procedures)
11. [Project Governance](#project-governance)
12. [Licensing and Intellectual Property](#licensing-and-intellectual-property)
13. [Community Contribution Opportunities](#community-contribution-opportunities)
14. [Troubleshooting Guide](#troubleshooting-guide)
15. [Appendix: Development Environment Setup](#appendix-development-environment-setup)

## Introduction
Thank you for your interest in contributing to the project. This document provides comprehensive guidance for contributors, covering development workflow, code standards, review processes, and community participation. The project involves human pose estimation research and experimentation with various frameworks and tools, including AlphaPose, OpenVINO, FFmpeg, and containerized environments.

**Updated** Repository structure has been cleaned to remove development artifacts, streamlining the development workflow and improving maintainability.

## Repository Cleanup and Artifact Management
The repository has undergone systematic cleanup to remove development artifacts and streamline the development environment.

### Removed Development Artifacts
- Shell history files: `full_shell_history.txt`, `hist.txt`
- Issue documentation: `bug.md`
- Backup files: `*.bak` files (e.g., `openvino_base_hpe.py.bak`, `roi_align.py.bak`)
- Temporary and cache files

### Benefits of Cleanup
- Reduced repository size and improved cloning performance
- Cleaner working directory for contributors
- Elimination of stale documentation and obsolete files
- Streamlined development workflow with fewer distractions

### Artifact Management Best Practices
- Use `.gitignore` patterns to prevent accidental commits of development artifacts
- Regularly clean up temporary files and logs
- Remove backup files before committing changes
- Use proper version control for documentation and issue tracking

**Section sources**
- [full_shell_history.txt](file://full_shell_history.txt)
- [hist.txt](file://hist.txt)
- [bug.md](file://bug.md)
- [openvino_base_hpe.py.bak](file://openvino_base_hpe.py.bak)
- [roi_align.py.bak](file://models/AlphaPose/alphapose/utils/roi_align/roi_align.py.bak)

## Development Workflow
This section outlines the recommended workflow for contributing to the project, from forking to submitting changes.

- Fork the repository on GitHub and clone your fork locally.
- Create a new branch for your work. Use a descriptive name that reflects the change (e.g., feat/add-new-model, fix/bug-in-detector).
- Work within your branch and stage changes incrementally.
- Commit your changes using clear, descriptive messages that explain the "why" and "what" of the change.
- Push your branch to your fork and open a pull request targeting the appropriate branch in the upstream repository.

Branch management best practices:
- Keep branches focused on a single concern to simplify reviews.
- Rebase your branch onto the latest upstream branch to minimize merge conflicts.
- Delete merged branches from your fork to keep the repository tidy.

Commit conventions:
- Use imperative mood in commit messages (e.g., "Add support for XYZ").
- Limit the first line to 50 characters and wrap subsequent lines at 72 characters.
- Reference related issues or PRs in the body when applicable.

Testing requirements:
- Run existing tests locally before submitting changes.
- Add new tests for significant functional changes.
- Ensure all tests pass in CI.

Review process:
- Pull requests are reviewed by maintainers who assess correctness, performance, and adherence to standards.
- Address reviewer feedback promptly and update the PR accordingly.
- Approved PRs are merged following project policies.

**Section sources**
- [.github/pull_request_template.md](file://.github/pull_request_template.md)
- [dev_tools/README.md](file://dev_tools/README.md)

## Code Standards and Formatting
The project follows Python-centric development practices with emphasis on readability, modularity, and reproducibility.

- Python style: Adhere to PEP 8 guidelines. Use meaningful variable and function names, and keep functions focused and testable.
- Docstrings: Include docstrings for modules, classes, and functions to explain purpose, parameters, return values, and exceptions.
- Imports: Group standard library imports, third-party imports, and local imports separately, with blank lines between groups.
- Logging: Use structured logging for diagnostics and performance measurements.
- Type hints: Prefer type hints for function signatures to improve code clarity.
- Error handling: Use explicit exception handling and meaningful error messages.
- Configuration: Centralize configuration in environment variables or configuration files; avoid hardcoded values.

Formatting automation:
- Use a formatter (e.g., black) and linter (e.g., flake8 or ruff) consistently across the project.
- Integrate pre-commit hooks to enforce formatting and linting automatically.

**Section sources**
- [utils/evaluator.py](file://utils/evaluator.py)
- [utils/log_parser.py](file://utils/log_parser.py)
- [utils/video_detection.py](file://utils/video_detection.py)
- [utils/visualizer.py](file://utils/visualizer.py)
- [models/AlphaPose/detector/yolox/tools/demo.py](file://models/AlphaPose/detector/yolox/tools/demo.py)

## Review Process
The review process ensures code quality, correctness, and alignment with project goals.

- Automated checks: CI runs tests, linting, and formatting checks. Resolve failures before requesting review.
- Human review: Maintainers review PRs for correctness, performance, maintainability, and documentation.
- Feedback incorporation: Respond to comments promptly and update the PR accordingly.
- Approval: PRs require maintainer approval before merging.

Review criteria:
- Correctness: Does the code solve the intended problem?
- Tests: Are there sufficient tests and do they pass?
- Documentation: Is the change documented appropriately?
- Performance: Does the change introduce regressions?
- Security: Are there potential security concerns?

**Section sources**
- [.github/pull_request_template.md](file://.github/pull_request_template.md)
- [tests/test_hpe_regressions.py](file://tests/test_hpe_regressions.py)
- [tests/contact_sheet_smoke/run_contact_sheet_smoke.py](file://tests/contact_sheet_smoke/run_contact_sheet_smoke.py)

## Pull Request Procedure
Follow these steps to submit a pull request effectively.

- Template completion: Use the pull request template to provide context, changes, testing steps, and impact assessment.
- Description: Clearly describe the problem being solved, the solution implemented, and any trade-offs.
- Testing: Include steps to reproduce and verify the change. Reference relevant tests and scripts.
- Screenshots/examples: Attach screenshots or example outputs when helpful.
- Related issues: Link to related issues or discussions.

Approval workflows:
- Multiple approvals may be required depending on the scope of changes.
- After approval, merge using squash or rebase to maintain a clean history.

**Section sources**
- [.github/pull_request_template.md](file://.github/pull_request_template.md)

## Issue Reporting and Feature Requests
Effective issue reporting helps maintainers prioritize and resolve problems quickly.

- Search existing issues: Before opening a new issue, search for duplicates.
- Use templates: Fill out the provided templates to include environment details, reproduction steps, expected vs. actual behavior, and logs.
- Provide context: Include relevant configuration, hardware/software versions, and environment details.
- Feature requests: Describe the problem you face and the desired outcome. Explain why current solutions are insufficient.

Feature request process:
- Discuss ideas in issues before implementing major features.
- Provide use cases and acceptance criteria.
- Collaborate on design decisions with maintainers.

**Section sources**
- [.github/pull_request_template.md](file://.github/pull_request_template.md)

## Documentation Standards
Documentation contributes to project maintainability and usability.

- Inline documentation: Document modules, classes, and functions with clear docstrings.
- User guides: Update README and domain-specific documents when adding new capabilities.
- Diagrams: Include diagrams for complex workflows or architectures.
- Examples: Provide runnable examples demonstrating new features.

**Section sources**
- [README.md](file://README.md)
- [ONBOARDING.md](file://ONBOARDING.md)
- [dev_tools/README.md](file://dev_tools/README.md)

## Example Submission Requirements
When submitting examples or demonstrations:

- Self-contained: Provide minimal, runnable examples with clear instructions.
- Dependencies: Specify required dependencies and versions.
- Validation: Include validation steps and expected outputs.
- Licensing: Ensure examples comply with project licensing terms.

**Section sources**
- [dev_tools/install_from_readme.sh](file://dev_tools/install_from_readme.sh)
- [dev_tools/smoke_test.sh](file://dev_tools/smoke_test.sh)

## Recognition Procedures
Contributors are acknowledged for their efforts.

- Pull requests: Contributors are recognized for accepted changes.
- Documentation: Significant documentation contributions are acknowledged.
- Community: Active participants may be invited to participate in decision-making.

Recognition mechanisms:
- Contributor lists in documentation.
- Acknowledgments in release notes.
- Invitation to maintain or contribute to specific areas.

**Section sources**
- [README.md](file://README.md)

## Project Governance
The project operates under a maintainer-driven governance model.

Decision-making:
- Maintainers review and approve changes.
- Major decisions are discussed in issues and PRs.
- Consensus is encouraged; maintainers have the final say on technical direction.

Maintainer responsibilities:
- Code review and feedback.
- Ensuring quality and adherence to standards.
- Guiding contributors and maintaining project health.

**Section sources**
- [.github/pull_request_template.md](file://.github/pull_request_template.md)

## Licensing and Intellectual Property
The project requires contributors to comply with licensing obligations.

- Contributor License Agreement (CLA): Contributors may be required to sign a CLA before merging.
- License headers: Preserve existing license headers in modified files.
- Third-party components: Ensure compliance with third-party licenses for included components.

Intellectual property considerations:
- Respect third-party rights when integrating external components.
- Document license obligations for redistributed artifacts.

**Section sources**
- [.claude/settings.local.json](file://.claude/settings.local.json)

## Community Contribution Opportunities
There are several ways to contribute to the project.

- Code contributions: Bug fixes, new features, performance improvements.
- Documentation: Improving guides, tutorials, and API documentation.
- Testing: Adding tests and improving test coverage.
- Examples: Creating demos and tutorials.
- Feedback: Providing feedback on issues and proposals.

**Section sources**
- [README.md](file://README.md)
- [ONBOARDING.md](file://ONBOARDING.md)

## Troubleshooting Guide
Common issues and resolutions during development.

- Environment setup: Use provided installation scripts and compose files to set up the environment.
- Running tests: Execute regression and smoke tests locally before submitting changes.
- Logs and diagnostics: Use logging utilities and parsers to diagnose issues.
- Containerization: Leverage Docker configurations for consistent environments.
- Artifact cleanup: Remove development artifacts and temporary files to maintain a clean repository.

**Updated** Repository cleanup procedures now include systematic removal of development artifacts to maintain a clean working environment.

**Section sources**
- [dev_tools/install_from_readme.sh](file://dev_tools/install_from_readme.sh)
- [dev_tools/smoke_test.sh](file://dev_tools/smoke_test.sh)
- [utils/log_parser.py](file://utils/log_parser.py)
- [monitor_hpe/docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)
- [ffmpeg_hpe/docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [recent-dash/docker-compose.yml](file://recent-dash/docker-compose.yml)

## Appendix: Development Environment Setup
Set up your development environment using the provided resources.

- Prerequisites: Install required dependencies as specified in requirements files.
- Virtual environment: Create and activate a virtual environment.
- Build and install: Use setup.py or make targets to build and install the package.
- Scripts: Utilize provided shell scripts for installation and smoke testing.
- Entrypoints: Use entrypoint scripts to initialize services and experiments.
- Artifact management: Regularly clean up temporary files and remove development artifacts.

**Updated** Development environment setup now includes repository cleanup procedures to ensure contributors start with a clean, artifact-free workspace.

**Section sources**
- [requirements.txt](file://requirements.txt)
- [requirements_dev.txt](file://requirements_dev.txt)
- [setup.py](file://setup.py)
- [Makefile](file://Makefile)
- [Dockerfile.hpe](file://Dockerfile.hpe)
- [entrypoint.sh](file://entrypoint.sh)
- [dev_tools/install_from_readme.sh](file://dev_tools/install_from_readme.sh)
- [dev_tools/smoke_test.sh](file://dev_tools/smoke_test.sh)