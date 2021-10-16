import json
import time
import yagmail
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

class Strategy:
	def __init__(self, freq):
		self.frequency = freq
		self.targetAssets = []

class TargetAsset:
	def __init__(self, json):
		self.ticker = json["ticker"]
		self.buyLimit = json["buyLimit"]
		self.sellLimit = json["sellLimit"]
		self.usdtPairPrice = 0.0
	
	def updateUsdtPairValue(self):
		if self.ticker != 'USDT':
			self.usdtPairPrice = float(client.get_avg_price(symbol=self.ticker+'USDT')["price"])

	# Return true if price is lower than buy limit, false otherwise
	def checkBuyLimit(self):
		self.updateUsdtPairValue()
		return self.usdtPairPrice < self.buyLimit

	# Return true if price is higher than sell limit, false otherwise
	def checkSellLimit(self):
		self.updateUsdtPairValue()
		return self.usdtPairPrice > self.sellLimit

def getStrategy():
	with open("strategy.json") as strategy_file:
		strat = json.load(strategy_file)
	
	strategy = Strategy(strat["frequency"])
	for asset in strat["assets"]:
		newTargetAsset = TargetAsset(asset)
		strategy.targetAssets.append(newTargetAsset)

	return strategy

def sendMail(text):
	with open("comm.json") as comm_file:
		mailComm = json.load(comm_file)["mail"]

	yagmail.register(mailComm["address"], mailComm["appPwd"])

	yag = yagmail.SMTP(mailComm["address"])
	yag.send(
        to=mailComm["address"],
        subject="Crypto bot",
        contents=text
    )

if __name__ == "__main__":
	myPortfolio = getPortfolio()
	print("Portfolio value (USDT): " + str(myPortfolio.usdtValue)+"\n")

	while True:
		alertText = ""
		print(time.time())
		myStrategy = getStrategy()
		print("Freq: " + str(myStrategy.frequency)+"\n")
		for target in myStrategy.targetAssets:
			buy = target.checkBuyLimit()
			sell = target.checkSellLimit()
			print(target.ticker)
			print("Buy if lower than " + str(target.buyLimit))
			print("Buy if higher than " + str(target.sellLimit))
			print("Current price (USDT): " + str(target.usdtPairPrice))
			print("Buy: " + str(buy))
			print("Sell: " + str(sell)+"\n")

			if buy :
				alertText += "Alert for {0} lower than {1} USDT\nCurrent price : {2} USDT \nStrategy: BUY \n\n".format(target.ticker, str(target.buyLimit), str(target.usdtPairPrice))
		
			if sell :
				alertText += "Alert for {0} higher than {1} USDT\nCurrent price : {2} USDT \nStrategy: SELL \n\n".format(target.ticker, str(target.sellLimit), str(target.usdtPairPrice))
		
		if alertText != "":
			sendMail(alertText)

		time.sleep(myStrategy.frequency)
