PY ?= python

.PHONY: film validate smoke script narration keyframes shots music radio_cut assemble costs

# The whole pipeline, one command. Re-runs regenerate only what changed in storyboard.json.
film:
	$(PY) -m pipeline.film --keep-going

validate:
	$(PY) -m pipeline.validate

smoke:
	$(PY) -m pipeline.smoke_test

script:
	$(PY) -m pipeline.script

narration:
	$(PY) -m pipeline.narration

keyframes:
	$(PY) -m pipeline.keyframes

shots:
	$(PY) -m pipeline.shots

music:
	$(PY) -m pipeline.music

radio_cut:
	$(PY) -m pipeline.radio_cut

assemble:
	$(PY) -m pipeline.assemble

costs:
	$(PY) -m pipeline.costs
