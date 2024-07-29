# Toolbox for NanoVNA and tinySA

Small ***NanoVNA*** and ***tinySA*** programs for scripting and automation,
developed on Debian stable (bullseye), but any other Linux/Unix system should work.
Windows and Mac are untested due to lack of HW.
The Python tools can be used without installation on all systems where
a Python interpreter is available,
this is standard for Linux and Mac.
For Windows you have to install Python separately.
Some Python tools also require the modules `cv2`, `matplotlib`, `numpy`, `PIL` and `scikit-rf`,
which should normally already be present on your computer if you are involved
in processing and visualising RF and microwave data with Python.
If you are working under Linux and want to install the tool in your path,
you can create a Debian package by typing `make deb`.
For this you need to install python3-stdeb,
the module for converting Python code and modules to a Debian package.
This package contains also an udev rule that allows user access to the USB serial port of NanoVNA and tinySA.
This rule also creates also a symlink, either `/dev/nanovna` or `/dev/tinysa`
for recent FW versions that announce the device type.

The python commands will detect the serial port automatically,
but can be overruled with the option `-d` if you have more than one device connected.

## Communication and Measurement

### nanotiny_communication_template.py

A very simple template to explore the NanoVNA or tinySA serial communication and build own applications.
When called without options it connects to the 1st detected NanoVNA or tinySA.
The script sends the command `vbat` and displays the result.
It does it step-by-step with commented commands to make own modifications.

```
usage: nanotiny_communication_template.py [-h] [-d DEVICE] [-D] [-v]

options:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        connect to device
  -D, --detect          detect the NanoVNA or tinySA device
  -v, --verbose         be verbose about the communication

```

### nanotiny_command.py

A simple gateway to the *NanoVNA* or *tinySA* shell commands for use in automatisation scripts, e.g.:

    ./nanotiny_command.py help
    Commands: scan scan_bin data frequencies freq sweep power bandwidth saveconfig clearconfig touchcal touchtest pause resume cal save recall trace marker edelay capture vbat tcxo reset smooth vbat_offset transform threshold help info version color

### nanotiny_command.c

The same function, coded in C.

### nanotiny_capture.py

Fast command line tool that captures a screenshot from *NanoVNA* or *tinySA* and stores it as small png:
- Connect via USB serial or serial
- Autodetect the device on USB
- Issue the command 'pause' to freeze the screen
- Issue the command 'capture rle'
- Checks for a valid RLE header
- If yes, fetch and expand a compressed image
- Else fetch 320x240 or 480x320 rgb565 pixels
- Issue the command 'resume' to resume the screen update
- Disconnect from USB serial
- Convert pixels to rgba8888 values and optionally scale
- Finally store the image as png with date_time stamped name (e.g NanoVNA_20210617_153045.png)
- You can provide an output file name (-o NAME.EXT) to store also as BMP, GIF, JPEG, PNG or TIFF.

The program takes less than 1 second to complete.

```
usage: nanotiny_capture.py [-h] [-b BAUDRATE] [-d DEVICE] [-n | --h4 | -t | -u | -p] [-i] [-o OUT] [-r]
                           [-s {1,2,3,4,5,6,7,8,9,10}] [-v]

Capture a screenshot from NanoVNA-H, NanoVNA-H4, tinySA, tinySA Ultra or tinyPFA.
Autodetect the device when connected to USB.
Optional RLE compression if available, especially useful e.g. for slow serial connections.

options:
  -h, --help            show this help message and exit
  -b BAUDRATE, --baudrate BAUDRATE
                        set serial baudrate
  -d DEVICE, --device DEVICE
                        connect to serial device
  -n, --nanovna         use with NanoVNA-H (default)
  --h4, --nanovna-h4    use with NanoVNA-H4
  -t, --tinysa          use with tinySA
  -u, --ultra           use with tinySA Ultra
  -p, --tinypfa         use with tinyPFA
  -i, --invert          invert the colors, e.g. for printing
  -o OUT, --out OUT     write the data into file OUT
  -r, --rle             try rle compression, useful for slow serial connections
  -s {1,2,3,4,5,6,7,8,9,10}, --scale {1,2,3,4,5,6,7,8,9,10}
                        scale image
  -v, --verbose         verbose the communication progress
```

### nanotiny_capture.c

An even faster command line tool that captures a screenshot from *NanoVNA* or *tinySA* and stores it as small png.
It works similar to the python above and is a proof of concept how to communicate over USB serial in c.
Usage: `nanotiny_capture [NANOPORT] [NAME.EXT]` -> Stores screenshot as PNG unless EXT == "ppm".
Opens `/dev/ttyACM0` unless the 1st argument starts with `/dev/`.
PNG format is provided by `libpng` and `libpng-dev`, NetPBM format needs no extra library support.

### nanovna_snp.py

Command line tool to fetch S11, S21 or S11 & S21 parameter from *NanoVNA-H*.
Save as S-parameter (1 port or 2 port) or Z-parameter (1 port) in "touchstone" format (rev 1.1).
Connect via USB serial, issue the command, calculate, and format the response.
Do it as an exercise - step by step - without using tools like scikit-rf.

