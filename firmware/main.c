#include <stdio.h>
#include <string.h>
#include "esp_wifi.h"
#include "esp_system.h"
#include "nvs_flash.h"
#include "esp_event.h"
#include "protocol_examples_common.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "freertos/event_groups.h"

#include "esp_log.h"
#include "esp_websocket_client.h"
#include "esp_event.h"

#include "driver/gpio.h"

// GPIO settings
#define GPIO_BUTTON (0)
#define GPIO_LED    (13)
//#define GPIO_READ   (17)
//#define GPIO_SWITCH (21)

// speed LED pins
#define GPIO_SPEED5 (21)
#define GPIO_SPEED4 (17)
#define GPIO_SPEED3 (16)
#define GPIO_SPEED2 (19)
#define GPIO_SPEED1 (18)

// dust LED pins
#define GPIO_DUST5 (15)
#define GPIO_DUST4 (32)
#define GPIO_DUST3 (14)
#define GPIO_DUST2 (22)
#define GPIO_DUST1 (23)

// auto speed LED
#define GPIO_AUTO (5)
// buttons
#define GPIO_SPDBTN (4)   // speed
#define GPIO_PWRBTN (26)  // power
#define GPIO_AUTOBTN (25) // auto
typedef enum {
	LED_DUST,
	LED_SPEED,
} Leds_t; // LED types

#define NO_DATA_TIMEOUT_SEC 60

static const char *TAG = "WEBSOCKET";
static const char *UUID = "AEHS3Y3KH1";

#define TRUE (1)
#define FALSE (0)

// websocket opcodes (frames)
#define OPCODE_CONTINUATION 	(0x0)
#define OPCODE_TEXT				(0x1)
#define OPCODE_BINARY			(0x2)
#define OPCODE_CONNECTION_CLOSE (0x8)
#define OPCODE_PING				(0x9)
#define OPCODE_PONG				(0xA)

// command names from server
typedef enum {
	CMD_ON         = 100,
	CMD_OFF        = 101,
	CMD_GETSPEED   = 102,
	CMD_SETSPEED   = 103,
	CMD_GETDUST    = 104,
	CMD_AUTOSPDON  = 105,
	CMD_AUTOSPDOFF = 106,
	CMD_QUERY      = 107,
} ap_cmd_t;

// replies to names to server
#define INIT_SERIAL "serial"
#define REPLY_SPEED "speed"
#define REPLY_DUST  "dust"
#define KEEP_ALIVE	"alive"

#define WEBSOCKETORG (0)
#define HEROKU (1)

#if WEBSOCKETORG
extern const uint8_t websocket_org_pem_start[] asm("_binary_websocket_org_pem_start");
#elif HEROKU
extern const uint8_t heroku_com_pem_start[] asm("_binary_heroku_com_pem_start");
#else
extern const uint8_t ngrok_com_pem_start[] asm("_binary_ngrok_com_pem_start");
#endif

static TimerHandle_t shutdown_signal_timer;
static SemaphoreHandle_t shutdown_sema;
//static SemaphoreHandle_t reply_sema;
static int registered = FALSE;
static int ws_failure = TRUE;
static int was_connected = FALSE; // don't shutdown if connection was never establish, wait for connection

static int crash_counter = 0; // count how many times connection died

static int readLevels(Leds_t type)
{
	ESP_LOGI(TAG, "SPEED %d %d %d %d %d",gpio_get_level(GPIO_SPEED5),gpio_get_level(GPIO_SPEED4),gpio_get_level(GPIO_SPEED3),
			gpio_get_level(GPIO_SPEED2),gpio_get_level(GPIO_SPEED1));
	ESP_LOGI(TAG, "DUST %d %d %d %d %d",gpio_get_level(GPIO_DUST5),gpio_get_level(GPIO_DUST4),gpio_get_level(GPIO_DUST3),
			gpio_get_level(GPIO_DUST2),gpio_get_level(GPIO_DUST1));
	if (type == LED_SPEED)
	{
		if (gpio_get_level(GPIO_SPEED5) == 0)
			return 5;
		else if (gpio_get_level(GPIO_SPEED4) == 0)
			return 4;
		else if (gpio_get_level(GPIO_SPEED3) == 0)
			return 3;
		else if (gpio_get_level(GPIO_SPEED2) == 0)
			return 2;
		else if (gpio_get_level(GPIO_SPEED1) == 0)
			return 1;
	}
	else if (type == LED_DUST)
	{
		if (gpio_get_level(GPIO_DUST5) == 0)
			return 5;
		else if (gpio_get_level(GPIO_DUST4) == 0)
			return 4;
		else if (gpio_get_level(GPIO_DUST3) == 1)
			return 3;
		else if (gpio_get_level(GPIO_DUST2) == 1)
			return 2;
		else if (gpio_get_level(GPIO_DUST1) == 1)
			return 1;
	}
	return 0;
}
static void pressSpeed(int presses)
{
	int i;
	for (i = 0; i < presses; i++)
	{
		gpio_set_level(GPIO_SPDBTN,1);
		vTaskDelay(100 / portTICK_PERIOD_MS);
		gpio_set_level(GPIO_SPDBTN,0);
		vTaskDelay(100 / portTICK_PERIOD_MS);
	}
}

