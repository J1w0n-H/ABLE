.PHONY: help install install-dev test lint format clean run-example docker-clean

help:
	@echo "ABLE - Available commands:"
	@echo ""
	@echo "  make install        Install production dependencies"
	@echo "  make install-dev    Install development dependencies"
	@echo "  make test          Run tests"
	@echo "  make lint          Run linters"
	@echo "  make format        Format code"
	@echo "  make clean         Clean build artifacts"
	@echo "  make docker-clean  Clean Docker resources"
	@echo "  make run-example   Run example build"
	@echo ""

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v --cov=build_agent --cov-report=html --cov-report=term

lint:
	flake8 build_agent/ --max-line-length=120 --exclude=build_agent/utils/repo
	mypy build_agent/ --exclude utils/repo

format:
	black build_agent/ --exclude utils/repo
	isort build_agent/ --skip utils/repo

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf build/ dist/ *.egg-info
	rm -rf htmlcov/ .coverage .pytest_cache/

docker-clean:
	docker system prune -f
	docker volume prune -f
	docker rmi $$(docker images --filter "dangling=true" -q) 2>/dev/null || true

run-example:
	python build_agent/main.py ImageMagick/ImageMagick 336f2b8 .

verify:
	@echo "Verifying installation..."
	@python -c "import docker, pexpect, openai; print('✅ All dependencies installed')"
	@docker --version || (echo "❌ Docker not found" && exit 1)
	@echo "✅ Installation verified"

