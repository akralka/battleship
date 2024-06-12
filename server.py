import socket
import threading
import signal
import sys
import logging
from gameLogic import shutdown_server, validate_ships_position, place_ship, parse_position, display_board, is_ship_sunk
 
logging.basicConfig(filename='server.log', level=logging.INFO)

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 3501
MAX_CLIENTS = 2

MULTICAST_GROUP = '224.0.0.1'
MULTICAST_PORT = 5007

clients = []
player_boards = []
ships_info = [{}, {}]
turn = 0  # Czyja tura (0 - gracz 1, 1 - gracz 2)
turn_lock = threading.Condition()  # Blokada dla zmiany tur

# Obsługa CTRL+C
def signal_handler(sig, frame):
    print("\n[INFO] Serwer zakończył rozgrywkę.")
    for client_socket in clients:
        try:
            client_socket.send("Serwer zakończył rozgrywkę".encode())
            client_socket.close()
        except:
            pass
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)  # Ustawienie obsługi sygnału
signal.signal(signal.SIGHUP, signal.SIG_IGN)  # DAEMON - jak zamkniemy terminal to działa

def multicast_listener():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as multicast_socket:
        multicast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        multicast_socket.bind((MULTICAST_GROUP, MULTICAST_PORT))
        mreq = socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton(SERVER_HOST)
        multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        while True:
            data, addr = multicast_socket.recvfrom(1024)
            if data.decode() == 'DISCOVER_SERVER':
                multicast_socket.sendto(f'Serwer:{SERVER_HOST}:{SERVER_PORT}'.encode(), addr)


