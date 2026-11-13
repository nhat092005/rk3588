# Board access and locations, defined once for every Makefile of the meta-repo.
# Override on the CLI, for example: make sysroot BOARD=user@host
BOARD     ?= minhnhat@192.168.137.49
BOARD_DIR ?= rk3588-board
# adb address of the board for RKNN-Toolkit2 tier 1 from the PC (adbd on TCP 5555, deploy/sh/start_rknn_server.sh)
DEVICE    ?= $(lastword $(subst @, ,$(BOARD))):5555
SYSROOT   ?= $(HOME)/sysroots/orangepi5
