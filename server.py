import socket
import threading
import signal
import sys
import logging
from gameLogic import validate_ships_position, place_ship, parse_position, display_board, is_ship_sunk
 
logging.basicConfig(filename='server.log', level=logging.INFO)

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 3501
MAX_CLIENTS = 2

MULTICAST_GROUP = '224.0.0.1'
MULTICAST_PORT = 5007

clients = []
player_boards = []
ships_info = [{}, {}]
turn = 0  #  (0 - player 1, 1 - player 2)
turn_lock = threading.Condition()  # Lock for changing turns

# CTRL+C
def signal_handler(*args):
    for client_socket in clients:
        try:
            client_socket.send("The server has ended the game.".encode())
            client_socket.close()
        except:
            pass
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)  # Signal handling setup
signal.signal(signal.SIGHUP, signal.SIG_IGN)  # DAEMON - works after teriminal is closed

def multicast_listener():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as multicast_socket:
        multicast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        multicast_socket.bind((MULTICAST_GROUP, MULTICAST_PORT))
        mreq = socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton(SERVER_HOST)
        multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        while True:
            data, addr = multicast_socket.recvfrom(1024)
            if data.decode() == 'DISCOVER_SERVER':
                multicast_socket.sendto(f'Server:{SERVER_HOST}:{SERVER_PORT}'.encode(), addr)


