deb:
	mkdir -p hilink-tray-4.0/usr/lib/python2.7/dist-packages hilink-tray-4.0/usr/bin
	cp -rf hilink hilink-tray-4.0/usr/lib/python2.7/dist-packages
	cp -f hilink-tray.py hilink-tray-4.0/usr/bin/hilink-tray
	dpkg --build hilink-tray-4.0 hilink-tray-4.0_all.deb

pacman:
	makepkg -sr

windows:
	wine C:/Python27/Scripts/pyinstaller -w hilink-tray.py
	mkdir -p dist/hilink-tray/phonon_backend
	cp -rf ~/.wine/drive_c/Python27/Lib/site-packages/PySide/plugins/phonon_backend/phonon_ds94.dll dist/hilink-tray/phonon_backend

windows-dbg:
	wine C:/Python27/Scripts/pyinstaller hilink-tray.py
	mkdir -p dist/hilink-tray/phonon_backend
	cp -rf ~/.wine/drive_c/Python27/Lib/site-packages/PySide/plugins/phonon_backend/phonon_ds94.dll dist/hilink-tray/phonon_backend

install:
	install -D hilink /usr/lib/python2.7/dist-packages/
	install -D hilink-tray.py /usr/bin/hilink-tray

uninstall:
	rm -rf /usr/bin/hilink-tray /usr/lib/python2.7/dist-packages/hilink

deb-clean:
	rm -rf hilink-tray-4.0/usr

pacman-clean:
	rm -rf hilink-tray pkg src

windows-clean:
	rm -rf build *.spec
