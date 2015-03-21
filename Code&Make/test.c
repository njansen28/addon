//#include <math.h>
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
#define F_CPU 16000000 // rewrite


#define DEVICE_INITIALIZED 0x600
#define DEVICE_DISCOVERY_DONE 0x601
#define DEVICE_INFORMATION 0x60D
#define BAUD 115200
#define MYUBRR (F_CPU / 16 / BAUD) - 1 //rewrite
#define is_high(x,y) (x & _BV(y)) == _BV(y)
//#include <util/setbaud.h> // commented out for rewrite

static uint8_t gapCentralRoleTaskId = 0;
static uint8_t gapCentralRoleIRK[KEYLEN] = {0};
static uint8_t gapCentralRoleSRK[KEYLEN] = {0};
static uint32_t gapCentralRoleSignCounter = 1;
static uint8_t gapCentralRoleMaxScanRes = 5;

uint8_t buf[64];
char szInfo[63];

// Begin rewrite stuff
void delayLong()
{
	unsigned int delayvar;
	delayvar = 0; 
	while (delayvar <=  65500U)		
	{ 
		asm("nop");  
		delayvar++;
	} 
}

unsigned char serialCheckRxComplete(void)
{
	return( UCSR0A & _BV(RXC0)) ;		// nonzero if serial data is available to read.
}

unsigned char serialCheckTxReady(void)
{
	return( UCSR0A & _BV(UDRE0) ) ;		// nonzero if transmit register is ready to receive new data.
}

unsigned char serialRead(void)
{
	while (serialCheckRxComplete() == 0)		// While data is NOT available to read
	{;;} 
	return UDR0;
}

void serialWrite(unsigned char DataOut)
{
	while (serialCheckTxReady() == 0)		// while NOT ready to transmit 
	{;;} 
	UDR0 = DataOut;
}
void publish(char* event, char* message) {
	printf("%s: %s\r\n", event, message);
}

void uart_init(void) {
	/*Set baud rate */ 
	DDRD = _BV(1);
	UBRR0H = (unsigned char)(MYUBRR>>8); 
	UBRR0L = (unsigned char) MYUBRR; 
	/* Enable receiver and transmitter   */
	UCSR0B = (1<<RXEN0)|(1<<TXEN0); 
	/* Frame format: 8data, No parity, 1stop bit */ 
	UCSR0C = (3<<UCSZ00);  
   
   
   
   
   /*UBRR0H = UBRRH_VALUE;
   UBRR0L = UBRRL_VALUE;

#if USE_2X
   UCSR0A |= _BV(U2X0);
#else
   UCSR0A &= ~(_BV(U2X0));
#endif

   UCSR0C = _BV(UCSZ01) | _BV(UCSZ00);*/ /* 8-bit data */
   //UCSR0B = _BV(RXEN0) | _BV(TXEN0);   /* Enable RX and TX */
}
/*
void uart_putchar(char c) {
   loop_until_bit_is_set(UCSR0A, UDRE0); // Wait until data register empty. 
   UDR0 = c;
}
/*
char uart_getchar(void) {
   loop_until_bit_is_set(UCSR0A, RXC0); // Wait until data exists. 
   return UDR0;
}

FILE uart_output = FDEV_SETUP_STREAM(uart_putchar, NULL, _FDEV_SETUP_WRITE);
FILE uart_input = FDEV_SETUP_STREAM(NULL, uart_getchar, _FDEV_SETUP_READ);
FILE uart_io = FDEV_SETUP_STREAM(uart_putchar, uart_getchar, _FDEV_SETUP_RW);
*/
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
		serialWrite(buf[i]);
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
		serialWrite(buf[i]);
    }
    return 1;
}

// BLE Event Processing
void ble_event_process() {
    uint8_t type, event_code, data_len, status1;
    uint16_t event;
    int i;

	//_delay_ms(100);
	//printf("processing event\r\n");
    type = serialRead();
	//printf("type %hx\r\n", type);
    //_delay_ms(100);
    event_code = serialRead();
	//printf("event_code=%hx \r\n", event_code);
	//_delay_ms(100);  
	data_len = serialRead();
  	//printf("data_len=%hX\r\n", data_len);
    for (i = 0; i < data_len; i++) {
		//_delay_ms(100);       
		buf[i] = serialRead();
		//printf("%hhX\r\n", buf[i]);
    }
	
    
    event = BUILD_UINT16(buf[0], buf[1]);
    status1 = buf[2];
  
    switch(event){
        case DEVICE_INITIALIZED:{
			printf("device_initialized\r\n");
            hci_start_discovery();
            
            break;
        }
        case DEVICE_DISCOVERY_DONE:{
			printf("device discovery done\r\n");
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
              
            //if(ratio < 1.0)
            //    distance = pow(ratio, 10);
            //else
              //  distance = (0.89976)*pow(ratio,7.7095) + 0.111;
                
            
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
	    default: {
		printf("Default: %d\r\n", event);
	    }
        }
    }
}


int main(void)
{

   	/* Setup serial port */
   	uart_init();
   	//stdout = &uart_output;
   	//stdin  = &uart_input;

   	char input;

   	// Setup ports
   	DDRB |= (1<<1) | (1<<0) | (1<<2);
   	PORTB |= (1<<0);
   	PORTB &= ~(1<<1);
	PORTB = 0x01;
	PORTD &= 0x7F;

    DDRD = DDRD & 0x7F;

	while(!(is_high(PIND, PD7))) {
		PORTB = 0x04;
		//printf("\nNo button press %lX\r\n", PD7);
		_delay_ms(500);
	}

	hci_init(gapCentralRoleTaskId, GAP_PROFILE_CENTRAL, gapCentralRoleMaxScanRes, 		gapCentralRoleIRK, gapCentralRoleSRK, &gapCentralRoleSignCounter);

	PORTB = 0x01;
   	/* Print hello and then echo serial
  	** port data while blinking LED */
   	//printf("Hello world!\r\n");
   	while(1) {
      	input = getchar();
      	ble_event_process();
      	//printf("%hhX\r\n", input);
		//_delay_ms(100);
      		PORTB ^= 0x01;
   	}

}