def handle_client(client_socket, addr, client_id):
    global turn
    logging.info(f"[INFO] Client {addr} has joined the game.")

    try:
        client_socket.send("=========== WELCOME TO THE BATTLESHIP ===========\n\n".encode())
        client_socket.send("[INFO] Position your ships.\n".encode())

        board = [['_'] * 10 for _ in range(10)]  # Empty board [['_', '_', '_', '_', '_', '_', '_', '_', '_', '_'], ['_', ...]] x 10
        ships = {}  # {'5-seater': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)], '3-seater'....}
        ships_info[client_id] = ships   
        ship_definitions = [(5, "5-seater"), (3, "3-seater"), (1, "1-seater")]

        # Ships deployment
        for ship_length, ship_name in ship_definitions:
            while True:
                if ship_length == 1:
                    client_socket.send(f"[INFO] Place {ship_name} ship on the board:\n       Specify its position (e.g., H4):".encode())
                    try:
                        position = client_socket.recv(1024).decode().strip()
                    except:
                        continue
                    start = parse_position(position)
                    if start is None:
                        client_socket.send("[ERROR] Only the {A-J}{1-10} format can be used.\n".encode())
                        continue
                    end = start
                else:
                    client_socket.send(f"[INFO] Place {ship_name} ship on the board:\n       Enter its beginning and end (e.g. B2 B6): ".encode())
                    try:
                        positions = client_socket.recv(1024).decode().strip().split()
                    except:
                        continue
                    if len(positions) != 2:
                        client_socket.send("[ERROR] Invalid format. Try again.\n".encode())
                        continue
                    start = parse_position(positions[0])
                    end = parse_position(positions[1])
                    if start is None or end is None:
                        client_socket.send("[ERROR] Only the {A-J}{1-10} format can be used.\n".encode())
                        continue

                error_message = validate_ships_position(board, ship_length, start, end)
                if error_message:
                    client_socket.send(error_message.encode() + b"\n")    #b"\n" bytes, not a string
                    continue

                place_ship(board, start, end, ship_name, ships)  
                # print(ships[ship_name])                # [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)]
                # print(ships_info[client_id])           # {'5-seater': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)], '3-seater': [(0, 5), (0, 6), (0, 7)], '1-seater': [(7, 3)]}
                break

        logging.info(f"[INFO] {addr} completed positioning the ships.")

        player_boards.append(board)

        if len(player_boards) < MAX_CLIENTS:
            client_socket.send("[INFO] Waiting for the opponent.\n".encode())
            while len(player_boards) < MAX_CLIENTS:
                pass

        client_socket.send("========The game starts.=======\n\n".encode())

        opponent_board_display = [['_'] * 10 for _ in range(10)] 

        # The main game loop
        waiting_message = True
        while True:
            with turn_lock:  # Blockade - whose turn
                while client_id != turn:  # Waiting for your turn
                    if waiting_message:
                        client_socket.send("[INFO] Waiting for the opponent's move.\n".encode())
                        waiting_message = False 
                    turn_lock.wait()  # Waiting for the signal to change turn

            client_socket.send("YOUR MOVE! Enter your shooting position (e.g. A1):\n".encode())
            client_socket.send(display_board(opponent_board_display).encode())
            try: 
                position = client_socket.recv(1024).decode().strip()
            except:
                logging.info("The client has finished the game.")
                continue
            target = parse_position(position)
            if target is None:
                client_socket.send("[ERROR] Only A-J and 1-10 can be used.\n".encode())
                continue
            target_row, target_col = target
            opponent_id = 1 - client_id
            opponent_board = player_boards[opponent_id]

            if opponent_board[target_row][target_col] in ['X', '~']: 
                client_socket.send("[ERROR] This field has already been checked. Try again.\n".encode())
                continue

            if opponent_board[target_row][target_col] == 'O':  # That is, when we hit the ship
                opponent_board[target_row][target_col] = 'X'
                opponent_board_display[target_row][target_col] = 'X'
                player_boards[opponent_id] = opponent_board
                response = f"HIT: {position}\n"
                for ship_name, ship_positions in ships_info[opponent_id].items():  # {'5-seater': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)], ...
                    if (target_row, target_col) in ship_positions:                 # ('5-seater', [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)])
                        if is_ship_sunk(ship_positions, opponent_board):
                            response += f"SUNK: {ship_name}\n"
                            client_socket.send(response.encode())
                            clients[opponent_id].send(f"THE OPPONENT HIT: {position}\nSUNK: {ship_name}\n".encode())
                            break
                else: # for else:  if "break" ^ then "else" will not be executed
                    client_socket.send(response.encode())
                    clients[opponent_id].send(f"THE OPPONENT HIT: {position}\n".encode())
            else:
                opponent_board[target_row][target_col] = '~'  # miss
                opponent_board_display[target_row][target_col] = '~'
                response = f"MISS: {position}\n"
                client_socket.send(response.encode())

            # Checking whether the opponent has lost
            if all(cell != 'O' for row in opponent_board for cell in row):
                client_socket.send("==============END OF THE GAME!==============\n                  You won!".encode())
                clients[opponent_id].send("==============GAME OVER!==============\n         Your opponent has won!".encode())
                client_socket.close()
                clients[opponent_id].close()
                logging.info(f"[INFO] End of the game. {addr} won.")       
                break

            with turn_lock:
                turn = opponent_id  
                waiting_message = True  
                turn_lock.notify_all()  # Info for the opponent about his turn

    except Exception as e:
        logging.error(f"[ERROR] Handling client {addr} finished with: {e}")
        other_client_id = 1 - client_id
        if other_client_id < len(clients):
            try:
                clients[other_client_id].send(f"Player {addr} has finished the game.\n".encode())
                clients[other_client_id].close()
            except:
                pass
        client_socket.close()

def server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1) # (can be) separately on other addresses on the same port
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT,1) # bind (when TIME/CLOSE_WAIT)
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen()
        logging.info(f"[INFO] Server running on {SERVER_HOST}:{SERVER_PORT}.")

        threading.Thread(target=multicast_listener, daemon=True).start()

        client_id = 0
        while True:
            try:
                client_socket, addr = server_socket.accept()
                if len(clients) >= MAX_CLIENTS:
                    logging.info(f"[INFO] Attempt to connect from the address:{addr}")
                    client_socket.send("[INFO] The server is full. Please try again later.\n".encode())
                    client_socket.close()
                    continue
                clients.append(client_socket)
                client_thread = threading.Thread(target=handle_client, args=(client_socket, addr, client_id))  # Create a thread for the client
                client_thread.start()  
                client_id += 1  # Increasing the customer ID
            except Exception as e:
                print(f"[ERROR] {e}")
                break

if __name__ == "__main__":
    server()
