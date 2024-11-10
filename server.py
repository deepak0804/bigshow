import socket
import threading
import random
import time
import re
import select
ranks = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
values = {'2': 2, '3' : 3, '4' : 4, '5' : 5, '6' : 6, '7' : 7 , '8' : 8, '9' : 9, '10' : 10, 'J' : 10, 'Q' : 10, 'K' : 10, 'A' : 1}


HOST = '127.0.0.1'
PORT = 8080
cards_per_player = 5
player_hands = {}
last_discarded_card = None
rounds_completed = 0
clients = []
max_players = 6
game_start_time = 10
deck = []
current_turn = 1
turn_ondition = threading.Condition()
game_over =False
players_ready_to_show = 0
player_rounds = {}
discarded_pile = []
show_flag = False
start_condition = True

def create_deck(num_players):
    single_deck = ranks * 4 + ['Joker', 'Joker']
    deck = single_deck * 2 if num_players > 4 else single_deck
    random.shuffle(deck)
    return deck 
    
def replenish_deck(num_players):
    global deck
    deck = create_deck(num_players)

def replenish_and_draw():
    global deck,  discarded_pile
    if discarded_pile:
        deck = discarded_pile[:]
        random.shuffle(deck)
        discarded_pile.clear()
    else:
        deck = [str(i) for i in range(1,53)] * 2
        random.shuffle(deck)
        
    return deck.pop()

def card_value(card):
    if card.isdigit():
        return int(card)

    elif card == 'J':
        return 10
    elif card == 'Q':
        return 10
    elif card == 'K':
        return 10
    elif card == 'A':
        return 1
    elif card == 'Joker':
        return 0
    else:
        raise ValueError(f"Invalid card value: {card}")
        
            
