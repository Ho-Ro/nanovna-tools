TARGETS = nanotiny_command nanotiny_capture

.PHONY: all
all: $(TARGETS)


.PHONY: strip
strip:
	strip $(TARGETS)


.PHONY: format
format:
	clang-format -i --style=file *.c


CFLAGS = -Wall -Wextra
#LDFLAGS = -lpng


nanotiny_command: nanotiny_command.c
	gcc -o $@ $(CFLAGS) $^

nanotiny_capture: nanotiny_capture.c
	gcc -o $@ $(CFLAGS) $^ -lpng


# create a python source package
.PHONY:	sdist
sdist:
	python setup.py --command-packages=stdeb.command sdist


# create a debian source package
.PHONY:	dsc
dsc:
	python setup.py --command-packages=stdeb.command sdist_dsc


# create a debian binary package
.PHONY:	deb
deb:	distclean all strip
	git log --pretty="%cs: %s [%h]" > Changelog
	python setup.py --command-packages=stdeb.command bdist_deb
	ln `ls deb_dist/nanovna-tools*_all.deb | tail -1` .


# install the latest debian package
.PHONY:	debinstall
debinstall:
	sudo dpkg -i `ls deb_dist/nanovna-tools*_all.deb | tail -1`


# prepare a clean build
.PHONY:	clean
clean:
	-rm $(TARGETS)
	-python setup.py clean


# removes all build artefacts
.PHONY:	distclean
distclean: clean
	-rm -rf *~ .*~ deb_dist dist *.tar.gz *.deb *.egg* build tmp

