# このファイルを「cateye_speed_settings.py」という名前でコピーして利用すること
# 通常は「ホイール周長」「速度のしきい値」「Fire TV Stick のMACアドレス」を適切に変更するだけで大丈夫なはず

# サイクルコンピューターのサービスUUID（Bluetooth SIGで決まっているらしい）
CSC_SERVICE_UUID = '00001816-0000-1000-8000-00805f9b34fb'
# スピード、ケイデンスのキャラクタリスティックUUID（Bluetooth SIGで決まっているらしい）
WHEEL_CHAR_UUID = '00002a5b-0000-1000-8000-00805f9b34fb'

# ホイール周長
WHEEL_CIRCUMFERENCE = 1590

# 速度のしきい値（これ以上であれば再生、以下であれば停止）
SPEED_THRESHOLD = 10.5

# Fire TV Stick のMACアドレス
FIRE_STICK_TV_MAC_ADDRESS = 'Fire Sticke TV のMACアドレス'