```
usage: nanovna_snp.py [-h] [-d DEVICE] [-o [FILE]] [-c] [-t TIMEOUT] [-1 | -2 | -z]

Save S parameter from NanoVNA-H in "touchstone" format

optional arguments:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        connect to device
  -o [FILE], --out [FILE]
                        write output to FILE, default = <stdout>
  -c, --comment         add comments to output file (may break some simple tools, e.g.
                        octave's load("-ascii" ...))
  -t TIMEOUT, --timeout TIMEOUT
                        timeout for data transfer (default = 3 s)
  -1, --s1p             store S-parameter for 1-port device (default)
  -2, --s2p             store S-parameter for 2-port device
  -z, --z1p             store Z-parameter for 1-port device
```

The Z-parameter are stored as normalized (R/Z0 + jX/Z0) values, as also mentioned in the comment of the data:

```
! NanoVNA 20230112_105451
! scan 50000 900000000 101 3
! 1-port normalized Z-parameter (R/Z0 + jX/Z0)
# HZ Z RI R 50
     50000     1.042313132     0.000526267
   9049500     1.047180375     0.070234472
  18049000     1.052795732     0.137763222
...
 891000500     0.118583454    -1.276420745
 900000000     0.111755060    -1.256828212
```

### plot_snp.py

Plot a `*.s[12]p` file in touchstone format. Render S11 as smith diagram and S21 (if available) as magnitude and phase into one figure.

```
usage: plot_snp.py [-h] [-x] infile

Plot S11 as smith chart and S22 as dB/phase

positional arguments:
  infile      infile in touchstone format

optional arguments:
  -h, --help  show this help message and exit
  -x, --xkcd  draw the plot in xkcd style :)
```

### check_s11.py

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

### nanovna_remote.py

Remote control for the *NanoVNA* or *tinySA* - mirror the screen to your PC and operate the device with the mouse.
The keys `+` and `-` zoom in and out, `s` takes a screenshot with timestamp, `ESC` quits the program.

```
usage: nanovna_remote.py [-h] [-d DEVICE] [-n | --h4 | -t | --ultra] [-i] [-z {2,3,4}]

Remote control NanoVNA-H or tinySA

optional arguments:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        connect to serial usb device
  -n, --nanovna         use with NanoVNA-H (default)
  --h4                  use with NanoVNA-H4
  -t, --tinysa          use with tinySA
  --ultra               use with tinySA Ultra
  -i, --invert          invert the colors, e.g. for printing of screen shots
  -z {2,3,4}, --zoom {2,3,4}
                        zoom the screen image
```

### nanovna_time.py

Show the RTC time of *NanoVNA-H* or *NanoVNA-H4* and sync it with the system time or calculate time deviation

```
usage: nanovna_time.py [-h] [-d DEVICE] [-s] [-p]

Show and sync the RTC time of NanoVNA-H or NanoVNA-H4

options:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        connect to device
  -s, --sync            sync the NanoVNA time to the system time
  -p, --ppm             calculate ppm deviation since last sync

```

### tinysa_scanraw.py

Get a CSV formatted scan from the *tinySA*

```
usage: tinysa_scanraw.py [-h] [-d DEVICE] [-s START] [-e END] [-p POINTS] [-r RBW] [-c] [-v]

Get a raw scan from tinySA, formatted as csv (freq, power)

optional arguments:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        connect to serial device
  -s START, --start START
                        start frequency, default = 0 Hz
  -e END, --end END     end frequency, default = 350000000 Hz
  -p POINTS, --points POINTS
                        Number of sweep points, default = 101
  -r RBW, --rbw RBW     resolution bandwidth / Hz, default = 0 (calculate RBW from scan steps)
  -c, --comma           use comma as decimal separator
  -v, --verbose         provide info about scan parameter and timing
```


## Low Level Tools (be careful)

### nanovna_config.sh

Tool to read or write the configuration and calibration data of NanoVNA[-H|-H4]
This is stored on top of flash memory, address and size depend on device and FW variant
(select your device in the top lines of script)

The script saves one complete configuration block from the device.
On restore the size of the config file is checked against the flash config size.
Also the *MAGIC* value at file start will be checked, either `TNOC` for calibration
or `VNOC` for configuration - this is 'CONT' or 'CONV' reverse :)
This check helps a little bit to avoid the usage of wrong data.

```
usage:
nanovna_config.sh SAVE [FILENAME]
  if FILENAME is omitted an unique name is created, e.g.:
  NanoVNA-H_5_slots_config_DATE_TIME.bin
or:
nanovna_config.sh RESTORE FILENAME
```

### nanovna_config_split.py

Tool to process the config data block of a NanoVNA-H retrieved with `nanovna_config.sh`
and save the data as individual files for each calibration slot and global config data
or transfer the config file into the opposite format (5 slot format <-> 7 slot format).

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
                            0       0x08015000
                            1       0x08016800
0       0x08018000          2       0x08018000
1       0x08019800          3       0x08019800
2       0x0801B000          4       0x0801B000
3       0x0801C800          5       0x0801C800
4       0x0801E000          6       0x0801E000
config  0x0801F800          config  0x0801F800
```

#### Reason:
In my FW modification, I omitted the SD functions because my NanoVNA-H HW V3.4 does not have an SD card slot.
The increased free flash memory can be used to store 7 calibration slots instead of 5.

