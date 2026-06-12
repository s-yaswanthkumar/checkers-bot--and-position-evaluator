import copy

# Board piece constants
EMPTY = 0
RED_PAWN = 1
RED_KING = 2
WHITE_PAWN = -1
WHITE_KING = -2

# Directions for movement
# Diagonal offsets: (row_offset, col_offset)
DIRECTIONS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

def get_initial_board():
    """Returns the standard starting Checkers board layout (8x8 grid)."""
    board = [[EMPTY for _ in range(8)] for _ in range(8)]
    
    # Red pawns start in rows 0, 1, 2 on dark squares (r + c) % 2 == 1
    for r in range(3):
        for c in range(8):
            if (r + c) % 2 == 1:
                board[r][c] = RED_PAWN
                
    # White pawns start in rows 5, 6, 7 on dark squares
    for r in range(5, 8):
        for c in range(8):
            if (r + c) % 2 == 1:
                board[r][c] = WHITE_PAWN
                
    return board

def copy_board(board):
    """Creates a fast copy of the board grid."""
    return [row[:] for row in board]

def get_piece_color(piece):
    """Returns 'Red', 'White', or None based on the piece value."""
    if piece > 0:
        return 'Red'
    elif piece < 0:
        return 'White'
    return None

def is_king(piece):
    """Returns True if the piece is a King."""
    return abs(piece) == 2

def get_opponent(player):
    """Returns the opposing player name."""
    return 'White' if player == 'Red' else 'Red'

def get_jumps_for_piece(board, r, c, player, current_path=None, visited_captured=None):
    """
    Recursively finds all complete jump paths starting from (r, c) for the given player.
    A jump path is represented as a list of coordinates: [(from_r, from_c), (land1_r, land1_c), ...]
    """
    if current_path is None:
        current_path = [(r, c)]
    if visited_captured is None:
        visited_captured = set()
        
    piece = board[r][c]
    if piece == EMPTY:
        return []
        
    # Determine valid direction offsets for jumps
    if is_king(piece):
        dirs = DIRECTIONS
    else:
        # Pawns only move forward: Red moves down (rows +1), White moves up (rows -1)
        dirs = [(1, -1), (1, 1)] if player == 'Red' else [(-1, -1), (-1, 1)]
        
    jump_paths = []
    
    for dr, dc in dirs:
        mid_r, mid_c = r + dr, c + dc
        land_r, land_c = r + 2 * dr, c + 2 * dc
        
        # Check boundary bounds
        if not (0 <= land_r < 8 and 0 <= land_c < 8):
            continue
            
        mid_piece = board[mid_r][mid_c]
        land_piece = board[land_r][land_c]
        
        # Must jump over an opponent piece, and the landing square must be empty
        is_opponent_piece = False
        if player == 'Red' and mid_piece < 0:
            is_opponent_piece = True
        elif player == 'White' and mid_piece > 0:
            is_opponent_piece = True
            
        if is_opponent_piece and land_piece == EMPTY and (mid_r, mid_c) not in visited_captured:
            # Simulate the jump step
            board_copy = copy_board(board)
            new_piece = piece
            
            # Check if this step crowns the pawn
            is_crowned = False
            if player == 'Red' and land_r == 7 and piece == RED_PAWN:
                new_piece = RED_KING
                is_crowned = True
            elif player == 'White' and land_r == 0 and piece == WHITE_PAWN:
                new_piece = WHITE_KING
                is_crowned = True
                
            # Perform intermediate board updates
            board_copy[r][c] = EMPTY
            board_copy[mid_r][mid_c] = EMPTY
            board_copy[land_r][land_c] = new_piece
            
            new_path = current_path + [(land_r, land_c)]
            new_visited = visited_captured | {(mid_r, mid_c)}
            
            # If the piece got crowned, the turn ends immediately
            if is_crowned:
                jump_paths.append(new_path)
            else:
                # Recursively look for subsequent jumps
                further_jumps = get_jumps_for_piece(board_copy, land_r, land_c, player, new_path, new_visited)
                if further_jumps:
                    jump_paths.extend(further_jumps)
                else:
                    # No more jumps available, this is a complete path
                    jump_paths.append(new_path)
                    
    return jump_paths

def get_all_jumps(board, player):
    """Finds all complete jump moves available for the player on the board."""
    all_jumps = []
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece != EMPTY and get_piece_color(piece) == player:
                piece_jumps = get_jumps_for_piece(board, r, c, player)
                for path in piece_jumps:
                    if len(path) > 1:
                        all_jumps.append(path)
    return all_jumps

def get_slides_for_piece(board, r, c, player):
    """Finds all standard single-square diagonal moves for a piece at (r, c)."""
    piece = board[r][c]
    if piece == EMPTY:
        return []
        
    if is_king(piece):
        dirs = DIRECTIONS
    else:
        dirs = [(1, -1), (1, 1)] if player == 'Red' else [(-1, -1), (-1, 1)]
        
    slides = []
    for dr, dc in dirs:
        tgt_r, tgt_c = r + dr, c + dc
        if 0 <= tgt_r < 8 and 0 <= tgt_c < 8:
            if board[tgt_r][tgt_c] == EMPTY:
                slides.append([(r, c), (tgt_r, tgt_c)])
    return slides

