import socket  
import threading  
import signal 
import sys  
import logging  

MULTICAST_GROUP = '224.0.0.1'
MULTICAST_PORT = 5007

# Logs
logging.basicConfig(filename='client.log', level=logging.INFO)
client_socket = None

# CTRL+C
def signal_handler(*args):  # args: sig & frame
    global client_socket
    if client_socket:
        logging.info(f"[INFO] One of the clients ended the game.")
        client_socket.close()  
    sys.exit(0) 

# Handling SIGINT (CTRL+C) signal using the signal_handler function
signal.signal(signal.SIGINT, signal_handler)

def discover_server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as multicast_socket:
        multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        message = 'DISCOVER_SERVER'.encode()
        multicast_socket.sendto(message, (MULTICAST_GROUP, MULTICAST_PORT))
        multicast_socket.settimeout(5) 

        while True:
            try:
                data, _ = multicast_socket.recvfrom(1024)
                if data.decode().startswith('Server'):
                    _, server_ip, server_port = data.decode().split(':')
                    return server_ip, int(server_port)
            except socket.timeout:
                logging.error("Multicast server not found. Try again.")
                sys.exit(0)

def receive_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode()
            if not message:
                break
            print(message) 
            if "You won!" in message or "Your opponent has won!" in message: 
                client_socket.close() 
                sys.exit(0) 
        except:
            logging.error("Connection to the server was lost.")
            sys.exit(0)

def client():
    global client_socket 
    try:
        server_ip, server_port = discover_server()
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        client_socket.connect((server_ip, server_port))
        logging.info(f"[INFO] Connected to the server {server_ip}:{server_port}") 
        
        #A thread for receiving messages from the server
        receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
        receive_thread.start()
        
        while True:
            try:
                message = input() 
                client_socket.send(message.encode())
            except KeyboardInterrupt:  # CTRL+C
                logging.info("\n[INFO] The client has finished the game.") 
                client_socket.close()  
                sys.exit(0) 
            except Exception as e:
                logging.error(f"Error: {e}") 
    except Exception as e:
        logging.error(f"Error: {e}")

if __name__ == "__main__":
    client()
