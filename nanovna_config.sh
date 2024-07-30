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
# or "H_noSD" for Ho-Ro's noSD 8 slot FW modification
# https://github.com/Ho-Ro/NanoVNA-D/tree/NanoVNA-noSD
#
#VARIANT="H4"
#VARIANT="H"
VARIANT="H_noSD"
#
# the USB serial port of NanoVNA (default for Linux)
SERIAL_DEVICE="/dev/nanovna"
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
#set -x

# how are we called
CMD_NAME="$(basename $0)"
if [ "$#" -lt 1 ]; then # no command given
    CMD="NONE"
else
    CMD="$1"
fi


if [ "$CMD" = "SAVE_noSD" ]; then
    CMD=SAVE
    VARIANT="H_noSD"
elif [ "$CMD" = "SAVE_H" ]; then
    CMD=SAVE
    VARIANT="H"
elif [ "$CMD" = "SAVE_H4" ]; then
    CMD=SAVE
    VARIANT="H4"
elif [ "$CMD" = "RESTORE_noSD" ]; then
    CMD=RESTORE
    VARIANT="H_noSD"
elif [ "$CMD" = "RESTORE_H" ]; then
    CMD=RESTORE
    VARIANT="H"
elif [ "$CMD" = "RESTORE_H4" ]; then
    CMD=RESTORE
    VARIANT="H4"
fi


# setup filename, flash address and config size
if [ "$VARIANT" = "H4" ]; then
    PROP_MAX=7
    DEVICE="NanoVNA-H4_${PROP_MAX}_slots"
    FLASH_SIZE=0x40000
    CONF_SIZE=0x800
    PROP_SIZE=0x4000
    MAGIC0=434F4E54
    MAGICC=434F4E56
elif [ "$VARIANT" = "H" ]; then
    PROP_MAX=5
    DEVICE="NanoVNA-${VARIANT}_${PROP_MAX}_slots"
    FLASH_SIZE=0x20000
    CONF_SIZE=0x800
    PROP_SIZE=0x1800
    MAGIC0=434F4E54
    MAGICC=434F4E56
elif [ "$VARIANT" = "H_noSD" ]; then
    PROP_MAX=8
    DEVICE="NanoVNA-${VARIANT}_${PROP_MAX}_slots"
    FLASH_SIZE=0x20000
    CONF_SIZE=0x800
    PROP_SIZE=0x1800
    MAGIC0=434F4E54
    MAGICC=434F4E56
else
    echo VARIANT must be one of "H4", "H", or "H_noSD"
    exit
fi


# calculate size and address of config
# format some as hex for better human readability in debug etc.
SLOTS_SIZE=$(printf "0x%08X\n" $(($PROP_MAX * $PROP_SIZE)))
CONFIG_ADDR=$(printf "0x%08X\n" $(($FLASH + $FLASH_SIZE - $SLOTS_SIZE - $CONF_SIZE)))
SLOTS_CFG_SIZE=$(( $SLOTS_SIZE + $CONF_SIZE ))

echo "CONFIG_ADDR:    $CONFIG_ADDR"
echo "SLOTS_SIZE:     $SLOTS_SIZE"
echo "SLOTS_CFG_SIZE: $(printf "0x%08X" $SLOTS_CFG_SIZE) ($SLOTS_CFG_SIZE)"


# prepare the cmd line, --device VID:PID, --alt (@Internal Flash)
DFU_UTIL="dfu-util --device 0483:df11 --alt 0 --dfuse-address $CONFIG_ADDR"

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
    echo $EXECUTE
    $EXECUTE
    # is this the correct config content (start with magic "TNOC" or "VNOC")
    # get hex string of 1st 4 bytes
    XXXX=$(od --traditional -N4 -An -tx4 "$NAME" | tr a-f A-F | tr -d " ")
    echo Slot 0 magic: $XXXX
    if [ $XXXX != $MAGIC0 ]; then
        echo "\n$NAME: no correct config file"
        exit
    fi
    XXXX=$(od --traditional -N4 -An -tx4 "$NAME" +$SLOTS_SIZE | tr a-f A-F | tr -d " ")
    echo Config magic: $XXXX
    if [ $XXXX != $MAGICC ]; then
        echo "\n$NAME: no correct config file"
        exit
    fi
    echo Saved to $NAME

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
    if [ "$FILESIZE" -ne "$SLOTS_CFG_SIZE" ]; then
        echo "$CMD_NAME: wrong config file size ${FILESIZE}, expected ${SLOTS_CFG_SIZE} (${PROP_MAX} slots)"
        exit
    fi
    # is this the correct config content (start with magic "TNOC" or "VNOC")
    # get hex string of 1st 4 bytes
    XXXX=$(od --traditional -N4 -An -tx4 "$2" | tr a-f A-F | tr -d " ")
    echo Slot 0 magic: $XXXX
    if [ $XXXX != $MAGIC0 ]; then
        echo "\n$NAME: no correct config file"
        exit
    fi
    XXXX=$(od --traditional -N4 -An -tx4 "$2" +$SLOTS_SIZE | tr a-f A-F | tr -d " ")
    echo Config magic: $XXXX
    if [ $XXXX != $MAGICC ]; then
        echo "\n$NAME: no correct config file"
        exit
    fi
    # if the device is in UART mode then switch to DFU mode
    if [ -c "$SERIAL_DEVICE" ]; then
        printf "\rreset dfu\r" > "$SERIAL_DEVICE"
        sleep 1
    fi
    EXECUTE="$DFU_UTIL --download $2"
    echo $EXECUTE
    $EXECUTE

else
    echo Save / restore the NanoVNA calibration and configuration data to / from file
    echo usage:
    echo "  $CMD_NAME SAVE [CONFIG_FILE]"
    echo or
    echo "  $CMD_NAME RESTORE CONFIG_FILE"
    exit
fi

echo Ready, now power-cycle the NanoVNA
