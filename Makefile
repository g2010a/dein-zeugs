.PHONY: build test package clean

test:
	.venv/bin/pytest tests/ -v

build:
	cd build && ../.venv/bin/pyinstaller podq.spec --distpath ../dist --workpath ../build/work

package: build
	codesign --force --deep --sign - dist/podq
	@echo "Binary at dist/podq — ready to copy to /usr/local/bin/"

clean:
	rm -rf dist/ build/work/ build/__pycache__/
