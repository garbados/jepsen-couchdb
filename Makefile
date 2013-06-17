install:
	pip install -r requirements.txt

clean:
	python reset.py

build:
	python sync.py

rebuild:
	python reset.py
	python sync.py