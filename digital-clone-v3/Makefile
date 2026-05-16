.PHONY: install run test clean docker

install:
	pip install -r requirements.txt
	playwright install chromium

run:
	python main.py

test:
	pytest tests/ -v

clean:
	rm -rf __pycache__ .pytest_cache

docker:
	docker-compose up --build
