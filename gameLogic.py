def shutdown_server():
    for client_socket in clients:
        try:
            client_socket.send("Serwer zakończył rozgrywkę".encode())
            client_socket.close()
        except:
            pass
    sys.exit(0)

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