static void shutdown_signaler(TimerHandle_t xTimer)
{
    ESP_LOGI(TAG, "No PING received for %d seconds, signaling shutdown", NO_DATA_TIMEOUT_SEC);
    ws_failure = TRUE;
    xSemaphoreGive(shutdown_sema);
}

static void websocket_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
{
    esp_websocket_event_data_t *data = (esp_websocket_event_data_t *)event_data;
    esp_websocket_client_handle_t client = data->client;
    switch (event_id)
    {
    case WEBSOCKET_EVENT_CONNECTED:
        ESP_LOGI(TAG, "WEBSOCKET_EVENT_CONNECTED");
        ws_failure = FALSE;
        break;
    case WEBSOCKET_EVENT_DISCONNECTED:
        ESP_LOGI(TAG, "WEBSOCKET_EVENT_DISCONNECTED");
        ws_failure = TRUE;
        registered = FALSE;
        crash_counter++;
        break;
    case WEBSOCKET_EVENT_DATA:
        ESP_LOGI(TAG, "WEBSOCKET_EVENT_DATA");
        ESP_LOGI(TAG, "Received opcode=%d", data->op_code);
    	if (data->op_code == OPCODE_CONNECTION_CLOSE)
    	{
    		ESP_LOGI(TAG, "Connection Close");
    		break;
    	}
    	else if (data->op_code == OPCODE_PING)
    	{
    		ESP_LOGI(TAG, "PING, Sending PONG. crash count:%d.", crash_counter);
    		ESP_LOGI(TAG, "speed level is %d",readLevels(LED_SPEED));
    		ESP_LOGI(TAG, "auto mode is %s",gpio_get_level(GPIO_AUTO) ? "off":"on");
    		ESP_LOGI(TAG, "dust level is %d",readLevels(LED_DUST));
    		// send a pong back, as required by websocket spec 5.5.2
    		esp_websocket_client_send_pong(client, NULL, 0, portMAX_DELAY);
    		xTimerReset(shutdown_signal_timer, portMAX_DELAY);
    		gpio_set_level(GPIO_LED, 1);
    		//gpio_set_level(GPIO_SPDBTN, 1);
    		//vTaskDelay(200 / portTICK_PERIOD_MS);
    		//gpio_set_level(GPIO_SPDBTN, 0);

// most likely dont need this if server's websocket protocol always get disconnect message even if device dies
#if (TRUE)
    		// why is this here and not in main loop? because server (in lower levels) sends ping every 10 seconds,
    		// if i reply back with serial number I can keep status update
    		// but if that doesn't work, this would have to move to main loop
    		// also if i don't have this, device get weird messages
    		if (registered == TRUE) // only send status up IF the device id registered
    		{
				char message[32];
                int len = sprintf(message, "%s:%s", KEEP_ALIVE, UUID);
                ESP_LOGI(TAG, "Keep Alive: Sending %s", message);
                esp_websocket_client_send_text(client, message, len, portMAX_DELAY);
    		}
    		break;
#endif
    	}
    	else if (data->op_code == OPCODE_PONG)
    	{
    		// not sure why certain servers sends out PONG, I dont think ESP sends out PINGS
    		ESP_LOGI(TAG, "PONG");
    		xTimerReset(shutdown_signal_timer, portMAX_DELAY);
    		gpio_set_level(GPIO_LED, 0);
    		//gpio_set_level(GPIO_SWITCH, 0);
    		break;
    	}
        ESP_LOGW(TAG, "Received=%.*s", data->data_len, (char *)data->data_ptr);
        ESP_LOGW(TAG, "Total payload length=%d, data_len=%d, current payload offset=%d\r\n", data->payload_len, data->data_len, data->payload_offset);

        // only op_codes with data should get to this point
        if (registered == FALSE)
    	{	// see if registering to server is successful, if it is, i should get back my UUID, otherwise fail.

    		if (data->data_len != 17)
    		{
    			char message[32];
                int len = sprintf(message, "%s:wrong", INIT_SERIAL);
                ESP_LOGI(TAG, "wrong serial length. Sending %s", message);
                esp_websocket_client_send_text(client, message, len, portMAX_DELAY);
    			break;
    		}
    		else
    		{  // if the returned data length is the same, then match with internal key for verification
    			char reply[32];
    			char key[32];
    			sprintf(key, "%s:%s", INIT_SERIAL,UUID);
    			strncpy(reply, (char *)data->data_ptr, data->data_len);
    			reply[data->data_len] = '\0';
    			ESP_LOGI(TAG, "returned %s",reply);
    			if (strcmp(key,reply) == 0)
    			{
    				ESP_LOGI(TAG, "match key, acccess allowed");
    				registered = TRUE;
    			}
    		}
    	}
    	else // if registered, then we can begin accepting commands
    	{
    		char message[8];
    		if (data->data_len > 8)
    		{
    			ESP_LOGE(TAG, "command too long");
    			break;
    		}
    		strncpy(message, (char *)data->data_ptr, data->data_len); // no limiter from server
    		message[data->data_len] = '\0';

    		int speedSetting = 0;

    		// if length of command is 4, then we know it's for set speed
    		if (data->data_len == 4)
    		{
    			speedSetting = message[3] - '0';
    			message[3] = '\0';					// cover up my crime
    		}
    		int command = atoi(message);
    		ESP_LOGI(TAG, "command: %d\n", command);
    		//char reply;
    		char sReply[20];
    		int speedLevel = 0;
    		int len = 0;
    		int speedDiff = 0;
    		int dustLevel = 0;
			switch (command)
			{
			case CMD_ON:
				// check register to see if its on or off
				if (gpio_get_level(GPIO_SPEED1) == 1) // it means device is off
				{
					gpio_set_level(GPIO_PWRBTN,1);
					vTaskDelay(100 / portTICK_PERIOD_MS);
					gpio_set_level(GPIO_PWRBTN,0);
				}
				break;
			case CMD_OFF:
				if (gpio_get_level(GPIO_SPEED1) == 0) // it means device is on
				{
					gpio_set_level(GPIO_PWRBTN,1);
					vTaskDelay(100 / portTICK_PERIOD_MS);
					gpio_set_level(GPIO_PWRBTN,0);
				}
				break;
			case CMD_AUTOSPDON: //ESP_LOGI(TAG, "auto mode is %s",gpio_get_level(GPIO_AUTO) ? "off":"on");
				ESP_LOGI(TAG, "Turning on Auto");
				if (gpio_get_level(GPIO_AUTO) == 1) // 1 is for off!
				{
					gpio_set_level(GPIO_AUTOBTN,1); // assumes auto is off
					vTaskDelay(200 / portTICK_PERIOD_MS);
					gpio_set_level(GPIO_AUTOBTN,0);
				}
				break;
			case CMD_AUTOSPDOFF:
				// cannot read auto button's LED
				ESP_LOGI(TAG, "Turning off Auto");
				if (gpio_get_level(GPIO_AUTO) == 0)
				//if (gpio_get_level(GPIO_SPEED1) == 0) // it means device is on
				{
					gpio_set_level(GPIO_AUTOBTN,1);
					vTaskDelay(100 / portTICK_PERIOD_MS);
					gpio_set_level(GPIO_AUTOBTN,0);
				}
				break;
			case CMD_GETSPEED:
				speedLevel = readLevels(LED_SPEED);  // check speed from LEDs
				ESP_LOGI(TAG, "speed level is %d", speedLevel);

				len = sprintf(sReply, "%d:%d", CMD_GETSPEED, speedLevel);
				ESP_LOGI(TAG, "Sending reply: %s", sReply);
				esp_websocket_client_send_text(client, sReply, len, portMAX_DELAY);
				break;
			case CMD_SETSPEED:
				speedLevel = readLevels(LED_SPEED);
				if (speedLevel > speedSetting)
					speedDiff = 5 - speedLevel + speedSetting;
				else if (speedLevel < speedSetting)
					speedDiff = speedSetting - speedLevel;
				ESP_LOGI(TAG, "speedDiff: %d", speedDiff);
				pressSpeed(speedDiff);
				break;
			case CMD_GETDUST:
				dustLevel = readLevels(LED_DUST);
				//reply = '7';
				len = sprintf(sReply, "%d:%d", CMD_GETDUST, dustLevel);
				ESP_LOGI(TAG, "Sending dust %d", dustLevel);
				esp_websocket_client_send_text(client, sReply, len, portMAX_DELAY);
				break;
			case CMD_QUERY:
				len = sprintf(sReply, "%d:%d,%d,%d,%d", CMD_QUERY,
						gpio_get_level(GPIO_SPEED1) ? 0:1, // if speed 1 is on, that means device is on
						readLevels(LED_SPEED),
						gpio_get_level(GPIO_AUTO) ? 0:1,
						readLevels(LED_DUST));
				ESP_LOGI(TAG, "Sending Query: %s", sReply);
				esp_websocket_client_send_text(client, sReply, len, portMAX_DELAY);
				break;
			default:
				break;
			}
    	}
        //xSemaphoreGive(shutdown_sema);

        break;
    case WEBSOCKET_EVENT_ERROR:
        ESP_LOGI(TAG, "WEBSOCKET_EVENT_ERROR");
        ws_failure = TRUE;
        break;
    }
}
// for some reason, the pem can be found by going to their respective website
// but not for ngrok.io
static void websocket_task(void *pvParameters)
{
#if (WEBSOCKETORG)
    const esp_websocket_client_config_t websocket_cfg = {
        .uri = "wss://echo.websocket.org",
		.port = 443,
        .cert_pem = (const char *)websocket_org_pem_start,
    };
#elif (HEROKU)
    const esp_websocket_client_config_t websocket_cfg = {
		.uri = "wss://.com",
		.path = "ws/",
		.port = 443,
        .cert_pem = (const char *)heroku_com_pem_start,
    };
#else
    const esp_websocket_client_config_t websocket_cfg = {
		.uri = "ws://2692e722bc1f.ngrok.io/ws/",
		//.path = "ws/",
		//.port = 80,
        //.cert_pem = (const char *)ngrok_com_pem_start,
    };
#endif
    // reply_sema = xSemaphoreCreateBinary();

    // shutdown timer: websocket usually should have pings and pongs to keep connection active, looks lik it's 10 seconds apart
    shutdown_signal_timer = xTimerCreate("Websocket shutdown timer", NO_DATA_TIMEOUT_SEC * 1000 / portTICK_PERIOD_MS,
                                         pdFALSE, NULL, shutdown_signaler);
#if WEBSOCKETORG
    ESP_LOGI("SSL","%s",websocket_org_pem_start);
#elif HEROKU
    ESP_LOGI("SSL","%s",heroku_com_pem_start);
#else
    ESP_LOGI("SSL","%s",ngrok_com_pem_start);
#endif
    xTimerStart(shutdown_signal_timer, portMAX_DELAY);
    while (1) // this task loops forever in here
    {
		esp_websocket_client_handle_t client = esp_websocket_client_init(&websocket_cfg);
		esp_websocket_register_events(client, WEBSOCKET_EVENT_ANY, websocket_event_handler, (void *)client);
		esp_websocket_client_start(client);
		ESP_LOGI(TAG, "website: %s",websocket_cfg.uri);
		while (1) // only breaks out here IF websocket connection has a problem
		{
			char data[32];
			while ((!esp_websocket_client_is_connected(client)) && was_connected == FALSE)
			{
				ESP_LOGI(TAG, "Waiting for websocket connection");
				vTaskDelay(2000 / portTICK_PERIOD_MS);
				xTimerReset(shutdown_signal_timer, portMAX_DELAY); // reset, so we don't die just trying to connect the first time
				was_connected = TRUE;
				ws_failure = FALSE;
			}
			if (registered == FALSE && ws_failure == FALSE) // if current session hasn't been registered to server, need to do so
			{
				int len = sprintf(data, "%s:%s", INIT_SERIAL,UUID);
				ESP_LOGI(TAG, "Sending %s", data);
				esp_websocket_client_send_text(client, data, len, portMAX_DELAY);
				// at this point, I should wait for reply in handler
				// need to wait for a certain time before sending more register requests
				vTaskDelay(3000 / portTICK_PERIOD_MS);
			}
			// likelyhood of websocket failing to connect but wifi/internet still up?

			if (ws_failure == TRUE && was_connected == TRUE) // if ws_failure happen for any reason
			{
				vTaskDelay(1000 / portTICK_PERIOD_MS);
				esp_websocket_client_stop(client);
				esp_websocket_unregister_events(client, WEBSOCKET_EVENT_ANY, websocket_event_handler);
				ESP_LOGI(TAG, "Websocket Stopped, restarting.");
				esp_websocket_client_destroy(client);  // will free up the client struct
				vTaskDelay(2000 / portTICK_PERIOD_MS);
				registered = FALSE;
				ws_failure = FALSE;
				was_connected = FALSE;
				break;
			}

		}
    }

}

