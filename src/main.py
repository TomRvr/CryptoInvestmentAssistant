import json
import time
import yagmail
from binance.client import Client
import discord
import asyncio



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

with open("discord.json") as discord_conf_file:
	discord_conf = json.load(discord_conf_file)

class Bot(discord.Client):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.alertText = ""
		self.myStrategy = getStrategy()
		print("Freq: " + str(self.myStrategy.frequency)+"\n")

		# create the background task and run it in the background
		self.bg_task = self.loop.create_task(self.my_background_task())

	async def on_ready(self):
		print('Logged in as')
		print(self.user.name)
		print(self.user.id)
		print('------')

	async def my_background_task(self):
		await self.wait_until_ready()
		channel = self.get_channel(discord_conf["CHANNEL"]) # channel ID goes here
		while not self.is_closed():
			self.alertText = ""
			for target in self.myStrategy.targetAssets:
				buy = target.checkBuyLimit()
				sell = target.checkSellLimit()

				if buy :
					self.alertText += "Alert for {0} lower than {1} USDT\nCurrent price : {2} USDT \nStrategy: BUY \n\n".format(target.ticker, str(target.buyLimit), str(target.usdtPairPrice))
		
				if sell :
					self.alertText += "Alert for {0} higher than {1} USDT\nCurrent price : {2} USDT \nStrategy: SELL \n\n".format(target.ticker, str(target.sellLimit), str(target.usdtPairPrice))
		
			if self.alertText != "":
				await channel.send(self.alertText)
			
			await asyncio.sleep(self.myStrategy.frequency) # task runs every 60 seconds


discordClient = Bot()

@discordClient.event
async def on_message(message):
    #if message.author == client.user:
    #    return

	if message.content.startswith('$PRTFL'):
		myPortfolio = getPortfolio()
		print("Portfolio value (USDT): " + str(myPortfolio.usdtValue)+"\n")
		await message.channel.send("Portfolio value (USDT): " + str(myPortfolio.usdtValue))

if __name__ == "__main__":
	discordClient.run(discord_conf["TOKEN"])