def handle_client(conn, player_id):
    global last_discarded_card, rounds_completed, current_turn, game_over, players_ready_to_show, player_rounds, show_flag
    if player_id not in player_rounds:
        player_rounds[player_id] = 0
    
    try:
        global deck
        if not deck:
            replenish_deck(len(clients))
    
        try:
            
            hand = [deck.pop() for _ in range(cards_per_player)]
        except IndexError:
            conn.sendall("Deck is empty.\n".encode())
            conn.close()
            return
        
        player_hands[f"Player {player_id}"] = hand
    
        conn.sendall(f"Your initial hand: {', '.join(hand)}\n".encode())
        
        while not game_over:
            with turn_ondition:
                while current_turn != player_id:
                    turn_ondition.wait()
                player_rounds[player_id] += 1
                
                try:
                    conn.sendall("It's your turn.\n".encode())
            
                except (ConnectionResetError, BrokenPipeError):
                    print(f"Player {player_id} has disconnected.")
                    clients.remove(conn)
                    current_turn = (current_turn % len(clients)) + 1
                    turn_ondition.notify_all()
                    return
                
                
                
                if last_discarded_card:    
                    conn.sendall(f"Last discarded card: {last_discarded_card if last_discarded_card else 'None'}\n".encode())
                else:
                    conn.sendall("No discarded card available yet.\n".encode())
                
                conn.sendall("Please discard your lowest card: ".encode())
                ready = select.select([conn], [], [], 10)  # Wait for up to 10 seconds
                if ready[0]:
                    discarded_card = conn.recv(1024).decode().strip()
                    print(f"discarded card: {discarded_card}\n")
                    if discarded_card in hand:
                    
                        hand.remove(discarded_card)
            
                        player_discarded_card = discarded_card
                    
                    else:
                        conn.sendall(f"Error: You dont have {discarded_card} in your hand. \n".encode())
                        continue
                else:
                    print(f"No response from client within 10 seconds. Continuing...\n")
           # last_discarded_card = discarded_card
            
                if player_id == 1 and player_rounds[player_id] == 1:
                    new_card = deck.pop() if deck else replenish_and_draw()
                    
                    conn.sendall(f"You are the first player; you drew from the deck: {new_card}\n".encode())
                
                else:
                    conn.sendall(f"Choose to take a card from deck or previous discard({last_discarded_card}): ".encode())
        
                    choice = conn.recv(1024).decode().strip()
                    if choice.lower() == 'discard':
                        print("inside discard")
                        new_card = last_discarded_card
                
                    else:
                        print("not inside discard")
                        new_card = deck.pop() if deck else None
                    
                        if new_card is None:
                            replenish_deck(len(clients))
                            new_card = deck.pop()
                
                    conn.sendall(f"New card: {new_card}\n".encode())
            
            
                hand.append(new_card)
            #if discarded_card in hand:
             #   hand.remove(discarded_card)
                
            
                player_hands[f"Player {player_id}"] = hand
                conn.sendall(f"New card: {new_card}\n Your updated hand: {', '.join(hand)}\n".encode())
            
                last_discarded_card = player_discarded_card
                conn.sendall("Your turn is complete.\n".encode())
            
                next_player_id = (current_turn % len(clients)) + 1
                current_turn = next_player_id
                turn_ondition.notify_all()
                
                
            if all(round >= 3 for round in player_rounds.values()):
                print("yes")
                for pid in range(1, len(clients) + 1):
                    if player_rounds[pid] > 3:
                        player_conn = clients[pid - 1]
                        show_flag = True
                        player_conn.sendall("Three rounds completed. Show your cards? (yes/no): ".encode())
                        
                        show_decision = conn.recv(1024).decode().strip()  # Use player_conn
                        print("show decisiom")
                        print(show_decision)
                        if show_decision.lower() == 'yes':
                            
                            game_over = True
                            break
                        
                if game_over:
                    for client in clients:
                        client.sendall("Game over! One of the players has chosen to show their cards.\n".encode())
                    break
                    
                
                    
                    
    except (ConnectionResetError, BrokenPipeError, OSError):
        print(f"Player {player_id} has disconnected unexpectedly.")
        clients.remove(conn)
        conn.close()
        return        
        
    if game_over:
       # with turn_ondition:
        players_sum = {pid: sum(card_value(card) for card in hand) for pid , hand in player_hands.items()}
        winner_id_name, winning_score = max(players_sum.items(), key=lambda x: x[1])
        print("winner_id")
        winner_id = int ( ''.join(filter(str.isdigit, winner_id_name) ) )
        print(winner_id)
        for pid, client_conn in enumerate(clients,1):
            print("pid")
            print(pid)
            if pid == winner_id:
                print("winner")
                client_conn.sendall(f"Congrats, you won with a score of {winning_score}.\n".encode())
            else:
                print("loser")
                client_conn.sendall(f"Player {winner_id} won with a score of {winning_score}.\n".encode())
                
            if player_id in player_hands:  # Check if this player is still in the game
                conn.sendall("The game has ended. Thank you for playing!\n".encode())
        
    #conn.sendall("Final hand: {}\n".format(", ".join(hand)).encode())        
    #conn.close()
    conn.sendall("The game has ended\n".encode())
def start_game():
    global start_condition
    time.sleep(game_start_time+2)  # Wait for 30 seconds
    if len(clients) >= 2:
        print("30 seconds have passed. Game starts now.")
        num_players = len(clients)
        deck = create_deck(num_players)

        # Start handling each client in a new thread
        for player_id, conn in enumerate(clients, start=1):
            threading.Thread(target=handle_client, args=(conn, player_id)).start()
    else:
        print("Minimum players not connected. Unable to start the game.")
        start_condition = False
        return

        
def start_server():
    global deck, start_condition

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"Server started on {HOST}:{PORT}. Waiting for players to connect ...")
        
        first_client_connected = False
        start_time = None
        player_id = 1
        threading.Thread(target=start_game, daemon=True).start()
        time.sleep(game_start_time)
        while True:
            conn, address = server_socket.accept()
            player_id += len(clients)
            print(f"Player {player_id} connected from {address}")
            clients.append(conn)
            if not start_condition:
                conn.sendall("Minimum players not connected. Unable to start the game.\n".encode())
                conn.close()
                return
  # Exit loop to start the game

        print("30 seconds have passed. Game starts now.")
        num_players = len(clients)
        deck = create_deck(num_players)




start_server()
    
    