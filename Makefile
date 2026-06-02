.PHONY: build test package clean

test:
	.venv/bin/pytest tests/ -v

build:
	cd build && ../.venv/bin/pyinstaller dein_zeugs.spec --distpath ../dist --workpath ../build/work

package: build
	codesign --force --deep --sign - dist/dein-zeugs

release: package
	mkdir -p dist/release
	cp dist/dein-zeugs dist/release/dein-zeugs
	cp installer/dein-zeugs.command dist/release/dein-zeugs.command
	chmod +x dist/release/dein-zeugs dist/release/dein-zeugs.command
	cd dist && zip -r dein-zeugs-release.zip release/
	@echo "Release archive: dist/dein-zeugs-release.zip"

clean:
	rm -rf dist/ build/work/ build/__pycache__/
