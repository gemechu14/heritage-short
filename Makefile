PY ?= python

validate:
	$(PY) -m pipeline.validate

smoke:
	$(PY) -m pipeline.smoke_test
