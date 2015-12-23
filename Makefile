test: test-sqlite test-postgres test-flake8

test-sqlite: install-dependencies install-wkhtmltopdf
	coverage run setup.py test
	coverage report -m --fail-under 90

test-postgres: install-dependencies install-wkhtmltopdf
	python setup.py test_on_postgres

test-flake8:
	pip install flake8
	flake8 .

install-dependencies:
	CFLAGS=-O0 pip install lxml
	pip install -r dev_requirements.txt

install-wkhtmltopdf:
	sudo apt-get update
	sudo apt-get install -y build-essential xorg libssl-dev libxrender-dev
	wget http://wkhtmltopdf.googlecode.com/files/wkhtmltopdf-0.11.0_rc1-static-amd64.tar.bz2
	tar xvjf wkhtmltopdf-0.11.0_rc1-static-amd64.tar.bz2
	sudo chown root:root wkhtmltopdf-amd64
	sudo mv wkhtmltopdf-amd64 /usr/bin/wkhtmltopdf