static void GPIOInit(void)
{
	gpio_pad_select_gpio(GPIO_LED);
	gpio_pad_select_gpio(GPIO_BUTTON);
	gpio_pad_select_gpio(GPIO_SPEED5);
	gpio_pad_select_gpio(GPIO_SPEED4);
	gpio_pad_select_gpio(GPIO_SPEED3);
	gpio_pad_select_gpio(GPIO_SPEED2);
	gpio_pad_select_gpio(GPIO_SPEED1);

	gpio_pad_select_gpio(GPIO_DUST5);
	gpio_pad_select_gpio(GPIO_DUST4);
	gpio_pad_select_gpio(GPIO_DUST3);
	gpio_pad_select_gpio(GPIO_DUST2);
	gpio_pad_select_gpio(GPIO_DUST1);
	gpio_pad_select_gpio(GPIO_AUTO);

	gpio_pad_select_gpio(GPIO_SPDBTN);
	gpio_pad_select_gpio(GPIO_PWRBTN);
	gpio_pad_select_gpio(GPIO_AUTOBTN);



	gpio_set_pull_mode(GPIO_DUST3,GPIO_PULLDOWN_ONLY);
	gpio_set_pull_mode(GPIO_DUST2,GPIO_PULLDOWN_ONLY);
	gpio_set_pull_mode(GPIO_DUST1,GPIO_PULLDOWN_ONLY);
	gpio_set_direction(GPIO_SPEED5, GPIO_MODE_INPUT);
	gpio_set_direction(GPIO_SPEED4, GPIO_MODE_INPUT);
	gpio_set_direction(GPIO_SPEED3, GPIO_MODE_INPUT);
	gpio_set_direction(GPIO_SPEED2, GPIO_MODE_INPUT);
	gpio_set_direction(GPIO_SPEED1, GPIO_MODE_INPUT);
	gpio_set_direction(GPIO_DUST5, GPIO_MODE_INPUT);
	gpio_set_direction(GPIO_DUST4, GPIO_MODE_INPUT);
	gpio_set_direction(GPIO_DUST3, GPIO_MODE_INPUT);
	gpio_set_direction(GPIO_DUST2, GPIO_MODE_INPUT);
	gpio_set_direction(GPIO_DUST1, GPIO_MODE_INPUT);
	gpio_set_direction(GPIO_AUTO, GPIO_MODE_INPUT);

	gpio_set_direction(GPIO_SPDBTN, GPIO_MODE_OUTPUT);
	gpio_set_direction(GPIO_PWRBTN, GPIO_MODE_OUTPUT);
	gpio_set_direction(GPIO_AUTOBTN, GPIO_MODE_OUTPUT);



	gpio_set_direction(GPIO_LED, GPIO_MODE_OUTPUT);
}
void app_main(void)
{
	GPIOInit();
    ESP_LOGI(TAG, "[APP] Startup..");
    ESP_LOGI(TAG, "[APP] Free memory: %d bytes", esp_get_free_heap_size());
    ESP_LOGI(TAG, "[APP] IDF version: %s", esp_get_idf_version());
    esp_log_level_set("*", ESP_LOG_INFO);
    esp_log_level_set("WEBSOCKET_CLIENT", ESP_LOG_DEBUG);
    esp_log_level_set("TRANS_TCP", ESP_LOG_DEBUG);

    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    /* This helper function configures Wi-Fi or Ethernet, as selected in menuconfig.
     * Read "Establishing Wi-Fi or Ethernet Connection" section in
     * examples/protocols/README.md for more information about this function.
     */
    ESP_ERROR_CHECK(example_connect());

    //websocket_app_start();
    xTaskCreate(&websocket_task, "websocket_task", 8192, NULL, 5, NULL);
}
