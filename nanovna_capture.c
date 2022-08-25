// SPDX-License-Identifier: GPL-3.0-or-later


// Command line tool to capture a screen shot from NanoVNA
// connect via USB serial, issue the command 'capture'
// and fetch 320x240 rgb565 pixel.
// These pixels are converted to rgb888 values
// that are stored as an image (e.g. png)

#include <errno.h>
#include <fcntl.h>
#include <png.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>


const char *nano_port = "/dev/ttyACM0";

const int nano_width = 320;
const int nano_height = 240;

static int nano_fd = 0;


static int nano_open() {
    nano_fd = open( nano_port, O_RDWR | O_NOCTTY | O_SYNC );
    if ( nano_fd < 0 ) {
        fprintf( stderr, "Error opening %s: %s\n", nano_port, strerror( errno ) );
        return -1;
    }
    return nano_fd;
}

static int nano_close() { return close( nano_fd ); }


static int nano_set_interface_attribs( int speed ) {
    struct termios tty;

    if ( tcgetattr( nano_fd, &tty ) < 0 ) {
        fprintf( stderr, "Error from tcgetattr: %s\n", strerror( errno ) );
        return -1;
    }

    cfsetospeed( &tty, (speed_t)speed );
    cfsetispeed( &tty, (speed_t)speed );

    tty.c_cflag |= ( CLOCAL | CREAD ); /* ignore modem controls */
    tty.c_cflag &= ~CSIZE;
    tty.c_cflag |= CS8;      /* 8-bit characters */
    tty.c_cflag &= ~PARENB;  /* no parity bit */
    tty.c_cflag &= ~CSTOPB;  /* only need 1 stop bit */
    tty.c_cflag &= ~CRTSCTS; /* no hardware flowcontrol */

    /* setup for non-canonical mode */
    tty.c_iflag &= ~( IGNBRK | BRKINT | PARMRK | ISTRIP | INLCR | IGNCR | ICRNL | IXON );
    tty.c_lflag &= ~( ECHO | ECHONL | ICANON | ISIG | IEXTEN );
    tty.c_oflag &= ~OPOST;

    /* fetch bytes as they become available */
    tty.c_cc[ VMIN ] = 1;
    tty.c_cc[ VTIME ] = 1;

    if ( tcsetattr( nano_fd, TCSANOW, &tty ) != 0 ) {
        fprintf( stderr, "Error from tcsetattr: %s\n", strerror( errno ) );
        return -1;
    }
    return 0;
}


// read from input until pattern was received
static int nano_wait_for( const char *pattern ) {
    int match = 0;
    int len = strlen( pattern );
    uint8_t c;
    while ( match < len ) {
        if ( 1 != read( nano_fd, &c, 1 ) )
            return -1;
        if ( c == pattern[ match ] )
            ++match;
        else
            match = 0;
    }
    return 0;
}


static int nano_send_string( const char *string ) {
    int len = strlen( string );
    int wlen = write( nano_fd, string, len );
    if ( wlen != len ) {
        fprintf( stderr, "Error from write: %d, %d\n", wlen, errno );
        return -1;
    }
    tcdrain( nano_fd ); /* delay for output */
    return 0;
}


static void nano_send_command( const char *cmd ) {
    nano_send_string( cmd );  // send the command
    nano_send_string( "\r" ); // .. terminated with CR
    nano_wait_for( cmd );     // wait for echo
    nano_wait_for( "\r\n" );  // .. terminated by CR LF
}


static int nano_get_buffer( uint8_t *buf, int size ) {
    int sum = 0;
    uint8_t *bp = buf;
    /* simple noncanonical input */
    do { // nanovna sends 16 bit rgb565 date in chunks of two lines
        int rdlen = read( nano_fd, bp, nano_width * 2 * 2 );
        if ( rdlen > 0 ) {
            sum += rdlen;
            bp += rdlen;
            // printf( "got %d, total %d\n", rdlen, sum );
        } else if ( rdlen < 0 ) {
            fprintf( stderr, "Error from read: %d: %s\n", rdlen, strerror( errno ) );
            return -1;
        } else { /* rdlen == 0 */
            fprintf( stderr, "Timeout from read\n" );
            return -1;
        }
        /* repeat read to get full message */
    } while ( sum < size );
    return sum;
}


// clear last column of rgb565 because of random artifacts in some lines
static void clear_last_nv_col( uint8_t *buffer ) {
    int iii = 0;
    do {
        iii += 2 * nano_width;
        buffer [ iii - 1 ] = 0;
        buffer [ iii - 2 ] = 0;
    } while ( iii < nano_width * nano_height * 2 );
}


// in-buffer conversion from native big-endian rgb565 to little-endian rgb888
static void nv2rgb( uint8_t *buffer, int screensize ) {
    uint8_t *nv = buffer + 2 * screensize;  // this points at 2/3 of the buffer (after end of nv)
    uint8_t *rgb = buffer + 3 * screensize; // this points after the end of rgb888 buffer
    while ( screensize-- ) {                // iterate backwards
        // fetch two bytes of rgb565
        uint8_t lsb = *--nv;
        uint8_t msb = *--nv;
        // convert to rgb888
        uint8_t r = msb & 0xf8;
        uint8_t g = ( ( msb & 0x07 ) << 5 ) | ( ( lsb & 0xe0 ) >> 3 );
        uint8_t b = ( lsb & 0x1f ) << 3;
        // write three bytes of rgb888
        *--rgb = b;
        *--rgb = g;
        *--rgb = r;
    }
}


