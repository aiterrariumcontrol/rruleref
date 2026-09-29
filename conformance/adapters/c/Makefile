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

# A SECOND binary, always against the system library, under its own name so it
# can sit beside a master build instead of replacing it. Finding 115 needs both
# at once: LD_LIBRARY_PATH cannot turn one binary into the other, because
# libical 3 and 4 differ in API and the source compiles to different calls.
libical_adapter3: libical_adapter.c
	$(CC) -O2 -Wall -Wextra -o $@ $< -lical

clean:
	rm -f libical_adapter libical_adapter3
.PHONY: clean
