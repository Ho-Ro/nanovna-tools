# Toolbox for NanoVNA
Small NanoVNA program(s) for scripting and automatisation

## capture_nanovna.py

Fast command line tool that captures a screenshot from NanoVNA and stores it as small png:
- Connect via USB serial
- Issue the command 'pause' to freeze the screen
- Issue the command 'capture'
- Fetch 320x240 rgb565 pixels
- Issue the command 'resume' to resume the screen update
- Disconnect from USB serial
- Convert pixels to rgb888 values
- Finally store the image as png with date_time stamped name (e.g NanoVNA_20210617_153045.png)

The program takes less than 1 second to complete.

## capture_nanovna.c

An even faster command line tool that captures a screenshot from NanoVNA and stores it as small png.
It works similar to the python above and is a proof of concept how to communicate over USB serial in c.

## nanovna.c

A simple gateway to the NanoVNA shell commands for use in automatisation scripts, e.g.:
````
 ./nanovna help
help
Commands: scan scan_bin data frequencies freq sweep power bandwidth saveconfig clearconfig touchcal touchtest pause resume cal save recall trace marker edelay capture vbat tcxo reset smooth vbat_offset transform threshold help info version color
ch>

./nanovna sweep
sweep
50000 900000000 101
ch>
````
