# Build against the system libical (Debian/Ubuntu: libical-dev).
#   make
# Build against a libical you compiled yourself, e.g. master:
#   make LIBICAL_PREFIX=/path/to/install
# and run with LD_LIBRARY_PATH=$(LIBICAL_PREFIX)/lib.
CC      ?= cc
CFLAGS  ?= -O2 -Wall -Wextra
LIBICAL_PREFIX ?=
ifneq ($(LIBICAL_PREFIX),)
CFLAGS  += -I$(LIBICAL_PREFIX)/include
LDFLAGS += -L$(LIBICAL_PREFIX)/lib
endif

libical_adapter: libical_adapter.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS) -lical

clean:
	rm -f libical_adapter
.PHONY: clean
