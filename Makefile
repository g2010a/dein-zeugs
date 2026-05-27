.PHONY: build test package clean

test:
	.venv/bin/pytest tests/ -v

build:
	cd build && ../.venv/bin/pyinstaller dein_zeugs.spec --distpath ../dist --workpath ../build/work

package: build
	codesign --force --deep --sign - dist/dein-zeugs
	@echo "Binary at dist/dein-zeugs — ready to copy to /usr/local/bin/"

clean:
	rm -rf dist/ build/work/ build/__pycache__/
