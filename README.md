# OpenGPN - A Custom Game VPN

This project provides a simple, custom-built "Game VPN" (GPN) designed to route traffic for a specific game (e.g., Aion 2) through a relay server. This can help improve latency and bypass certain network restrictions.

## How It Works

The solution consists of two main components:

*   **`client.py`**: A Windows client that captures outbound traffic from a specific game process using `pydivert`. It then encapsulates this traffic and sends it to a relay server.
*   **`server.py`**: A relay server (designed for Linux) that receives the encapsulated traffic, forwards it to the actual game server, and sends the responses back to the client.

## Setup Instructions

### 1. Server Setup (Taiwan VPS)

1.  **SSH into your VPS:**
    ```bash
    ssh your_username@your_vps_ip
    ```

2.  **Upload `server.py`:**
    Use `scp` or any other method to upload the `server.py` script to your VPS.

3.  **Run the Server:**
    It's recommended to run the server with `sudo` to ensure it has the necessary permissions for network operations.
    ```bash
    sudo python3 server.py
    ```
    You should see the output: `[*] Relay server listening on 0.0.0.0:5000`

4.  **Firewall Configuration:**
    Ensure that UDP port `5000` is open in your cloud provider's firewall settings (e.g., AWS Security Groups, Oracle Security Lists).

### 2. Client Setup (Windows PC)

1.  **Install Python:**
    If you don't have Python installed, download and install it from [python.org](https://www.python.org/). Make sure to check the box that says "Add Python to PATH" during installation.

2.  **Install Libraries:**
    Open a Command Prompt or PowerShell and install the required Python libraries:
    ```bash
    pip install pydivert psutil
    ```

3.  **WinDivert DLLs:**
    This is a crucial step. `pydivert` requires the WinDivert driver to be present.
    *   Download the **WinDivert 2.2** package from the [official website](https://reqrypt.org/windivert.html).
    *   Extract the contents of the downloaded zip file.
    *   From the extracted folder, find the `x64` subdirectory.
    *   Copy the following files from the `x64` folder and place them in the **same directory** as your `client.py` script:
        *   `WinDivert.dll`
        *   `WinDivert64.sys`

4.  **Configure `client.py`:**
    *   Open `client.py` in a text editor.
    *   Change the `RELAY_SERVER_IP` to the IP address of your Taiwan VPS.
    *   Change the `TARGET_PROCESS_NAME` to the executable name of your game (e.g., `"Aion2.exe"` or `"Purple.exe"`).

### 3. How to Run

1.  **Start the Server:**
    Make sure `server.py` is running on your VPS.

2.  **Start the Client:**
    You **must** run the client as an Administrator for it to be able to capture network traffic.
    *   Right-click on your `client.py` script and select "Run as administrator".
    *   Alternatively, open a Command Prompt or PowerShell **as Administrator**, navigate to the directory containing `client.py`, and run:
        ```bash
        python client.py
        ```

3.  **Launch the Game:**
    Start Aion 2. The client script will automatically detect the game process and start tunneling its traffic.

**Note:** If the game launcher and the game itself are separate processes, you may need to tunnel the launcher first to handle login and updates. You can do this by setting `TARGET_PROCESS_NAME` to the launcher's executable name. Once the game is running, you can either restart the client to target the game's executable or modify the script to handle both.
