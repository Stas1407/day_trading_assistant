
def handle_console_interface(q):
    print("[+] Started reading from queue")
    while True:
        state = q.get()
        print("Handling queue process: ", state)
