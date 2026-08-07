.PHONY: install configure shortcut services doctor test clean

install:
	./scripts/install

configure:
	./scripts/configure

shortcut:
	./scripts/copy-shortcut

services:
	./scripts/install-services

doctor:
	@$(HOME)/.local/bin/iphone doctor

test:
	PYTHONPATH="$(CURDIR)/src" python3 -m unittest discover -s tests -v
	python3 -m compileall -q src tests scripts
	python3 scripts/validate-shortcut.py shortcut/actions.template.plist

clean:
	rm -rf build
