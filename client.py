
import pydivert
import psutil
import socket
import threading
import struct
import time

# --- Configuration ---
RELAY_SERVER_IP = "127.0.0.1"  # Replace with your VPS IP
RELAY_SERVER_PORT = 5000
TARGET_PROCESS_NAME = "game.exe"

# --- Globals ---
# Connection table to map (game_server_ip, game_server_port) -> (original_src_ip, original_src_port)
connection_table = {}
# Lock for thread-safe access to the connection table
lock = threading.Lock()

def find_pid(process_name):
    """
    Find the Process ID (PID) for a given process name.
    """
    while True:
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == process_name:
                return proc.info['pid']
        print(f"Process '{process_name}' not found. Retrying in 5 seconds...")
        time.sleep(5)

def create_custom_header(dest_ip, dest_port):
    """
    Creates the custom header for the tunnel.
    Header format: [IP_len (1 byte)][IP (variable)][Port (2 bytes)]
    """
    ip_bytes = dest_ip.encode('utf-8')
    ip_len = len(ip_bytes)
    return struct.pack(f'!B{ip_len}sH', ip_len, ip_bytes, dest_port)

def relay_to_server(packet, client_socket):
    """
    Encapsulates and sends a captured packet to the relay server.
    """
    try:
        dest_ip = packet.dst_addr
        dest_port = packet.dst_port

        # Store the connection info
        with lock:
            connection_table[(dest_ip, dest_port)] = (packet.src_addr, packet.src_port)

        header = create_custom_header(dest_ip, dest_port)
        encapsulated_packet = header + packet.payload
        client_socket.sendto(encapsulated_packet, (RELAY_SERVER_IP, RELAY_SERVER_PORT))
    except Exception as e:
        print(f"Error relaying packet to server: {e}")

def listen_for_relay(w, client_socket):
    """
    Listens for responses from the relay server and injects them back.
    """
    while True:
        try:
            data, _ = client_socket.recvfrom(4096)

            # Unpack the header to get the game server's address
            ip_len = data[0]
            game_server_ip = data[1:1+ip_len].decode('utf-8')
            game_server_port = struct.unpack('!H', data[1+ip_len:1+ip_len+2])[0]
            payload = data[1+ip_len+2:]

            game_server_addr = (game_server_ip, game_server_port)

            with lock:
                if game_server_addr in connection_table:
                    original_src = connection_table[game_server_addr]

                    # Create a new packet to inject.
                    # We now have the correct source and destination addresses.
                    # Pydivert will automatically build the IP and UDP headers.
                    new_packet = pydivert.Packet(
                        payload=payload,
                        src_addr=game_server_ip,
                        src_port=game_server_port,
                        dst_addr=original_src[0],
                        dst_port=original_src[1]
                    )
                    w.send(new_packet)

        except Exception as e:
            print(f"Error receiving from relay: {e}")
            break

def main():
    """
    Main function to start the client.
    """
    pid = find_pid(TARGET_PROCESS_NAME)
    print(f"Found {TARGET_PROCESS_NAME} with PID: {pid}")

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # The filter now includes both TCP and UDP.
        # Note: This simple client is only suitable for UDP-based games.
        # A full TCP proxy would be much more complex.
        filter_rule = f"outbound and (udp or tcp) and pid == {pid}"
        with pydivert.WinDivert(filter_rule) as w:
            print(f"[*] Capturing outbound UDP/TCP traffic for PID {pid}")

            listener_thread = threading.Thread(target=listen_for_relay,
                                             args=(w, client_socket),
                                             daemon=True)
            listener_thread.start()

            for packet in w:
                if packet.is_udp:
                    relay_to_server(packet, client_socket)
                else:
                    # For TCP, we just let it pass through for now.
                    # A proper implementation would require a TCP state machine.
                    w.send(packet)

    except KeyboardInterrupt:
        print("[*] Client shutting down.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    main()
