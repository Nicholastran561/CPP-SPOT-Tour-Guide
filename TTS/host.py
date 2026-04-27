#!/usr/bin/env python3
import socket
import time
import threading

HOST = "0.0.0.0"
PORT = 852

def send_msg(conn):
    """Sends every 3 seconds"""
    while True:
        msg = input("Enter text for SPOT to speak: ")

        if msg.lower() in ['quit', 'exit', 'bye']:
            break
        if msg:
            conn.sendall(msg.encode() + b"\n")
        time.sleep(3)

print(f"Single connection: {PORT}")
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    
    conn, addr = s.accept()  # one connection
    print(f":white_check_mark: Connected: {addr}")
    
    # background loop
    threading.Thread(target=send_msg, args=(conn,), daemon=True).start()
    
    # Main echo loop
    with conn:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            print(f" {data.decode().strip()}")
            conn.sendall(data)