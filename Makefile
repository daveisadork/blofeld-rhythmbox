DESTDIR=
SUBDIR=/usr/lib/rhythmbox/plugins/blofeld/

all:
clean:
	- rm *.pyc

install:
	install -d $(DESTDIR)$(SUBDIR)
	install -m 644 *.py $(DESTDIR)$(SUBDIR)
	install -m 644 blofeld.rb-plugin $(DESTDIR)$(SUBDIR)
