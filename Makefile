.PHONY: test bridge verify export
test:
	python3 -m unittest discover -s tests -v
bridge:
	python3 scripts/repository_bridge.py prepare
verify:
	python3 scripts/repository_bridge.py verify
export:
	python3 scripts/repository_bridge.py export
