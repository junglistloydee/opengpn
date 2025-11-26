
import socket
import threading
import struct

# --- Configuration ---
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 5000

# --- Globals ---
client_to_game_socket = {}
lock = threading.Lock()

def create_custom_header(dest_ip, dest_port):
    """
    Creates the custom header for the tunnel.
    Header format: [IP_len (1 byte)][IP (variable)][Port (2 bytes)]
    """
    ip_bytes = dest_ip.encode('utf-8')
    ip_len = len(ip_bytes)
    header = struct.pack(f'!B{ip_len}sH', ip_len, ip_bytes, dest_port)
    return header

def handle_client_packet(data, client_addr):
    """
    Handles a single packet from a client.
    """
    try:
        ip_len = data[0]
        game_server_ip = data[1:1+ip_len].decode('utf-8')
        game_server_port = struct.unpack('!H', data[1+ip_len:1+ip_len+2])[0]
        payload = data[1+ip_len+2:]

        game_server_addr = (game_server_ip, game_server_port)

        with lock:
            game_socket = client_to_game_socket.get(client_addr)

        if game_socket:
            game_socket.sendto(payload, game_server_addr)

    except Exception as e:
        print(f"Error handling client packet from {client_addr}: {e}")

def listen_for_game_server(game_socket, client_addr, server_socket):
    """
    Listens for responses from the game server and forwards them back to the client.
    """
    while True:
        try:
            data, game_server_addr = game_socket.recvfrom(4096)

            header = create_custom_header(game_server_addr[0], game_server_addr[1])
            response_packet = header + data
            server_socket.sendto(response_packet, client_addr)

        except Exception as e:
            print(f"Error receiving from game server for {client_addr}: {e}")
            break

    with lock:
        if client_addr in client_to_game_socket:
            client_to_game_socket[client_addr].close()
            del client_to_game_socket[client_addr]
        print(f"[*] Client {client_addr} disconnected.")

def main():
    """
    Main function to start the relay server.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((LISTEN_IP, LISTEN_PORT))
    print(f"[*] Relay server listening on {LISTEN_IP}:{LISTEN_PORT}")

    while True:
        try:
            data, client_addr = server_socket.recvfrom(4096)

            with lock:
                if client_addr not in client_to_game_socket:
                    print(f"[*] New client connected: {client_addr}")
                    game_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    client_to_game_socket[client_addr] = game_socket

                    # Start a single, long-lived listener thread for the new client
                    threading.Thread(target=listen_for_game_server,
                                     args=(game_socket, client_addr, server_socket),
                                     daemon=True).start()

            # Process the packet from the client
            handle_client_packet(data, client_addr)

        except KeyboardInterrupt:
            print("[*] Server shutting down.")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")

    server_socket.close()

if __name__ == "__main__":
    main()
