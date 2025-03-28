# import bluetooth
# import json
# import requests
# from time import sleep
# from collections import deque

# # Configuration
# NUM_SENSORS = 2
# WINDOW_SIZE = 5
# FLASK_SERVER_URL = "http://10.197.191.141:80/update"

# # Store previous data for sliding window filtering
# sensor_data = {}

# def connect_bluetooth(address):
#     try:
#         sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
#         sock.connect((address, 1))
#         print(f"Connected to {address}")
#         return sock
#     except Exception as e:
#         print(f"Failed to connect to {address}: {e}")
#         return None

# def initialize_nodes(node_addresses):
#     for addr in node_addresses:
#         sensor_data[addr] = [deque([0] * WINDOW_SIZE, maxlen=WINDOW_SIZE) for _ in range(NUM_SENSORS)]
#     print("Initialization complete.")

# def predict_occupancy(node_addr):
#     predictions = []
#     for i in range(NUM_SENSORS):
#         window = sensor_data[node_addr][i]
#         # Simple majority voting for prediction
#         predictions.append(1 if sum(window) > (WINDOW_SIZE // 2) else 0)
#     return predictions

# def send_data_to_server(total_available_seats):
#     try:
#         data = {
#             "location": "Edge_Server_1",
#             "available_spaces": total_available_seats
#         }
#         response = requests.post(FLASK_SERVER_URL, json=data)
#         print("Data sent to server:", response.status_code)
#     except Exception as e:
#         print(f"Failed to send data: {e}")

# def main(node_addresses):
#     initialize_nodes(node_addresses)
#     sockets = [connect_bluetooth(addr) for addr in node_addresses]

#     while True:
#         # sleep(1)
#         # continue
#         total_available_seats = 0
#         for sock, addr in zip(sockets, node_addresses):
#             try:
#                 data = sock.recv(1024).decode('utf-8').strip()
#                 print(f"Received from {addr}: {data}")
#                 payload = json.loads(data)

#                 # Update sliding window
#                 for i, value in enumerate(payload['occupancy']):
#                     sensor_data[addr][i].append(value)

#                 # Predict occupancy using sliding window
#                 predicted_occupancy = predict_occupancy(addr)
#                 total_available_seats += predicted_occupancy.count(0)  # 0 means available

#             except Exception as e:
#                 print(f"Error with {addr}: {e}")

#         # Send aggregated data to Flask server
#         send_data_to_server(total_available_seats)

# if __name__ == "__main__":
#     node_addresses = ["58:56:00:00:8E:88"]  # Replace with your actual Arduino addresses
#     main(node_addresses)

import bluetooth
import json
import requests
from time import sleep
from collections import deque

# Configuration
NUM_SENSORS = 2
WINDOW_SIZE = 5
FLASK_SERVER_URL = "http://10.197.191.141:80/update"

sensor_data = {}
buffer = {}  # Buffer for accumulating incomplete messages

def connect_bluetooth(address):
    try:
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        sock.connect((address, 1))
        print(f"Connected to {address}")
        return sock
    except Exception as e:
        print(f"Failed to connect to {address}: {e}")
        return None

def initialize_nodes(node_addresses):
    for addr in node_addresses:
        sensor_data[addr] = [deque([0] * WINDOW_SIZE, maxlen=WINDOW_SIZE) for _ in range(NUM_SENSORS)]
        buffer[addr] = ""  # Initialize buffer for each node
    print("Initialization complete.")

def predict_occupancy(node_addr):
    predictions = []
    for i in range(NUM_SENSORS):
        window = sensor_data[node_addr][i]
        #predictions.append(1 if sum(window) > (WINDOW_SIZE // 2) else 0)
        predictions.append(1 if window[len(window)-1] == 1 else 0)
    return predictions

def send_data_to_server(total_available_seats):
    try:
        data = {
            "location": "Edge_Server_1",
            "available_spaces": total_available_seats
        }
        response = requests.post(FLASK_SERVER_URL, json=data)
        print("Data sent to server:", response.status_code)
    except Exception as e:
        print(f"Failed to send data: {e}")

def process_data(addr, raw_chunk):
    """ Accumulate data and extract full JSON messages. """
    buffer[addr] += raw_chunk  # Append new data to buffer
    try:
        # Attempt to decode complete JSON
        while True:
            start = buffer[addr].find("{")
            end = buffer[addr].find("}") + 1  # Find end of JSON
            print(f"found end {end}")
            
            if start == -1 or end == 0:
                return  # Incomplete data, wait for more

            json_str = buffer[addr][start:end]  # Extract JSON substring
            buffer[addr] = buffer[addr][end:]  # Remove processed part

            try:
                payload = json.loads(json_str)  # Parse JSON
                return payload
            except json.JSONDecodeError:
                continue  # Keep looking for valid JSON
            
    except Exception as e:
        print(f"Buffer processing error for {addr}: {e}")

def main(node_addresses):
    initialize_nodes(node_addresses)
    sockets = [connect_bluetooth(addr) for addr in node_addresses]

    total_available_seats = [0 for addr in node_addresses]
    curr_total = -1

    while True:
        for idx, x in enumerate(zip(sockets, node_addresses)):
            sock = x[0] 
            addr = x[1]
            try:
                chunk = sock.recv(1024).decode('utf-8').strip()
                if not chunk:
                    continue
                
                print(f"Received from {addr}: {repr(chunk)}")  # Debugging
                
                payload = process_data(addr, chunk)
                if payload is None:
                    continue  # Wait for full JSON

                print(f"got full data from sensing node {idx}, going to predict occupancy")

                # Update sliding window
                for i, value in enumerate(payload['occupancy']):
                    sensor_data[addr][i].append(value)

                # Predict occupancy
                predicted_occupancy = predict_occupancy(addr)
                total_available_seats[idx] = predicted_occupancy.count(0)
                print(f"predicted occupancy count for sensing node {idx} is {total_available_seats[idx]}")

            except Exception as e:
                print(f"Error with {addr}: {e}")

        new_total = sum(total_available_seats)
        if new_total != curr_total:
            curr_total = new_total
            send_data_to_server(curr_total)

if __name__ == "__main__":
    node_addresses = ["58:56:00:00:8E:88", "58:56:00:00:8E:2A"]
    #node_addresses = ["58:56:00:00:8E:2A"]
    main(node_addresses)
