from support_resistance import SupportResistance
from banner import print_banner

print_banner()
s = SupportResistance("XBIO", interval="1d", period="1y", interval_chart="5m", period_chart="1d")
s.run()
