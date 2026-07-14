# Contributing Guide

Thank you for considering contributing to AI Portfolio Builder! This document outlines the development workflow, coding standards, and contribution guidelines.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Development Setup](#2-development-setup)
3. [Architecture Overview](#3-architecture-overview)
4. [Coding Standards](#4-coding-standards)
5. [Testing](#5-testing)
6. [Git Workflow](#6-git-workflow)
7. [Module Development Rules](#7-module-development-rules)
8. [Pull Request Guidelines](#8-pull-request-guidelines)

---

## 1. Getting Started

Before contributing:
1. Read [ARCHITECTURE.md](./ARCHITECTURE.md) to understand the project structure.
2. Read [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) to set up your environment.
3. Review [TODO.md](./TODO.md) to see what's planned.
4. Check open issues on GitHub for tasks to pick up.

---

## 2. Development Setup

```bash
# Clone the repository
git clone https://github.com/your-username/aiportfoliobuilder.git
cd aiportfoliobuilder/aiportfoliobuilder

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your local settings (SQLite is fine for development)

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

---

## 3. Architecture Overview

The project follows a **multi-app Django architecture** where each feature domain is its own app. See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full diagram.

Key rules:
- **Service layer**: Business logic goes in `services.py` files, not views.
- **Thin views**: Views coordinate requests and delegate to services.
- **Permission mixins**: Authorization goes in reusable mixins.
- **Signal auto-provisioning**: Use Django signals for automatic record creation.

---

## 4. Coding Standards

### Python Style
- Follow **PEP 8** conventions.
- Maximum line length: **120 characters**.
- Use **type hints** for function signatures.
- Add **docstrings** to all classes and non-trivial functions.

```python
def process_theme_upload(theme: Theme, zip_file: InMemoryUploadedFile) -> None:
    """
    Validates and extracts a theme ZIP file, creates ThemeAsset records,
    and generates a placeholder thumbnail.

    Args:
        theme: The Theme instance to update.
        zip_file: The uploaded ZIP file object.

    Raises:
        ThemeUploadError: If validation fails at any stage.
    """
```

### Imports
Organize imports in this order:
1. Standard library
2. Django
3. Third-party packages
4. Local app imports

### Error Handling
- Use specific exception types, not bare `except`.
- Log errors using Python's `logging` module.
- Never expose internal error details to users.

### Logging
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Portfolio %d published to GitHub", portfolio.pk)
logger.error("GitHub publish failed for portfolio %d: %s", portfolio.pk, str(e))
```

### Security
- Never hardcode secrets — use `python-decouple` / environment variables.
- Always validate user-uploaded files.
- Use `get_object_or_404` and ownership checks to prevent unauthorized access.
- Return `HttpResponseForbidden` (403) when a resource exists but the user lacks permission.
- Return `Http404` only when the resource genuinely does not exist.

---

## 5. Testing

### Running Tests
```bash
python manage.py test
```

### Writing Tests
- Place tests in the app's `tests.py` file.
- Each test class should inherit from `django.test.TestCase`.
- Use descriptive test method names: `test_<what_you_are_testing>`.
- Write a docstring explaining what the test verifies.

```python
class PortfolioBuilderTestCase(TestCase):
    """Test suite for Portfolio Builder module."""

    def test_portfolio_deletion_by_owner(self):
        """Verify owner can delete a portfolio and its data gets removed."""
        portfolio = Portfolio.objects.create(user=self.user, name="To Delete")
        res = self.client.post(reverse("portfolio:delete", kwargs={"pk": portfolio.pk}))
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Portfolio.objects.filter(pk=portfolio.pk).exists())
```

### Test Coverage Guidelines
- **Minimum**: Every new view, model method, and service function should have a test.
- **Target**: 50+ tests across all modules.
- **Don't**: Delete or overwrite existing tests when adding new ones.

---

## 6. Git Workflow

### Branch Naming
```
feature/module-12-security-hardening
fix/analytics-n1-query
docs/architecture-guide
```

### Commit Messages
Follow the Conventional Commits format:
```
feat(analytics): add prefetch_related to eliminate N+1 queries
fix(portfolio): return 403 instead of 404 for unauthorized API access
docs(architecture): add data flow diagrams
test(payments): add checkout failure scenario test
```

### Making a Commit
```bash
git add .
git commit -m "feat(module-12): optimize database queries and fix permission checks"
git push origin feature/your-branch-name
```

---

## 7. Module Development Rules

Each module must:
1. **Follow the service layer pattern** — no business logic in views.
2. **Add automated tests** — at minimum 4 new tests per module.
3. **Update documentation** — update `TODO.md`, `CHANGELOG.md`, `PROJECT_STATUS.md`.
4. **Not break existing tests** — run `python manage.py test` before committing.
5. **Not modify completed modules** without explicit justification.
6. **Update CONTINUE_PROMPT.md** with the next module start instructions.

---

## 8. Pull Request Guidelines

Before opening a PR:
- [ ] All tests pass: `python manage.py test`
- [ ] No system check issues: `python manage.py check`
- [ ] Code follows the style guide
- [ ] New functionality is tested
- [ ] Documentation is updated
- [ ] Commit messages are descriptive

PR description must include:
- Summary of changes
- Module number and name
- Test results (how many pass)
- Any breaking changes or migration notes

---

## Questions?

Open an issue on GitHub or review the documentation in `ARCHITECTURE.md`.
