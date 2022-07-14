TARGETS = capture_nanovna nanovna

.PHONY: all
all: $(TARGETS)


.PHONY: clean
clean:
	rm $(TARGETS)

.PHONY: format
format:
	clang-format -i --style=file *.c


CFLAGS = -Wall -Wextra
#LDFLAGS = -lpng


capture_nanovna: capture_nanovna.c
	gcc -o $@ $(CFLAGS) $^ -lpng

nanovna: nanovna.c
	gcc -o $@ $(CFLAGS) $^

