from support_resistance import SupportResistance
from banner import print_banner
from queue import Queue

print_banner()

q = Queue()

s = SupportResistance("XBIO", interval="1d", period="1y", interval_chart="5m", period_chart="1d", queue=q)
s.start()

try:
    while True:
        state = q.get()
        print("Main thread: ", state)
        q.task_done()
except KeyboardInterrupt:
    print("Exiting")
    s.stop()

print()
input("Press enter to exit")

# TODO: Process more stocks at once, another thread handling charts displaying
