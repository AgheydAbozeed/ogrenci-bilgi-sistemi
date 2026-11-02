DB ?= obs
VENV_PY ?= $(HOME)/.obs_venv/bin/python

.PHONY: test sql-test gui

sql-test:
	psql -d $(DB) -f tests/001_testler.sql
	psql -d $(DB) -f tests/002_mezuniyet_testleri.sql
	psql -d $(DB) -f tests/004_api_testleri.sql
	psql -d $(DB) -f tests/005_yetki_testleri.sql

test: sql-test
	$(VENV_PY) tests/006_eszamanlilik_testi.py

gui:
	$(VENV_PY) -m app.main
