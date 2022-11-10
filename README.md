# Toolbox for NanoVNA and tinySA

Small ***NanoVNA*** and ***tinySA*** program(s) for scripting and automatisation, developed on Debian stable (bullseye),
but every other Linux/Unix system should work too. Windows and Mac are untested due to missing HW.
To build a debian package just type `make deb`. You need to install python3-stdeb,
the Python to Debian source package conversion plugins for distutils.
Some python tools require also the modules `matplotlib` and `scikit-rf`,
which should normally already be on your computer if you are involved
in RF and microwave data processing and visualisation.

## nanovna_command.py

A simple gateway to the *NanoVNA* or *tinySA* shell commands for use in automatisation scripts, e.g.:

    ./nanovna_command.py help
    Commands: scan scan_bin data frequencies freq sweep power bandwidth saveconfig clearconfig touchcal touchtest pause resume cal save recall trace marker edelay capture vbat tcxo reset smooth vbat_offset transform threshold help info version color

## nanovna_command.c

The same function, coded in C.

## nanovna_capture.py

Fast command line tool that captures a screenshot from *NanoVNA* or *tinySA* and stores it as small png:
- Connect via USB serial
- Issue the command 'pause' to freeze the screen
- Issue the command 'capture'
- Fetch 320x240 rgb565 pixels
- Issue the command 'resume' to resume the screen update
- Disconnect from USB serial
- Convert pixels to rgb888 values
- Finally store the image as png with date_time stamped name (e.g NanoVNA_20210617_153045.png)
- You can provide an output file name (-o NAME.EXT) to store also as BMP, GIF, JPEG, PNG or TIFF.

The program takes less than 1 second to complete.

```
usage: nanovna_capture.py [-h] [-d DEVICE] [-o OUT]

optional arguments:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        connect to device
  -o OUT, --out OUT     write the data into file OUT
```

## nanovna_capture.c

An even faster command line tool that captures a screenshot from *NanoVNA* or *tinySA* and stores it as small png.
It works similar to the python above and is a proof of concept how to communicate over USB serial in c.
Usage: "nanovna_capture NAME.EXT" -> Stores screenshot as PNG unless EXT == "ppm"
PNG format is provided by `libpng` and `libpng-dev`, NetPBM format needs no extra library support.

## nanovna_snp.py

Command line tool to fetch S11, S21 or S11 & S21 parameter from *NanoVNA-H*.
Save as S-parameter (1 port or 2 port) or Z-parameter (1 port) in "touchstone" format (rev 1.1).
Connect via USB serial, issue the command, calculate, and format the response.
Do it as an exercise - step by step - without using tools like scikit-rf.

```
usage: nanovna_snp.py [-h] [-d DEVICE] [-o [FILE]] [-1 | -2 | -z]

optional arguments:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        connect to device
  -o [FILE], --out [FILE]
                        write output to FILE, default = <stdout>
  -1, --s1p             store S-parameter for 1-port device (default)
  -2, --s2p             store S-parameter for 2-port device
  -z, --z1p             store Z-parameter for 1-port device
```

## plot_snp.py

Plot a `*.s[12]p` file in touchstone format. Render S11 as smith diagram and S21 (if available) as magnitude and phase into one figure.

```
usage: plot_snp.py [-h] [-x] infile

positional arguments:
  infile      infile in touchstone format

optional arguments:
  -h, --help  show this help message and exit
  -x, --xkcd  draw the plot in xkcd style :)
```

## check_s11.py

Check S parameter files for values with |S11| > 1 that may indicate a calibration issue.

```
usage: check_s11.py [-h] [-i INFILE | -r] [-v]

Check all touchstone files in current directory for values with |S11| > 1

optional arguments:
  -h, --help            show this help message and exit
  -i INFILE, --infile INFILE
                        check only the touchstone file INFILE
  -r, --recursive       check also all touchstone files in subdirectories
  -v, --verbose         display all checked files, more mismatch details

```

## tinySA_remote.py

Remote control for the *tinySA* - mirror the screen to your PC and operate the device with the mouse.
The keys `+` and `-` zoom in and out, `s` takes a screenshot with timestamp, `ESC` quits the program.

Work in progress - the mouse click is not fully working, currently no NanoVNA support.

```
usage: tinySA_remote.py [-h] [-d DEVICE] [-t | -n] [-z {2,3,4}]

optional arguments:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        connect to serial usb device
  -t, --tinySA          use with tinySA (default)
  -n, --NanoVNA         use with NanoVNA (not yet implemented)
  -z {2,3,4}, --zoom {2,3,4}
                        zoom the screen image
```

## nanovna_config.sh

Tool to read or write the configuration and calibration data of NanoVNA[-H|-H4]
This is stored on top of flash memory, address and size depend on device and FW variant
(select your device in the top lines of script)

The script saves one complete configuration block from the device.
On restore the size of the config file is checked against the flash config size.
Also the *MAGIC* value at file start will be checked, either `RNOC` for calibration
or `UNOC` for configuration - this is 'CONR' or 'CONU' reverse :)
This check helps a little bit to avoid the usage of wrong data.

```
usage:
nanovna_config.sh SAVE [FILENAME]
  if FILENAME is omitted an unique name is created, e.g.:
  NanoVNA-H_5_slots_config_DATE_TIME.bin
or:
nanovna_config.sh RESTORE FILENAME
```

## nanovna_config_split.py

Tool to process the config data block of a NanoVNA-H retrieved with `nanovna_config.sh`
and save the data as individual files for each calibration slot and global config data
or transfer the config file into the opposite format (5 slot format <-> 8 slot format).

```
usage: nanovna_config_split.py [-h] [-p PREFIX] [-s] [-t] infile

positional arguments:
  infile                config file

optional arguments:
  -h, --help            show this help message and exit
  -p PREFIX, --prefix PREFIX
                        prefix for output files, default: NV-H
  -s, --split           split config file into individual slot files
  -t, --transfer        transfer 5 slot format <-> 8 slot format
```

The individual slot files can be downloaded to the NanoVNA-H with the program "dfu-util"
`dfu-util --device 0483:df11 --alt 0 --dfuse-address ADDR --download SLOTFILE`

ADDR depends on the FW, either [DiSlord´s originalFW](https://github.com/DiSlord/NanoVNA-D)
or [FW modified by Ho-Ro](https://github.com/Ho-Ro/NanoVNA-D/tree/NanoVNA-noSD)

```
DiSlord´s originalFW        FW modified by Ho-Ro
====================        ====================
SLOT    ADDR                SLOT    ADDR
config  0x08018000          config  0x0801F800
0       0x08018800          0       0x0801E000
1       0x0801A000          1       0x0801C800
2       0x0801B800          2       0x0801B000
3       0x0801D000          3       0x08019800
4       0x0801E800          4       0x08018000
                            5       0x08016800
                            6       0x08015000
                            7       0x08013800
```

Reason:
My FW modification omitted the SD functions, because my NanoVNA-H device has no SD card slot.
The increased free flash memory can be used to store 8 calibration slots instead of 5.
I also reverted the locations of the data and put config on top of flash and the slots
below in descending order. This has the advantage that with increased program size in
future versions the highest slot(s) can be removed and config is untouched, while in
original FW the config date and the low slot(s) will be overwritten 1st.

