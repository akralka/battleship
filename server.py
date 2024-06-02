import socket
import threading
import signal
import sys

# TODO - trzeba dodac obsługe sygnałów na wyjscie z programu (poprawić to co jest)
# TODO - obsługę dołączenia większej liczby użytkowników niż 2
# TODO - jakies procesy się otwoerają i nie konczą??
# TODO - programy mają się zamknąć jak ktoś wygra 
''' TODO - Serwer powinien działać w trybie „demona” z logowaniem do plików systemowych. 
W programach, tam gdzie to jest wskazane należy użyć funkcji do przekształcania nazw na adresy (API do DNS).'''

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 3500
MAX_CLIENTS = 2

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

def validate_ships_position(board, ship_length, start, end):
    start_row, start_col = start
    end_row, end_col = end

    if start_row == end_row:  # Poziomo
        if abs(start_col - end_col) + 1 != ship_length:
            return f"[ERROR]: Statek ma długość {ship_length}."
        for col in range(min(start_col, end_col), max(start_col, end_col) + 1):
            if board[start_row][col] != '_':
                return "[ERROR]: Pole jest już zajęte."
    elif start_col == end_col:  # Pionowo
        if abs(start_row - end_row) + 1 != ship_length:
            return f"[ERROR]: Statek ma długość {ship_length}."
        for row in range(min(start_row, end_row), max(start_row, end_row) + 1):
            if board[row][start_col] != '_':
                return "[ERROR]: Pole jest już zajęte."
    else:
        return "[ERROR]: Statek musi być umieszczony w jednej linii."

    return None

def place_ship(board, start, end, ship_length, ship_name, ships):
    start_row, start_col = start
    end_row, end_col = end

    ship_positions = []
#   =======================================
#   Jesli statek jest:              "O"
#   Jesli statek jest trafiony:     "X"
#   Jesli statku nie ma:            "_"
#   Jesli pudło:                    "~"
#   =======================================

    if start_row == end_row:
        for col in range(min(start_col, end_col), max(start_col, end_col) + 1):
            board[start_row][col] = 'O'
            ship_positions.append((start_row, col))
    elif start_col == end_col:
        for row in range(min(start_row, end_row), max(start_row, end_row) + 1):
            board[row][start_col] = 'O'
            ship_positions.append((row, start_col))

    ships[ship_name] = ship_positions  # [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)] 

# Pozycja -> współrzędne tablicy:
# Np: A1 -> (0,0) bo zwraca nam 0-9 dla kolumn i dla wierszy
# A jesli nie miesci sie w zakresie to zwraca None
def parse_position(position):
    try:
        row = ord(position[0].upper()) - ord('A')  # Konwersja wiersza (zmiana z ASCII)
        col = int(position[1:]) - 1  # Konwersja kolumny
        if row < 0 or row > 9 or col < 0 or col > 9:  # Sprawdzenie zakresu (0,9)
            raise ValueError
        return row, col  # Zwrócenie współrzędnych (0,0)
    except:
        return None  # Niepoprawna pozycja

def display_board(board, to_string=False): 
    header = "  " + " ".join(str(i + 1) for i in range(10)) #  1 2 3 4 5 6 7 8 9
    rows = ""
    for i, row in enumerate(board): # enumerate to (0, 1-el z tablicy)
        rows += chr(ord('A') + i) + " " + " ".join(row) + "\n"  # A _ _ _ _ _ _ _ _ _ _

    board_string = header + "\n" + rows 

    if to_string:
        return board_string  # Zwraca jako string
    else:
        print(board_string)  # Drukuje planszę

def is_ship_sunk(ship_positions, board):
    return all(board[row][col] == 'X' for row, col in ship_positions)

def handle_client(client_socket, addr, client_id):
    global turn
    print(f"[INFO] Klient {addr} dołączył do gry.")

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
                    position = client_socket.recv(1024).decode().strip()
                    start = parse_position(position)
                    if start is None:
                        client_socket.send("[ERROR] Można używać tylko formatu {A-J}{1-10}.\n".encode())
                        continue
                    end = start
                else:
                    client_socket.send(f"[INFO] Umieść {ship_name} statek na planszy:\n       Podaj jego początek i koniec (np. B2 B6): ".encode())
                    positions = client_socket.recv(1024).decode().strip().split()
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

        print(f"[INFO] {addr} ukończył ustawianie statków.")
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
            position = client_socket.recv(1024).decode().strip()
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
                break

            with turn_lock:
                turn = opponent_id  
                waiting_message = True  
                turn_lock.notify_all()  # Info dla przeciwnika o jego turze

    except Exception as e:
        print(f"[INFO] {addr} zakończył rozgrywkę. {e}")
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
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen()
        print(f"[INFO] Serwer nasłuchuje na {SERVER_HOST}:{SERVER_PORT}")

        client_id = 0
        while True:
            try:
                client_socket, addr = server_socket.accept()
                # tutaj do poprawy:
                if len(clients) >= MAX_CLIENTS:
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
