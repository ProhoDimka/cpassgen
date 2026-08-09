###########################################################
# Секция базовых команд, общих между всеми микросервисами #
###########################################################

init:
	$(MAKE) init_project

init_project:
	pip install --upgrade pip
	poetry install --without=test

# tests, formatters, linters etc.
fmt:
	isort app
	black app

fmt_check:
	isort --check app
	black --version
	black --check app

lint:
	flake8 -v app

sast:
	bandit -r ./ -c pyproject.toml

pkg_audit:
	pip-audit --skip-editable

test:
	pytest --cov=app
