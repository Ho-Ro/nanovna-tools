#!/bin/sh

# SPDX-License-Identifier: GPL-3.0-or-later
#
# Tool to read and write the configuration and calibration data of NanoVNA[-H|-H4]
# The data is stored on top of flash memory
# Address and size depend on device and FW variant (select below)

########################################################################################
#
# BEGIN OF CONFIG AREA
#
# set either "H4" or "H" for DiSlord's FW
# https://github.com/DiSlord/NanoVNA-D
# or "H_HORO" for Ho-Ro's noSD 8 slot FW modification
# https://github.com/Ho-Ro/NanoVNA-D/tree/NanoVNA-noSD
#
#VARIANT="H4"
VARIANT="H"
#VARIANT="H_HORO"
#
# the USB serial port of NanoVNA (default for Linux)
SERIAL_DEVICE="/dev/ttyACM0"
#
# flash start address (equal for -H and -H4)
FLASH=0x08000000
#
#
# END OF CONFIG AREA
#
########################################################################################

# exit at undefined variables
set -u
# debug output
set -x

# setup filename, flash address and config size
if [ "$VARIANT" = "H4" ]; then
    PROP_MAX=7
    DEVICE="NanoVNA-H4_${PROP_MAX}_slots"
    FLASH_SIZE=0x40000
    CONF_SIZE=0x800
    PROP_SIZE=0x4000
elif [ "$VARIANT" = "H" ]; then
    PROP_MAX=5
    DEVICE="NanoVNA-H_${PROP_MAX}_slots"
    FLASH_SIZE=0x20000
    CONF_SIZE=0x800
    PROP_SIZE=0x1800
elif [ "$VARIANT" = "H_HORO" ]; then
    PROP_MAX=8
    DEVICE="NanoVNA-H_${PROP_MAX}_slots"
    FLASH_SIZE=0x20000
    CONF_SIZE=0x800
    PROP_SIZE=0x1800
else
    echo VARIANT must be one of "H4", "H", or "H_HORO"
    exit
fi

# calculate size and address of config
CONFIG_SIZE=$(( $CONF_SIZE + $PROP_MAX * $PROP_SIZE ))
CONFIG_START=$(( $FLASH + $FLASH_SIZE - $CONFIG_SIZE ))

# format as hex for better human readability in debug etc.
START=$( printf "0x%08X" $CONFIG_START )

# how are we called (i.e. shall we read or write)
CMD_NAME="$(basename $0)"
if [ "$#" -lt 1 ]; then # no command given
    CMD="NONE"
else
    CMD="$1"
fi


# prepare the cmd line, --device VID:PID, --alt (@Internal Flash)
DFU_UTIL="dfu-util --device 0483:df11 --alt 0 --dfuse-address $START"

if [ "$CMD" = "SAVE" ]; then # read config block from device
    if [ "$#" -lt 2 ]; then # no filename given, create unique name
    NAME="${DEVICE}_config_$(date +%Y%m%d_%H%M%S).bin"
    else # use 1st argument as file name
        NAME="$2"
    fi
    # if the device is in UART mode then switch to DFU mode
    if [ -c "$SERIAL_DEVICE" ]; then
        printf "\rreset dfu\r" > "$SERIAL_DEVICE"
        sleep 2
    fi
    EXECUTE="$DFU_UTIL --upload $NAME"
    #echo $EXECUTE
    $EXECUTE
elif [ "$CMD" = "RESTORE" ]; then
    if [ "$#" -lt 2 ]; then # no filename given, exit
        echo "usage: $CMD_NAME RESTORE <CONFIG_FILE>"
        exit
    fi
    # is this regular file readable?
    if [ ! -f "$2" -o ! -r "$2" ]; then
        echo "$CMD_NAME: cannot read $2"
        exit
    fi
    # does it have the correct size?
    FILESIZE=$(wc -c "$2" | cut -d" " -f1)
    if [ "$FILESIZE" -ne "$CONFIG_SIZE" ]; then
        echo "$CMD_NAME: wrong config file size ${FILESIZE}, expected ${CONFIG_SIZE}"
        exit
    fi
    # is this the correct config content (start with magic "RNOC" or "UNOC")
    RNOC=434f4e52
    UNOC=434f4e55
    # get hex string of 1st 4 bytes
    MAGIC=$(od -N4 -An -tx4 "$2" | tr A-F a-f | tr -d " ")
    if [ $MAGIC != $RNOC -a $MAGIC != $UNOC ]; then
        echo "$CMD_NAME: no config file"
        exit
    fi
    # if the device is in UART mode then switch to DFU mode
    if [ -c "$SERIAL_DEVICE" ]; then
        printf "\rreset dfu\r" > "$SERIAL_DEVICE"
        sleep 2
    fi
    EXECUTE="$DFU_UTIL --download $2"
    #echo $EXECUTE
    $EXECUTE
else
    echo usage:
    echo $CMD_NAME SAVE [CONFIG_FILE]
    echo or
    echo $CMD_NAME RESTORE CONFIG_FILE
    exit
fi
