import json
from binance.client import Client


with open("binance-conf.json") as binance_conf_file:
	binance_conf = json.load(binance_conf_file)


def main():
	client = Client(binance_conf["API_KEY"], binance_conf["SECRET_KEY"])
	res = client.get_exchange_info()
	print(res)

if __name__ == "__main__":
	main()