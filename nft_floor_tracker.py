import requests
import time
from datetime import datetime
import threading

class MagicEdenNFTTracker:
    def __init__(self):
        self.me_api = "https://api-mainnet.magiceden.dev/v2/ord"
        self.coingecko_api = "https://api.coingecko.com/api/v3"
        self.api_key = ""  # 填入API Key
        self.collection_data = {}
        self.btc_price = None
        self.last_btc_update = 0

    def get_btc_price(self):
        current_time = time.time()
        if current_time - self.last_btc_update >= 60:
            try:
                response = requests.get(f"{self.coingecko_api}/simple/price?ids=bitcoin&vs_currencies=usd")
                data = response.json()
                self.btc_price = float(data['bitcoin']['usd'])
                self.last_btc_update = current_time
            except Exception as e:
                print(f"获取BTC价格失败: {e}")
        return self.btc_price

    def get_collection_floor_price(self, collection_symbol):
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            url = f"{self.me_api}/bitcoin/collections/{collection_symbol}"
            print(f"正在请求: {url}")
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'floorPrice' in data:
                    return float(data['floorPrice']) / 1e8
                else:
                    print(f"无地板价数据: {data}")
                    return None
            else:
                print(f"API请求失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            print(f"获取 {collection_symbol} 地板价失败: {e}")
            return None

    def update_collection_data(self, collection_symbol):
        current_floor = self.get_collection_floor_price(collection_symbol)
        if current_floor is not None:
            if collection_symbol not in self.collection_data:
                self.collection_data[collection_symbol] = []
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.collection_data[collection_symbol].append((timestamp, current_floor))
            return current_floor
        return None

    def calculate_increase(self, collection_symbol, period='daily'):
        if collection_symbol not in self.collection_data or len(self.collection_data[collection_symbol]) < 2:
            return None
        if period == 'daily':
            now = datetime.now()
            for i in range(len(self.collection_data[collection_symbol]) - 2, -1, -1):
                prev_time, prev_price = self.collection_data[collection_symbol][i]
                prev_time = datetime.strptime(prev_time, "%Y-%m-%d %H:%M:%S")
                if (now - prev_time).days >= 1:
                    latest_price = self.collection_data[collection_symbol][-1][1]
                    return ((latest_price - prev_price) / prev_price) * 100
            return None
        else:
            latest = self.collection_data[collection_symbol][-1][1]
            previous = self.collection_data[collection_symbol][-2][1]
            return ((latest - previous) / previous) * 100 if previous else None

    def track_cents_floor(self, interval=10):
        collection_symbol = "cents"
        print(f"开始跟踪Cents系列地板价，每{interval}秒更新一次")
        while True:
            self.get_btc_price()
            current_floor = self.update_collection_data(collection_symbol)
            daily_increase = self.calculate_increase(collection_symbol, 'daily')
            recent_increase = self.calculate_increase(collection_symbol, 'recent')
            if current_floor is not None:
                usd_floor = current_floor * self.btc_price if self.btc_price else None
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n{timestamp}")
                print(f"Cents地板价: {current_floor:.6f} BTC (~${usd_floor:.2f} USD)")
                if daily_increase is not None:
                    print(f"每日涨幅: {daily_increase:.2f}%")
                if recent_increase is not None:
                    print(f"最近{interval}秒涨幅: {recent_increase:.2f}%")
            time.sleep(interval)

    def search_nft_floor(self, collection_symbol):
        self.get_btc_price()
        floor_price = self.get_collection_floor_price(collection_symbol)
        if floor_price is not None:
            usd_floor = floor_price * self.btc_price if self.btc_price else None
            print(f"{collection_symbol} 当前地板价: {floor_price:.6f} BTC (~${usd_floor:.2f} USD)")
            return floor_price
        return None

if __name__ == "__main__":
    tracker = MagicEdenNFTTracker()
    cents_thread = threading.Thread(target=tracker.track_cents_floor, args=(10,))
    cents_thread.daemon = True
    cents_thread.start()
    while True:
        search_input = input("\n输入要搜索的NFT系列标识符（或输入'exit'退出）: ")
        if search_input.lower() == 'exit':
            break
        tracker.search_nft_floor(search_input)