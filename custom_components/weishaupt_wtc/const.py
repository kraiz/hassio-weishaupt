"""Constants for the Weishaupt WTC integration."""

DOMAIN = "weishaupt_wtc"

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "Admin123"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_PORT = 80

API_ENDPOINT = "/ajax/CanApiJson.json"

# CanApiJson commands
CMD_GET = 0x01
CMD_RESPONSE = 0x02
CMD_SET = 0x03
CMD_ACK = 0x04
CMD_ERROR = 0x05
CMD_GET_STRING = 0x11
CMD_RESPONSE_STRING = 0x12
CMD_SET_STRING = 0x13
CMD_ACK_STRING = 0x14

# Source identifiers
SRC_DDC = "DDC"
SRC_SYS = "SYS"
