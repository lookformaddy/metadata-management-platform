.PHONY: test demo lint

test:
	pytest -q

demo:
	python demo.py

lint:
	python -m compileall -q src demo.py
