default:
	python check.py

install:
	pip install -r requirements.txt

clean:
	python reset.py

build:
	python sync.py

work:
	python work.py

all:
	pip install -r requirements.txt
	python reset.py
	python sync.py
	python check.py