import streamlit as st
import streamlit.components.v1 as components
import os
import time

# Import engine logic (Red vs White Chess.com theme configuration)
from engine import (
    EMPTY, RED_PAWN, RED_KING, WHITE_PAWN, WHITE_KING,
    get_initial_board, get_valid_moves, execute_move,
    minimax, evaluate_board, get_piece_color, get_opponent,
    get_all_jumps, get_slides_for_piece
)

# Load the custom board component
parent_dir = os.path.dirname(os.path.abspath(__file__))
board_dir = os.path.join(parent_dir, "board_component")
checkers_board = components.declare_component("checkers_board", path=board_dir)

# Page Configuration
st.set_page_config(
    page_title="Checkers AI Engine",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Global CSS for styling Streamlit layout to match the Clay Wood Theme
st.markdown("""
<style>
    /* Styling headers and title */
    .title-text {
        font-family: 'Outfit', 'Inter', sans-serif;
        font-weight: 800;
        font-size: 2.8rem;
        background: linear-gradient(45deg, #a66e4e, #dfcaaa); /* Wood Terracotta Gradient */
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .subtitle-text {
        font-size: 1.1rem;
        color: #bababa;
        margin-top: 0px;
        margin-bottom: 2rem;
    }
    
    /* Metrics display */
    .metric-card {
        background-color: #2b3035; /* Dark card background */
        border: 1px solid #37414b;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.25);
    }
    .metric-label {
        font-size: 0.85rem;
        color: #eae2cf;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "board" not in st.session_state:
    st.session_state.board = get_initial_board()
if "turn" not in st.session_state:
    st.session_state.turn = "Red"
if "selected_piece" not in st.session_state:
    st.session_state.selected_piece = None
if "allowed_destinations" not in st.session_state:
    st.session_state.allowed_destinations = []
if "last_move" not in st.session_state:
    st.session_state.last_move = []
if "best_move" not in st.session_state:
    st.session_state.best_move = []
if "click_timestamp" not in st.session_state:
    st.session_state.click_timestamp = 0
if "partial_jump" not in st.session_state:
    st.session_state.partial_jump = None
if "winner" not in st.session_state:
    st.session_state.winner = None
if "eval_score" not in st.session_state:
    st.session_state.eval_score = 0
if "predicted_winner" not in st.session_state:
    st.session_state.predicted_winner = "Balanced"
if "eval_depth" not in st.session_state:
    st.session_state.eval_depth = 6
if "ai_enabled" not in st.session_state:
    st.session_state.ai_enabled = True
if "ai_color" not in st.session_state:
    st.session_state.ai_color = "White"
if "sound_effects" not in st.session_state:
    st.session_state.sound_effects = True
if "ai_ready" not in st.session_state:
    st.session_state.ai_ready = False

# Reset helper
def reset_game():
    st.session_state.board = get_initial_board()
    st.session_state.turn = "Red"
    st.session_state.selected_piece = None
    st.session_state.allowed_destinations = []
    st.session_state.last_move = []
    st.session_state.best_move = []
    st.session_state.partial_jump = None
    st.session_state.winner = None
    st.session_state.eval_score = 0
    st.session_state.predicted_winner = "Balanced"
    st.session_state.ai_ready = False

# Sidebar Controls
st.sidebar.markdown("<h2 style='color: #a66e4e;'>Controls</h2>", unsafe_allow_html=True)

# Mode Selector
mode = st.sidebar.radio(
    "Application Mode",
    ["Live Play Against AI", "Sandbox Position Evaluator"],
    key="app_mode"
)

st.sidebar.checkbox("Enable Sound Effects", key="sound_effects")

st.sidebar.markdown("---")

if mode == "Live Play Against AI":
    st.sidebar.subheader("Game Settings")
    
    # Choose human color (Chess.com Red vs White layout)
    player_color = st.sidebar.selectbox("Play as Color", ["Red", "White"], index=0)
    ai_color = "White" if player_color == "Red" else "Red"
    if st.session_state.ai_color != ai_color:
        st.session_state.ai_color = ai_color
        st.session_state.ai_ready = (st.session_state.turn == ai_color)
    
    # AI toggle
    st.sidebar.checkbox("AI Opponent Enabled", key="ai_enabled")
    
    # Difficulty / Depth
    ai_depth = st.sidebar.slider("AI Search Depth (Lookahead)", min_value=1, max_value=8, value=6)
    rotated = st.sidebar.checkbox("Flip Board (Rotate 180°)", value=(player_color == "Red"))
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Reset / Restart Game", type="primary", use_container_width=True):
        reset_game()
        st.rerun()

else:  # Sandbox Mode
    st.sidebar.subheader("Sandbox Editor Tools")
    
    # Palette selection (Red vs White checkers pieces)
    sandbox_tool = st.sidebar.radio(
        "Active Placement Tool",
        options=["RP", "RK", "WP", "WK", "E"],
        format_func=lambda x: {
            "RP": "🔴 Red Pawn",
            "RK": "👑🔴 Red King",
            "WP": "⚪ White Pawn",
            "WK": "👑⚪ White King",
            "E": "🧹 Eraser (Remove Piece)"
        }[x],
        key="sandbox_tool"
    )
    
    st.sidebar.markdown("---")
    
    # Explicit turn selector
    sandbox_turn = st.sidebar.radio(
        "Whose Turn to Move Next?",
        options=["Red", "White"],
        index=0 if st.session_state.turn == "Red" else 1,
        horizontal=True
    )
    if sandbox_turn != st.session_state.turn:
        st.session_state.turn = sandbox_turn
        st.session_state.best_move = [] # Clear best move on turn change
        st.rerun()
        
    # Sandbox depth selector
    eval_depth = st.sidebar.slider("Evaluator Search Depth", min_value=1, max_value=8, value=6)
    st.session_state.eval_depth = eval_depth
    rotated = st.sidebar.checkbox("Flip Board (Rotate 180°)", value=False)
    
    st.sidebar.markdown("---")
    
    col_sb1, col_sb2 = st.sidebar.columns(2)
    with col_sb1:
        if st.button("Clear Board", use_container_width=True):
            st.session_state.board = [[EMPTY for _ in range(8)] for _ in range(8)]
            st.session_state.selected_piece = None
            st.session_state.allowed_destinations = []
            st.session_state.last_move = []
            st.session_state.best_move = []
            st.session_state.winner = None
            st.session_state.eval_score = 0
            st.session_state.predicted_winner = "Balanced"
            st.rerun()
            
    with col_sb2:
        if st.button("Reset Layout", use_container_width=True):
            reset_game()
            st.rerun()

# Layout Design
st.markdown("<h1 class='title-text'>👑 Checkers AI Engine</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle-text'>A state-of-the-art interactive minimax board evaluator with alpha-beta search.</p>", unsafe_allow_html=True)

# Split view: Board on left, Stats/Actions on right
col_board, col_stats = st.columns([1.3, 1])

# --- Game Metrics Calculations ---
def count_pieces(board):
    rp, rk, wp, wk = 0, 0, 0, 0
    for row in board:
        for val in row:
            if val == RED_PAWN: rp += 1
            elif val == RED_KING: rk += 1
            elif val == WHITE_PAWN: wp += 1
            elif val == WHITE_KING: wk += 1
    return rp, rk, wp, wk

rp, rk, wp, wk = count_pieces(st.session_state.board)
red_total = rp + rk
white_total = wp + wk

# Game over checks (Live Mode)
if mode == "Live Play Against AI" and st.session_state.winner is None:
    # Check if active player has any moves
    active_moves = get_valid_moves(st.session_state.board, st.session_state.turn)
    if not active_moves:
        st.session_state.winner = get_opponent(st.session_state.turn)

# --- Automatic AI Execution (Live Play) ---
if (mode == "Live Play Against AI" and 
    st.session_state.ai_enabled and 
    st.session_state.turn == st.session_state.ai_color and 
    st.session_state.ai_ready and
    st.session_state.winner is None):
    
    maximizing = (st.session_state.ai_color == "Red")
    score, ai_move = minimax(
        st.session_state.board,
        ai_depth,
        -float('inf'),
        float('inf'),
        st.session_state.ai_color,
        maximizing
    )
    
    if ai_move:
        st.session_state.board = execute_move(st.session_state.board, ai_move, st.session_state.ai_color)
        st.session_state.last_move = ai_move
        st.session_state.eval_score = score
        
        # Check game over for user
        next_p = get_opponent(st.session_state.ai_color)
        next_moves = get_valid_moves(st.session_state.board, next_p)
        if not next_moves:
            st.session_state.winner = st.session_state.ai_color
        else:
            st.session_state.turn = next_p
    else:
        st.session_state.winner = get_opponent(st.session_state.ai_color)
        
    st.session_state.ai_ready = False
    st.rerun()

# --- Render Board UI in Column 1 ---
with col_board:
    board_mode = "play" if mode == "Live Play Against AI" else "sandbox"
    
    click_data = checkers_board(
        board=st.session_state.board,
        mode=board_mode,
        selected_piece=st.session_state.selected_piece,
        allowed_destinations=st.session_state.allowed_destinations,
        last_move=st.session_state.last_move,
        best_move=st.session_state.best_move,
        sandbox_tool=st.session_state.sandbox_tool if board_mode == "sandbox" else "E",
        sound_effects=st.session_state.sound_effects,
        winner=st.session_state.winner,
        rotated=rotated,
        key="checkers_board_instance"
    )

# --- Handle Board Clicks ---
if click_data and click_data.get("timestamp", 0) > st.session_state.click_timestamp:
    st.session_state.click_timestamp = click_data["timestamp"]
    
    if click_data.get("animation_completed"):
        if mode == "Live Play Against AI" and st.session_state.turn == st.session_state.ai_color:
            st.session_state.ai_ready = True
            st.rerun()
    else:
        r = click_data.get("r")
        c = click_data.get("c")
        
        if r is not None and c is not None:
            if mode == "Live Play Against AI":
                is_user_turn = (st.session_state.turn != st.session_state.ai_color or not st.session_state.ai_enabled)
                
                if is_user_turn and st.session_state.winner is None:
                    active_player = st.session_state.turn
                    
                    # Sub-scenario 1: Multi-jump locked in
                    if st.session_state.partial_jump is not None:
                        from_r, from_c = st.session_state.partial_jump
                        dest_coords = st.session_state.allowed_destinations
                        
                        if (r, c) in dest_coords:
                            # Execute single step of jump
                            step_move = [(from_r, from_c), (r, c)]
                            st.session_state.board = execute_move(st.session_state.board, step_move, active_player)
                            
                            # Accumulate jump paths for visuals
                            if not st.session_state.last_move:
                                st.session_state.last_move = [(from_r, from_c), (r, c)]
                            else:
                                st.session_state.last_move.append((r, c))
                                
                            # Check crowning
                            piece = st.session_state.board[r][c]
                            is_crowned = False
                            if active_player == 'Red' and r == 7 and piece == RED_PAWN:
                                is_crowned = True
                            elif active_player == 'White' and r == 0 and piece == WHITE_PAWN:
                                is_crowned = True
                                
                            # Find remaining jumps
                            further_jumps = []
                            if not is_crowned:
                                all_jumps = get_all_jumps(st.session_state.board, active_player)
                                further_jumps = [j for j in all_jumps if j[0] == (r, c)]
                                
                            if further_jumps:
                                st.session_state.partial_jump = (r, c)
                                st.session_state.selected_piece = (r, c)
                                st.session_state.allowed_destinations = [j[1] for j in further_jumps]
                                st.session_state.best_move = []
                            else:
                                # Turn complete!
                                st.session_state.partial_jump = None
                                st.session_state.selected_piece = None
                                st.session_state.allowed_destinations = []
                                st.session_state.best_move = []
                                
                                # Toggle turn and wait for human animation to finish
                                st.session_state.turn = get_opponent(active_player)
                                st.session_state.ai_ready = False
                                
                            st.session_state.eval_score = evaluate_board(st.session_state.board)
                            st.rerun()
                    
                    # Sub-scenario 2: Normal Move / Start Multi-jump
                    else:
                        piece_val = st.session_state.board[r][c]
                        piece_color = get_piece_color(piece_val)
                        
                        # Selecting one of own pieces
                        if piece_color == active_player:
                            all_jumps = get_all_jumps(st.session_state.board, active_player)
                            if all_jumps:
                                piece_jumps = [j for j in all_jumps if j[0] == (r, c)]
                                if piece_jumps:
                                    st.session_state.selected_piece = (r, c)
                                    st.session_state.allowed_destinations = list({j[1] for j in piece_jumps})
                                    st.session_state.best_move = []
                                else:
                                    st.sidebar.warning("Capture is available! Jumps are mandatory.")
                            else:
                                # Slides
                                piece_slides = get_slides_for_piece(st.session_state.board, r, c, active_player)
                                if piece_slides:
                                    st.session_state.selected_piece = (r, c)
                                    st.session_state.allowed_destinations = [s[1] for s in piece_slides]
                                    st.session_state.best_move = []
                            st.rerun()
                            
                        # Executing selection destination
                        elif (r, c) in st.session_state.allowed_destinations:
                            from_r, from_c = st.session_state.selected_piece
                            is_jump = (abs(from_r - r) == 2)
                            
                            if not is_jump:
                                # Simple slide
                                slide_move = [(from_r, from_c), (r, c)]
                                st.session_state.board = execute_move(st.session_state.board, slide_move, active_player)
                                st.session_state.last_move = slide_move
                                st.session_state.selected_piece = None
                                st.session_state.allowed_destinations = []
                                st.session_state.best_move = []
                                
                                # Toggle turn and wait for human animation to finish
                                st.session_state.turn = get_opponent(active_player)
                                st.session_state.ai_ready = False
                                
                                st.session_state.eval_score = evaluate_board(st.session_state.board)
                                st.rerun()
                            else:
                                # Single jump
                                jump_move = [(from_r, from_c), (r, c)]
                                st.session_state.board = execute_move(st.session_state.board, jump_move, active_player)
                                st.session_state.last_move = jump_move
                                
                                # Crown validation
                                piece = st.session_state.board[r][c]
                                is_crowned = False
                                if active_player == 'Red' and r == 7 and piece == RED_PAWN:
                                    is_crowned = True
                                elif active_player == 'White' and r == 0 and piece == WHITE_PAWN:
                                    is_crowned = True
                                    
                                further_jumps = []
                                if not is_crowned:
                                    all_jumps = get_all_jumps(st.session_state.board, active_player)
                                    further_jumps = [j for j in all_jumps if j[0] == (r, c)]
                                    
                                if further_jumps:
                                    # Must keep jumping
                                    st.session_state.partial_jump = (r, c)
                                    st.session_state.selected_piece = (r, c)
                                    st.session_state.allowed_destinations = [j[1] for j in further_jumps]
                                    st.session_state.best_move = []
                                else:
                                    st.session_state.partial_jump = None
                                    st.session_state.selected_piece = None
                                    st.session_state.allowed_destinations = []
                                    st.session_state.best_move = []
                                    
                                    # Toggle turn and wait for human animation to finish
                                    st.session_state.turn = get_opponent(active_player)
                                    st.session_state.ai_ready = False
                                    
                                st.session_state.eval_score = evaluate_board(st.session_state.board)
                                st.rerun()
                        else:
                            # Deselect
                            st.session_state.selected_piece = None
                            st.session_state.allowed_destinations = []
                            st.rerun()
                            
            elif mode == "Sandbox Position Evaluator":
                tool = st.session_state.sandbox_tool
                
                if (r + c) % 2 == 1: # Dark squares only
                    if tool == "RP":
                        st.session_state.board[r][c] = RED_PAWN
                    elif tool == "RK":
                        st.session_state.board[r][c] = RED_KING
                    elif tool == "WP":
                        st.session_state.board[r][c] = WHITE_PAWN
                    elif tool == "WK":
                        st.session_state.board[r][c] = WHITE_KING
                    elif tool == "E":
                        st.session_state.board[r][c] = EMPTY
                        
                    # Clear calculations since board edited
                    st.session_state.last_move = []
                    st.session_state.best_move = []
                    st.session_state.winner = None
                    st.session_state.eval_score = evaluate_board(st.session_state.board)
                    st.rerun()

# --- Render Stats & Dashboards in Column 2 ---
with col_stats:
    st.markdown(f"### ⚙️ Mode: {mode}")
    
    # 1. Show Turn Banner
    if st.session_state.winner is not None:
        st.balloons()
        st.success(f"🏆 **Winner: {st.session_state.winner} Wins!**")
    else:
        turn_color = "dark" if st.session_state.turn == "Red" else "light"
        turn_text_color = "#cbd5e1" if st.session_state.turn == "Red" else "#dfcaaa"
        border_color = "#3a444d" if st.session_state.turn == "Red" else "#dfcaaa"
        turn_label = "Red (Dark Slate)" if st.session_state.turn == "Red" else "White (Light Cream)"
        st.markdown(
            f"<div style='padding: 0.75rem; border-radius: 8px; border-left: 5px solid {border_color}; "
            f"background-color: #2b3035; color: {turn_text_color}; font-weight: 600;'>"
            f"👉 Turn: {turn_label} to move</div>",
            unsafe_allow_html=True
        )

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    
    # 2. Material count layout
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-label'>⚫ Red (Dark) Pieces</div>"
            f"<div class='metric-value' style='color: #7c8e9d;'>{red_total}</div>"
            f"<div style='font-size: 0.8rem; color: #bababa;'>Pawns: {rp} | Kings: {rk}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    with c_m2:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-label'>⚪ White (Light) Pieces</div>"
            f"<div class='metric-value' style='color: #dfcaaa;'>{white_total}</div>"
            f"<div style='font-size: 0.8rem; color: #bababa;'>Pawns: {wp} | Kings: {wk}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    # 3. Dynamic Evaluation score (with Chess.com style horizontal balance bar)
    st.markdown("#### 📊 Board Evaluation Balance")
    
    val_score = st.session_state.eval_score
    
    # Handle infinite/checkmate/extreme scores safely to prevent OverflowError in int(float('inf'))
    if val_score > 50000:
        red_bar_text = "+∞"
        white_bar_text = ""
        bounded_score = 1000
    elif val_score < -50000:
        red_bar_text = ""
        white_bar_text = "-∞"
        bounded_score = -1000
    else:
        bounded_score = max(-1000, min(1000, val_score))
        red_bar_text = f"+{bounded_score/100:.2f}" if bounded_score > 0 else ""
        white_bar_text = f"{bounded_score/100:.2f}" if bounded_score < 0 else ""
        if bounded_score == 0:
            red_bar_text = "0.0"
            
    raw_pct = 50 + (bounded_score / 1000) * 50
    red_pct = max(5, min(95, int(raw_pct)))
    white_pct = 100 - red_pct
        
    st.markdown(
        f'<div style="display: flex; height: 26px; width: 100%; background-color: #121416; border-radius: 13px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.35); border: 2px solid #5a6572;">'
        f'<div style="width: {red_pct}%; background: linear-gradient(to right, #2b353f, #4a5560); transition: width 0.4s ease; display: flex; align-items: center; justify-content: center; color: #ffffff; font-weight: 700; font-size: 11px;">{red_bar_text}</div>'
        f'<div style="width: {white_pct}%; background: linear-gradient(to right, #ebdcb9, #fdf6e7); transition: width 0.4s ease; display: flex; align-items: center; justify-content: center; color: #232a30; font-weight: 700; font-size: 11px;">{white_bar_text}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    
    st.markdown(f"<div style='text-align: center; font-size: 0.9rem; color: #dfcaaa; margin-top: 4px; font-weight: 500;'>Raw Heuristic Value: {val_score}</div>", unsafe_allow_html=True)
    
    # 4. Mode Actions Panel
    st.markdown("---")
    
    if mode == "Live Play Against AI":
        st.markdown("#### ℹ️ Game Status")
        if st.session_state.partial_jump:
            st.info("⚠️ **Multi-jump Lock**: You must finish jumping with the highlighted piece!")
        else:
            jumps = get_all_jumps(st.session_state.board, st.session_state.turn)
            if jumps:
                st.warning("⚠️ **Capture available!** You must capture your opponent's piece (mandatory jumps).")
            else:
                st.write("Make any legal diagonal move.")
                
        # History or log
        if st.session_state.last_move:
            move_desc = " ➡️ ".join([f"({r},{c})" for r, c in st.session_state.last_move])
            st.code(f"Last Move: {move_desc}", language="text")
            
    else:  # Sandbox Position Evaluator
        st.markdown("#### 🧠 AI Position Evaluator")
        
        if st.button("Evaluate Position", type="primary", use_container_width=True):
            active_side = st.session_state.turn
            maximizing = (active_side == "Red")
            
            # Perform search
            score, best_move = minimax(
                st.session_state.board,
                st.session_state.eval_depth,
                -float('inf'),
                float('inf'),
                active_side,
                maximizing
            )
            
            # Set highlights and display outputs
            st.session_state.best_move = best_move if best_move else []
            st.session_state.eval_score = score
            
            # Save predicted winner
            if score > 50000:
                st.session_state.predicted_winner = "Red Wins (Forced Checkmate)"
            elif score < -50000:
                st.session_state.predicted_winner = "White Wins (Forced Checkmate)"
            elif score > 150:
                st.session_state.predicted_winner = "Red has major advantage"
            elif score > 40:
                st.session_state.predicted_winner = "Red is slightly favored"
            elif score < -150:
                st.session_state.predicted_winner = "White has major advantage"
            elif score < -40:
                st.session_state.predicted_winner = "White is slightly favored"
            else:
                st.session_state.predicted_winner = "Draw / Even Game"
                
            st.rerun()
                
        # Render Evaluator results if computed
        if st.session_state.best_move:
            st.markdown("<div style='background-color: #2b3035; border-radius: 8px; padding: 12px; border: 1px solid #a66e4e;'>", unsafe_allow_html=True)
            st.markdown(f"**Predicted Winner**: `{st.session_state.predicted_winner}`")
            st.markdown(f"**Lookahead DFS Depth**: `{st.session_state.eval_depth}` ply")
            
            move_desc = " ➡️ ".join([f"({r},{c})" for r, c in st.session_state.best_move])
            st.markdown(f"**Best Next Move**: `{move_desc}`")
            st.markdown("<small style='color: #64748b;'>Best move path is currently highlighted in blue on the board.</small>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Click 'Evaluate Position' to execute minimax analysis at the selected depth.")