def get_all_slides(board, player):
    """Finds all standard sliding moves available for the player on the board."""
    all_slides = []
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece != EMPTY and get_piece_color(piece) == player:
                all_slides.extend(get_slides_for_piece(board, r, c, player))
    return all_slides

def get_valid_moves(board, player):
    """
    Returns all valid moves for the player.
    Enforces the mandatory jump (capture) rule: if any jump is possible, 
    only jumps are returned. Otherwise, standard sliding moves are returned.
    """
    jumps = get_all_jumps(board, player)
    if jumps:
        return jumps
    return get_all_slides(board, player)

def execute_move(board, move, player):
    """
    Modifies the board in place by executing the given move path.
    A slide is length 2 and distance 1.
    A jump is sequence of squares, where adjacent elements have distance 2.
    Also handles crowning pawns at their target rows.
    """
    if len(move) < 2:
        return board
        
    r0, c0 = move[0]
    piece = board[r0][c0]
    
    # Check if this is a jump sequence or a slide
    is_jump = (abs(move[0][0] - move[1][0]) == 2)
    
    if is_jump:
        # Loop through jump steps, clearing intermediate pieces
        for i in range(len(move) - 1):
            curr_r, curr_c = move[i]
            next_r, next_c = move[i+1]
            mid_r = (curr_r + next_r) // 2
            mid_c = (curr_c + next_c) // 2
            
            # Move the piece on intermediate steps
            curr_piece = board[curr_r][curr_c]
            board[curr_r][curr_c] = EMPTY
            board[mid_r][mid_c] = EMPTY
            
            # Check if crowning occurs at the end of this step
            if player == 'Red' and next_r == 7 and curr_piece == RED_PAWN:
                curr_piece = RED_KING
            elif player == 'White' and next_r == 0 and curr_piece == WHITE_PAWN:
                curr_piece = WHITE_KING
                
            board[next_r][next_c] = curr_piece
    else:
        # Standard single step slide
        r1, c1 = move[1]
        board[r0][c0] = EMPTY
        
        # Check if crowning occurs
        if player == 'Red' and r1 == 7 and piece == RED_PAWN:
            piece = RED_KING
        elif player == 'White' and r1 == 0 and piece == WHITE_PAWN:
            piece = WHITE_KING
            
        board[r1][c1] = piece
        
    return board

def evaluate_board(board):
    """
    Evaluation Heuristic:
    Positive scores favor Red, negative scores favor White.
    Weights: Pawns = 100, Kings = 175.
    Factors: Center control, back-row stability, advanced pawn promotion paths.
    """
    score = 0
    
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece == EMPTY:
                continue
                
            # Piece values and basic weights
            if piece == RED_PAWN:
                score += 100
                if 2 <= r <= 5 and 2 <= c <= 5:
                    score += 10
                if r == 0:
                    score += 15
                score += r * 8
                
            elif piece == RED_KING:
                score += 175
                if 2 <= r <= 5 and 2 <= c <= 5:
                    score += 12
                if r == 0:
                    score += 5
                    
            elif piece == WHITE_PAWN:
                score -= 100
                if 2 <= r <= 5 and 2 <= c <= 5:
                    score -= 10
                if r == 7:
                    score -= 15
                score -= (7 - r) * 8
                
            elif piece == WHITE_KING:
                score -= 175
                if 2 <= r <= 5 and 2 <= c <= 5:
                    score -= 12
                if r == 7:
                    score -= 5
                    
    return score

def minimax(board, depth, alpha, beta, player, maximizing_player):
    """
    Minimax search with Alpha-Beta Pruning structured as a Depth-First Search (DFS).
    maximizing_player is True for Red, False for White.
    Returns: (eval_score, best_move_path)
    """
    if depth == 0:
        return evaluate_board(board), None
        
    moves = get_valid_moves(board, player)
    
    if not moves:
        if player == 'Red':
            return -100000 + depth, None
        else:
            return 100000 - depth, None
            
    moves.sort(key=lambda m: (len(m) > 2 or abs(m[0][0] - m[1][0]) == 2), reverse=True)
    
    best_move = None
    
    if maximizing_player:
        max_eval = -float('inf')
        for move in moves:
            new_board = copy_board(board)
            execute_move(new_board, move, 'Red')
            val, _ = minimax(new_board, depth - 1, alpha, beta, 'White', False)
            if val > max_eval:
                max_eval = val
                best_move = move
            alpha = max(alpha, val)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = float('inf')
        for move in moves:
            new_board = copy_board(board)
            execute_move(new_board, move, 'White')
            val, _ = minimax(new_board, depth - 1, alpha, beta, 'Red', True)
            if val < min_eval:
                min_eval = val
                best_move = move
            beta = min(beta, val)
            if beta <= alpha:
                break
        return min_eval, best_move

if __name__ == "__main__":
    # Self-test
    b = get_initial_board()
    print("Initial Board Evaluation:", evaluate_board(b))
    red_moves = get_valid_moves(b, 'Red')
    print("Sample Red moves:", red_moves[:3])
    score, best_move = minimax(b, 4, -float('inf'), float('inf'), 'Red', True)
    print("Best move evaluation score:", score)
    print("Best move path:", best_move)
