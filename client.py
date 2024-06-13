import socket  
import threading  
import signal 
import sys  
import logging  

SERVER_HOST = '127.0.0.1'  
SERVER_PORT = 3501

MULTICAST_GROUP = '224.0.0.1'
MULTICAST_PORT = 5007

# Obsługa logów
logging.basicConfig(filename='client.log', level=logging.INFO)
client_socket = None

# Obsługa CTRL+C
def signal_handler(*args):
    global client_socket
    logging.info("[INFO] Zakończyłeś rozgrywkę.") 
    client_socket.close()  
    sys.exit(0) 

# Ustawienie obsługi sygnału SIGINT (CTRL+C) za pomocą funkcji signal_handler
signal.signal(signal.SIGINT, signal_handler)

def discover_server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as multicast_socket:
        multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        message = 'DISCOVER_SERVER'.encode()
        multicast_socket.sendto(message, (MULTICAST_GROUP, MULTICAST_PORT))

        while True:
            try:
                data, _ = multicast_socket.recvfrom(1024)
                if data.decode().startswith('Serwer'):
                    _, server_ip, server_port = data.decode().split(':')
                    return server_ip, int(server_port)
            except socket.timeout:
                logging.error("Nie znaleziono serwera multicast. Spróbuj ponownie.")
                sys.exit(0)

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
            logging.error("Utracono połączenie z serwerem.")
            sys.exit(0)

def client():
    global client_socket 
    server_ip, server_port = discover_server()
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    client_socket.connect((server_ip, server_port))
    logging.info(f"[INFO] Połączono z serwerem {server_ip}:{server_port}") 
    
    # Wątek do odbierania wiadomości od serwera
    receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
    receive_thread.start()
    
    while True:
        try:
            message = input() 
            client_socket.send(message.encode())
        except KeyboardInterrupt:  # CTRL+C
            # print("\n[INFO] Klient zakończył rozgrywkę.")
            logging.info("\n[INFO] Klient zakończył rozgrywkę.") 
            client_socket.close()  
            sys.exit(0) 
        except Exception as e:
            logging.error(f"Error: {e}") 

if __name__ == "__main__":
    client()
