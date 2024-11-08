import socket 
import time

HOST = '127.0.0.1'
PORT = 8080

def start_client():
    print("client")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((HOST, PORT))
        print("Connected to the server. \n")
    
        while True:
        
            initial_hand = client_socket.recv(1024).decode()
            print("\nYour initial hand of cards:")
            print(initial_hand)
        
            while True:
            
                response = client_socket.recv(1024).decode()
                print(response)
                
                if "Please discard your lowest card" in response:
                    discarded_card = input("Enter card to discard: ")
                    client_socket.sendall(discarded_card.encode())
                elif "Choose to take a card" in response:
                    choice = input("Enter 'deck' or 'discard': ")
                    client_socket.sendall(choice.encode())
                    
                elif "Show your cards?" in response:
                    show_decision = input("Would you like to show your cards? (yes/no): ")
                    client_socket.sendall(show_decision.encode())

                
            
        
if __name__ == "__main__":
    start_client()
            