import socket  
import threading  
import signal 
import sys  

SERVER_HOST = '127.0.0.1'  
SERVER_PORT = 3500  

# Obsługa CTRL+C
def signal_handler(sig, frame):
    print("\n[INFO] Zakończyłeś rozgrywkę.")  
    client_socket.close()  
    sys.exit(0) 

# Ustawienie obsługi sygnału SIGINT (CTRL+C) za pomocą funkcji signal_handler
signal.signal(signal.SIGINT, signal_handler)

def receive_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode()
            if not message:
                break
            print(message) 
            if "Wygrałeś!" in message or "Przeciwnik wygrał!" in message: 
                client_socket.close() 
                sys.exit(0) 
        except:
            break

def client():
    global client_socket 
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    client_socket.connect((SERVER_HOST, SERVER_PORT))
    print(f"[INFO] Połączono z serwerem {SERVER_HOST}:{SERVER_PORT}") 
    
    # Wątek do odbierania wiadomości od serwera
    receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
    receive_thread.start()
    
    while True:
        try:
            message = input() 
            client_socket.send(message.encode())
        except KeyboardInterrupt:  # CTRL+C
            print("\n[INFO] Klient zakończył rozgrywkę.") 
            client_socket.close()  
            sys.exit(0)  

if __name__ == "__main__":
    client()
