// SPDX-License-Identifier: GPL-2.0+

// A simple gateway to the NanoVNA shell commands for use in automatisation scripts.
// usage: nanovna <COMMAND> <ARG1> <ARG2> ...

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>


const char *nano_port = "/dev/ttyACM0";

static int nano_fd = 0;


static int nano_open() {
    nano_fd = open( nano_port, O_RDWR | O_NOCTTY | O_SYNC );
    if ( nano_fd < 0 ) {
        fprintf( stderr, "Error opening %s: %s\n", nano_port, strerror( errno ) );
        exit( -1 );
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


// read from input and echo the char until pattern was received, do not echo the pattern
static int nano_wait_for( const char *pattern, int echo ) {
    int matched = 0;
    int len = strlen( pattern );
    uint8_t c;
    while ( matched < len ) {              // still no match
        if ( 1 != read( nano_fd, &c, 1 ) ) // read error
            return -1;
        if ( c == pattern[ matched ] ) { // possible match, do not echo
            ++matched;
        } else { // nope
            if ( echo ) {
                if ( matched ) { // if there was a partial match then echo the suppressed chars
                    for ( int iii = 0; iii < matched; ++iii )
                        putchar( pattern[ iii ] );
                }
                putchar( c ); // echo all non matching char
            }
            matched = 0;
        }
    }
    return 0;
}


static int nano_send_string( const char *string ) {
    int len = strlen( string );
    int written = write( nano_fd, string, len );
    if ( written != len ) {
        fprintf( stderr, "Error from write: %d, %d\n", written, errno );
        return -1;
    }
    tcdrain( nano_fd ); /* delay for output */
    return 0;
}


static void nano_send_command( const char *cmd ) {
    nano_send_string( cmd );    // send the command
    nano_send_string( "\r" );   // .. terminated with CR
    nano_wait_for( cmd, 0 );    // wait for cmd but do not echo
    nano_wait_for( "\r\n", 0 ); // .. terminated by CR LF (no echo)
}


int main( int argc, char **argv ) {

    char cmdline[ 260 ] = "";

    if ( 0 == --argc ) // return if no argument
        return 1;

    strncat( cmdline, *( ++argv ), 256 ); // get 1st part
    while ( --argc ) {                    // add other parts separated by one space
        int len = strlen( cmdline );
        if ( len < 250 ) {
            strcat( cmdline, " " ); // separator
            ++len;
            strncat( cmdline, *( ++argv ), 256 - len ); // no longer than 256
        }
    }

    nano_open(); // connect to NanoVNA

    nano_set_interface_attribs( B115200 ); // baudrate 115200, 8 bits, no parity, 1 stop bit

    nano_send_command( cmdline ); // send the complete line
    nano_wait_for( "ch> ", 1 );   // .. got it

    nano_close();

    return 0;
}
