# Toolbox for NanoVNA
Small NanoVNA program(s) for scripting and automatisation

## capture_nanovna.py

Fast command line tool that captures a screen shot from NanoVNA and stores it as small png:
- Connect via USB serial
- Issue the command 'pause' to freeze the screen
- Issue the command 'capture'
- Fetch 320x240 rgb565 pixels
- Issue the command 'resume' to resume the screen update
- Disconnect from USB serial
- Convert pixels to rgb888 values
- Finally store them as png image with time stamped name (e.g NanoVNA_20210617_153045.png)

The program takes less than 1 second to complete.
