import json
from binance.client import Client

with open("binance-conf.json") as binance_conf_file:
	binance_conf = json.load(binance_conf_file)

client = Client(binance_conf["API_KEY"], binance_conf["SECRET_KEY"])
	
class Asset:
	def __init__(self, ticker):
		self.ticker = ticker
		self.amount = 0.0
		self.usdtValue = 0.0
		self.usdtPairPrice = 0.0
	
	def computeUsdtValue(self):
		if self.ticker != 'USDT':
			self.usdtPairPrice = float(client.get_avg_price(symbol=self.ticker+'USDT')["price"])
			self.usdtValue = self.amount * self.usdtPairPrice
		else :
			self.usdtValue = self.amount

class Portfolio:
	def __init__(self):
		self.assets = []
		self.usdtValue = 0.0	
		
	def computeUsdtValue(self):
		for asset in self.assets:
			self.usdtValue += asset.usdtValue
			
		return self.usdtValue



def getPortfolio():
	portfolio = Portfolio()
	res = client.get_exchange_info()
	info = client.get_account_snapshot(type='SPOT')
	#print(info)
	
	for asset in info["snapshotVos"][0]["data"]["balances"]:
		if (asset["free"] != '0') or (asset["locked"] != '0'):
			#print(asset["asset"] + " : " + asset["free"])
			newAsset = Asset(asset["asset"])
			details = client.get_asset_balance(asset=newAsset.ticker)
			newAsset.amount = float(details["free"]) + float(details["locked"])
			newAsset.computeUsdtValue()
			portfolio.assets.append(newAsset)
			
	for coin in portfolio.assets:
		print(coin.ticker)
		print("Amount: " + str(coin.amount))
		print("Price (USDT): " + str(coin.usdtPairPrice))
		print("Value (USDT): " + str(coin.usdtValue))
		print("")
		
	portfolio.computeUsdtValue()

	return portfolio	

if __name__ == "__main__":
	myPortfolio = getPortfolio()
	print("Portfolio value (USDT): " + str(myPortfolio.usdtValue))