def handle_client(client_socket, addr, client_id):
    global turn
    # print(f"[INFO] Klient {addr} dołączył do gry.")
    logging.info(f"[INFO] Klient {addr} dołączył do gry.")

    try:
        client_socket.send("================START================\n\n".encode())
        client_socket.send("[INFO] Ustaw swoje statki.\n".encode())

        board = [['_'] * 10 for _ in range(10)]  # Pusta plansza [['_', '_', '_', '_', '_', '_', '_', '_', '_', '_'], ['_', ...]] x 10
        ships = {}  # Informacje o statkach: {'5-miejscowy': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)], '3-miejscowy'....}
        ships_info[client_id] = ships   
        ship_definitions = [(5, "5-miejscowy"), (3, "3-miejscowy"), (1, "1-miejscowy")]

        # Rozmieszczenie statków
        for ship_length, ship_name in ship_definitions:
            while True:
                if ship_length == 1:
                    client_socket.send(f"[INFO] Umieść {ship_name} statek na planszy.\n       Podaj jego pozycję (np. H4):".encode())
                    try:
                        position = client_socket.recv(1024).decode().strip()
                    except:
                        continue
                    start = parse_position(position)
                    if start is None:
                        client_socket.send("[ERROR] Można używać tylko formatu {A-J}{1-10}.\n".encode())
                        continue
                    end = start
                else:
                    client_socket.send(f"[INFO] Umieść {ship_name} statek na planszy:\n       Podaj jego początek i koniec (np. B2 B6): ".encode())
                    try:
                        positions = client_socket.recv(1024).decode().strip().split()
                    except:
                        continue
                    if len(positions) != 2:
                        client_socket.send("[ERROR] Nieprawidłowy format. Spróbuj ponownie.\n".encode())
                        continue
                    start = parse_position(positions[0])
                    end = parse_position(positions[1])
                    if start is None or end is None:
                        client_socket.send("[ERROR] Można używać tylko formatu {A-J}{1-10}.\n".encode())
                        continue

                error_message = validate_ships_position(board, ship_length, start, end)
                if error_message:
                    client_socket.send(error_message.encode() + b"\n")    #b"\n" bo bytes, nie zwykły string
                    continue

                place_ship(board, start, end, ship_length, ship_name, ships)  
                # print(ships[ship_name])                # [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)]
                # print(ships_info[client_id])           # {'5-miejscowy': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)], '3-miejscowy': [(0, 5), (0, 6), (0, 7)], '1-miejscowy': [(7, 3)]}
                break

        # print(f"[INFO] {addr} ukończył ustawianie statków.")
        logging.info(f"[INFO] {addr} ukończył ustawianie statków.")

        player_boards.append(board)

        if len(player_boards) < MAX_CLIENTS:
            client_socket.send("[INFO] Oczekiwanie na drugiego gracza.\n".encode())
            while len(player_boards) < MAX_CLIENTS:
                pass

        client_socket.send("=====Gra rozpoczyna się.====\n\n".encode())

        opponent_board_display = [['_'] * 10 for _ in range(10)] 

        # Główna pętla gry
        waiting_message = True
        while True:
            with turn_lock:  # Blokada - czyja tura
                while client_id != turn:  # Czekanie na swoją turę
                    if waiting_message:
                        client_socket.send("[INFO] Oczekiwanie na ruch przeciwnika.\n".encode())
                        waiting_message = False 
                    turn_lock.wait()  # Czekanie na sygnał do zmiany tury

            client_socket.send("TWÓJ RUCH! Podaj pozycję do strzału (np. A1):\n".encode())
            client_socket.send(display_board(opponent_board_display, to_string=True).encode())
            try: 
                position = client_socket.recv(1024).decode().strip()
            except:
                # print("Klient zakończył grę.")
                logging.info("Klient zakończył grę.")
                continue
            target = parse_position(position)
            if target is None:
                client_socket.send("[ERROR] Można używać tylko A-J oraz 1-10.\n".encode())
                continue
            target_row, target_col = target
            opponent_id = 1 - client_id
            opponent_board = player_boards[opponent_id]

            if opponent_board[target_row][target_col] in ['X', '~']: 
                client_socket.send("[ERROR] To pole było już sprawdzane. Spróbuj ponownie.\n".encode())
                continue

            if opponent_board[target_row][target_col] == 'O':  # Czyli jak trafimy
                opponent_board[target_row][target_col] = 'X'
                opponent_board_display[target_row][target_col] = 'X'
                player_boards[opponent_id] = opponent_board
                response = f"TRAFIONY: {position}\n"
                for ship_name, ship_positions in ships_info[opponent_id].items():  # {'5-miejscowy': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)], ...
                    if (target_row, target_col) in ship_positions:                 # ('5-miejscowy', [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)])
                        if is_ship_sunk(ship_positions, opponent_board):
                            response += f"ZATOPIONY: {ship_name}\n"
                            client_socket.send(response.encode())
                            clients[opponent_id].send(f"PRZECIWNIK TRAFIŁ: {position}\nZATOPIONY: {ship_name}\n".encode())
                            break
                else: # for   else, bo jesli break ^ to else się nie wykona
                    client_socket.send(response.encode())
                    clients[opponent_id].send(f"PRZECIWNIK TRAFIŁ: {position}\n".encode())
            else:
                opponent_board[target_row][target_col] = '~'  # Pudło
                opponent_board_display[target_row][target_col] = '~'
                response = f"PUDŁO: {position}\n"
                client_socket.send(response.encode())

            # Czy przeciwnik przegrał
            if all(cell != 'O' for row in opponent_board for cell in row):
                client_socket.send("==============KONIEC GRY!==============\n              Wygrałeś!".encode())
                clients[opponent_id].send("==============KONIEC GRY!==============\n          Przeciwnik wygrał!".encode())
                client_socket.close()
                clients[opponent_id].close()
                logging.info(f"[INFO] Koniec gry. {addr} wygrał.")               
                shutdown_server()

            with turn_lock:
                turn = opponent_id  
                waiting_message = True  
                turn_lock.notify_all()  # Info dla przeciwnika o jego turze

    except Exception as e:
        print(f"[INFO] {addr} zakończył rozgrywkę. {e}")
        logging.error(f"Error handling client {addr}: {e}")
        other_client_id = 1 - client_id
        if other_client_id < len(clients):
            try:
                clients[other_client_id].send(f"Użytkownik {addr} zakończył rozgrywkę.\n".encode())
                clients[other_client_id].close()
            except:
                pass
        client_socket.close()

def server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1) # mozna osobno na innych adresach na tym samym porcie
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT,1) # mozna się bindowac jak TIME/CLOSE_WAIT
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen()
        logging.info(f"[INFO] Serwer uruchomiony na {SERVER_HOST}:{SERVER_PORT}.")
        # print(f"[INFO] Serwer nasłuchuje na {SERVER_HOST}:{SERVER_PORT}")

        threading.Thread(target=multicast_listener, daemon=True).start()

        client_id = 0
        while True:
            try:
                client_socket, addr = server_socket.accept()
                if len(clients) >= MAX_CLIENTS:
                    logging.info(f"[INFO] Próba połączenia z adresu: {addr}")
                    client_socket.send("[INFO] Serwer jest pełny. Spróbuj ponownie później.\n".encode())
                    client_socket.close()
                    continue
                clients.append(client_socket)
                client_thread = threading.Thread(target=handle_client, args=(client_socket, addr, client_id))  # Utworzenie wątku dla klienta
                client_thread.start()  # Uruchomienie wątku
                client_id += 1  # Zwiększenie ID klienta
            except Exception as e:
                print(f"[ERROR] {e}")
                break

if __name__ == "__main__":
    server()
