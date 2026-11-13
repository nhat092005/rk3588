# Board access and locations, defined once for every Makefile of the meta-repo.
# Override on the CLI, for example: make sysroot BOARD=user@host
BOARD     ?= minhnhat@192.168.137.49
BOARD_DIR ?= rk3588-board
SYSROOT   ?= $(HOME)/sysroots/orangepi5