int writePNG( const char *filename, int width, int height, const uint8_t *buffer, char *title ) {
    int status = 0;
    FILE *fp = NULL;
    png_structp png_ptr = NULL;
    png_infop info_ptr = NULL;

    // Open file for writing (binary mode)
    fp = fopen( filename, "wb" );
    if ( fp == NULL ) {
        fprintf( stderr, "Could not open file %s for writing\n", filename );
        status = -1;
        goto finalise;
    }

    // Initialize write structure
    png_ptr = png_create_write_struct( PNG_LIBPNG_VER_STRING, NULL, NULL, NULL );
    if ( png_ptr == NULL ) {
        fprintf( stderr, "Could not allocate write struct\n" );
        status = -1;
        goto finalise;
    }

    // Initialize info structure
    info_ptr = png_create_info_struct( png_ptr );
    if ( info_ptr == NULL ) {
        fprintf( stderr, "Could not allocate info struct\n" );
        status = -1;
        goto finalise;
    }

    // Setup Exception handling
    if ( setjmp( png_jmpbuf( png_ptr ) ) ) {
        fprintf( stderr, "Error during png creation\n" );
        status = -1;
        goto finalise;
    }

    png_init_io( png_ptr, fp );

    // Write header (8 bit colour depth)
    png_set_IHDR( png_ptr, info_ptr, width, height, 8, PNG_COLOR_TYPE_RGB, PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_BASE,
                  PNG_FILTER_TYPE_BASE );

    // Set title
    if ( title != NULL ) {
        png_text title_text;
        title_text.compression = PNG_TEXT_COMPRESSION_NONE;
        title_text.key = "Title";
        title_text.text = title;
        png_set_text( png_ptr, info_ptr, &title_text, 1 );
    }

    png_write_info( png_ptr, info_ptr );

    // Write image data
    for ( int row = 0; row < height; ++row ) {
        png_write_row( png_ptr, buffer + row * width * 3 );
    }

    // End write
    png_write_end( png_ptr, NULL );

finalise:
    if ( fp != NULL )
        fclose( fp );
    if ( info_ptr != NULL )
        png_free_data( png_ptr, info_ptr, PNG_FREE_ALL, -1 );
    if ( png_ptr != NULL )
        png_destroy_write_struct( &png_ptr, (png_infopp)NULL );

    return status;
}


// this is the easiest straight-forward way to create an image from a pixel array
// using the netpbm image format
static int writePPM( const char *filename, int width, int height, const uint8_t *buffer, char *title ) {
    FILE *fp = fopen( filename, "wb" );
    if ( fp == NULL ) {
        fprintf( stderr, "Error opening %s: %s\n", filename, strerror( errno ) );
        return -1;
    }
    // print the header, simple format: "P6 <width> <height> <maxvalue>\n"
    fprintf( fp, "P6\n" );                       // magic value "P6" -> binary portable pixmap "*.ppm"
    if ( title )                                 // include the title into the header
        fprintf( fp, "# %s\n", title );          // lines starting with '#' are treated as comment
    fprintf( fp, "%d %d 255\n", width, height ); // maxvalue = 255 -> one byte per color component
    fwrite( buffer, width * height, 3, fp );     // write 3 byte per pixel
    fclose( fp );                                // ready
    return 0;
}


int main( int argc, char **argv ) {

    uint8_t nano_buffer[ nano_width * nano_height * 3 ]; // enough place for 24bit rgb888 target format

    char name[ 256 ];
    char *target = name;
    char *title = "NanoVNA screenshot";

    if ( nano_open() < 0 ) // connect to NanoVNA
        return -1;

    if ( argc > 1 ) {
        target = argv[ 1 ];
    } else {
        time_t timer;
        struct tm *tm_info;
        timer = time( NULL );
        tm_info = localtime( &timer );
        strftime( target, 256, "NanoVNA_%Y%m%d_%H%M%S.png", tm_info );
        puts( target );
    }

    nano_set_interface_attribs( B115200 ); // baudrate 115200, 8 bits, no parity, 1 stop bit

    nano_send_command( "pause" ); // pause screen update
    nano_wait_for( "ch> " );      // .. got it

    nano_send_command( "capture" ); //

    nano_get_buffer( nano_buffer, nano_width * nano_height * 2 ); // fetch the screen as 16 bit rgb565

    nano_wait_for( "ch> " ); // wait for capture end

    nano_send_command( "resume" ); // resume screen update
    nano_wait_for( "ch> " );       // .. got it

    nano_close();

    clear_last_nv_col( nano_buffer );
    nv2rgb( nano_buffer, nano_width * nano_height );

    if ( strlen( target ) >= 4 && 0 == strcmp( target + strlen( target ) - 4, ".ppm" ) )
        writePPM( target, nano_width, nano_height, nano_buffer, title );
    else
        writePNG( target, nano_width, nano_height, nano_buffer, title );

    return 0;
}
