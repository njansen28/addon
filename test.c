#include <math.h>
#include <inttypes.h>
#include <avr/io.h>
#include <avr/pgmspace.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <util/delay.h>
#include <stdio.h>
#include <string.h>

#define GAP_PROFILE_CENTRAL 0x08
#define KEYLEN 16
#define BUILD_UINT16(loByte, hiByte) ((uint16_t)(((loByte) & 0x00FF) + (((hiByte) & 0x00FF) << 8)))

#define DEVICE_INITIALIZED 0x600
#define DEVICE_DISCOVERY_DONE 0x601
#define DEVICE_INFORMATION 0x60D
#define BAUD 115200
#include <util/setbaud.h>

static uint8_t gapCentralRoleTaskId = 0;
static uint8_t gapCentralRoleIRK[KEYLEN] = {0};
static uint8_t gapCentralRoleSRK[KEYLEN] = {0};
static uint32_t gapCentralRoleSignCounter = 1;
static uint8_t gapCentralRoleMaxScanRes = 5;

uint8_t buf[64];
char szInfo[63];

void publish(char* event, char* message) {
	printf("%s: %s\n", event, message);
}

void uart_init(void) {
   UBRR0H = UBRRH_VALUE;
   UBRR0L = UBRRL_VALUE;

#if USE_2X
   UCSR0A |= _BV(U2X0);
#else
   UCSR0A &= ~(_BV(U2X0));
#endif

   UCSR0C = _BV(UCSZ01) | _BV(UCSZ00); /* 8-bit data */
   UCSR0B = _BV(RXEN0) | _BV(TXEN0);   /* Enable RX and TX */
}

void uart_putchar(char c) {
   loop_until_bit_is_set(UCSR0A, UDRE0); /* Wait until data register empty. */
   UDR0 = c;
}

char uart_getchar(void) {
   loop_until_bit_is_set(UCSR0A, RXC0); /* Wait until data exists. */
   return UDR0;
}

FILE uart_output = FDEV_SETUP_STREAM(uart_putchar, NULL, _FDEV_SETUP_WRITE);
FILE uart_input = FDEV_SETUP_STREAM(NULL, uart_getchar, _FDEV_SETUP_READ);
FILE uart_io = FDEV_SETUP_STREAM(uart_putchar, uart_getchar, _FDEV_SETUP_RW);

int hci_init(uint8_t taskID, uint8_t profileRole, uint8_t maxScanResponses, uint8_t *pIRK, uint8_t *pSRK, uint32_t *pSignCounter){
    uint8_t len = 0;
    int i;
    
    buf[len++] = 0x01;                  // -Type    : 0x01 (Command)
    buf[len++] = 0x00;                  // -Opcode  : 0xFE00 (GAP_DeviceInit)
    buf[len++] = 0xFE;
  
    buf[len++] = 0x26;                  // -Data Length
    buf[len++] = profileRole;           //  Profile Role
    buf[len++] = maxScanResponses;      //  MaxScanRsps
    memcpy(&buf[len], pIRK, 16);        //  IRK
    len += 16;
    memcpy(&buf[len], pSRK, 16);        //  SRK
    len += 16;
    memcpy(&buf[len], pSignCounter, 4); //  SignCounter
    len += 4;

    //Serial1.write(buf, len);
	for (i = 0; i < len; i++) {
		putchar(buf[i]);
	}
	
    return 1;
}

int hci_start_discovery() {
    uint8_t len = 0;
    int i;
	
    buf[len++] = 0x01;                 // -Type    : 0x01 (Command)
    buf[len++] = 0x04;                 // -Opcode  : 0xFE04 (GAP_DeviceDiscoveryRequest)
    buf[len++] = 0xFE;
        
    buf[len++] = 0x03;                 // -Data Length
    buf[len++] = 0x03;                 //  Mode
    buf[len++] = 0x01;                 //  ActiveScan
    buf[len++] = 0x00;                 //  WhiteList
  
    //Serial1.write(buf, len);
    for (i = 0; i < len; i++) {
	putchar(buf[i]);
    }
    return 1;
}

// BLE Event Processing
void ble_event_process() {
    uint8_t type, event_code, data_len, status1;
    uint16_t event;
    int i;

    type = getchar();
    _delay_ms(100);
    event_code = getchar();
    data_len = getchar();
  
    for (i = 0; i < data_len; i++)
        buf[i] = getchar();
    
    event = BUILD_UINT16(buf[0], buf[1]);
    status1 = buf[2];
  
    switch(event){
        case DEVICE_INITIALIZED:{
            hci_start_discovery();
            
            break;
        }
        case DEVICE_DISCOVERY_DONE:{
           hci_start_discovery();
      
            break;
        }
        case DEVICE_INFORMATION:{
            // Just some visual indication
            //digitalWrite(D7, HIGH);
            
            // Get RSSI and Measured Power
            int rssi = buf[11];
            int txpower = buf[42];
            
            // Calculate Distance
            // This is based on the algorithm from http://stackoverflow.com/questions/20416218/understanding-ibeacon-distancing
            //
            double distance = 0.0;
            double ratio = (256 - rssi) * 1.0 / (256 - txpower);
              
            if(ratio < 1.0)
                distance = pow(ratio, 10);
            else
                distance = (0.89976)*pow(ratio,7.7095) + 0.111;
                
            
            // Publish information, since we can only have 63 chars, let's do it in two step
            // First publish the iBeacon UUID
            sprintf(szInfo, "%02X%02X%02X%02X-%02X%02X-%02X%02X-%02X%02X-%02X%02X%02X%02X%02X%02X",
                buf[22], buf[23], buf[24], buf[25],
                buf[26], buf[27],
                buf[28], buf[29],
                buf[30], buf[31],
                buf[32], buf[33], buf[34], buf[35], buf[36], buf[37]);
            
            publish("bnuuid", szInfo);
            
            // Delay another publish
            _delay_ms(1000);
            
            // Publish iBeacon information
            sprintf(szInfo, "Major: %d, Minor: %d, Measured Power: %d, Distance: %.2f",
                BUILD_UINT16(buf[39], buf[38]),
                BUILD_UINT16(buf[41], buf[40]),
                buf[42],
                distance);
                
            publish("bninfo", szInfo);
            
            // If the distance is less that 0.5m, that is too close, then turn on the LED on D2
            // if(distance < 0.5){
                // digitalWrite(D2, HIGH);
            // }
            // else{
                // digitalWrite(D2, LOW);
            // }
            
            // // Blink D7 LED to indicate we found iBeacon
            // digitalWrite(D7, LOW);

            break;
        }
    }
}


int main(void)
{

   /* Setup serial port */
   uart_init();
   stdout = &uart_output;
   stdin  = &uart_input;
   
   hci_init(gapCentralRoleTaskId, GAP_PROFILE_CENTRAL, gapCentralRoleMaxScanRes, gapCentralRoleIRK, 		gapCentralRoleSRK, &gapCentralRoleSignCounter);

   char input;

   // Setup ports
   DDRB |= (1<<1) | (1<<0);
   PORTB |= (1<<0);
   PORTB &= ~(1<<1);

   /* Print hello and then echo serial
   ** port data while blinking LED */
   printf("Hello world!\r\n");
   while(1) {
      input = getchar();
	  ble_event_process();
      //printf("You wrote %c\r\n", input);
      //PORTB ^= 0x01;
   }

}



