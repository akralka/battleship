def validate_ships_position(board, ship_length, start, end):
    start_row, start_col = start
    end_row, end_col = end

    if start_row == end_row:  # horizontally
        if abs(start_col - end_col) + 1 != ship_length:
            return f"[ERROR]: The ship has a length {ship_length}."
        for col in range(min(start_col, end_col), max(start_col, end_col) + 1):
            if board[start_row][col] != '_':
                return "[ERROR]: The field is already occupied."
    elif start_col == end_col:  # vertically
        if abs(start_row - end_row) + 1 != ship_length:
            return f"[ERROR]: The ship has a length {ship_length}."
        for row in range(min(start_row, end_row), max(start_row, end_row) + 1):
            if board[row][start_col] != '_':
                return "[ERROR]: The field is already occupied."
    else:
        return "[ERROR]: The ship must be placed in one line."

    return None

def place_ship(board, start, end, ship_name, ships):
    start_row, start_col = start
    end_row, end_col = end

    ship_positions = []
#   =======================================
#   If the ship exists:             "O"
#   If the ship is hit:             "X"
#   If there is no ship:            "_"
#   If miss:                        "~"
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

def parse_position(position):
# Position -> array coordinates:
# For example: A1 -> (0,0) because it returns 0-9 for columns and rows
# And if it does not fit in the range, it returns None
    try:
        row = ord(position[0].upper()) - ord('A')  # Line conversion (change from ASCII)
        col = int(position[1:]) - 1  # Column conversion
        if row < 0 or row > 9 or col < 0 or col > 9: 
            raise ValueError
        return row, col  # (0,0)
    except:
        return None  # Incorrect position

def display_board(board): 
    header = "  " + " ".join(str(i + 1) for i in range(10)) #  1 2 3 4 5 6 7 8 9
    rows = ""
    for i, row in enumerate(board): # enumerate: (0, 1st item from the array)
        rows += chr(ord('A') + i) + " " + " ".join(row) + "\n"  # A _ _ _ _ _ _ _ _ _ _

    board_string = header + "\n" + rows 


    return board_string  # Returns as a string


def is_ship_sunk(ship_positions, board):
    return all(board[row][col] == 'X' for row, col in ship_positions)
