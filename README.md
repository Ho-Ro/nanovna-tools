# Toolbox for NanoVNA

Small NanoVNA program(s) for scripting and automatisation, developed on Debian stable (bullseye),
but every other Linux/Unix system should work too. Windows and Mac are untested due to missing HW.
To build a debian package just type `make deb`. You need to install python3-stdeb,
the Python to Debian source package conversion plugins for distutils.
Some python tools require also the modules `matplotlib` and `scikit-rf`,
which should normally already be on your computer if you are involved
in RF and microwave data processing and visualisation.

## nanovna_command.py

A simple gateway to the NanoVNA shell commands for use in automatisation scripts, e.g.:

    ./nanovna_command.py help
    Commands: scan scan_bin data frequencies freq sweep power bandwidth saveconfig clearconfig touchcal touchtest pause resume cal save recall trace marker edelay capture vbat tcxo reset smooth vbat_offset transform threshold help info version color

## nanovna_command.c

The same function, coded in C.

## nanovna_capture.py

Fast command line tool that captures a screenshot from NanoVNA and stores it as small png:
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

An even faster command line tool that captures a screenshot from NanoVNA and stores it as small png.
It works similar to the python above and is a proof of concept how to communicate over USB serial in c.
Usage: "nanovna_capture NAME.EXT" -> Stores screenshot as PNG unless EXT == "ppm"
PNG format is provided by `libpng` and `libpng-dev`, NetPBM format needs no extra library support.

## nanovna_snp.py

Command line tool to fetch S11, S21 or S11 & S21 parameter from NanoVNA-H.
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
