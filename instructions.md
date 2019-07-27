Dependencies: Python 3.6

1. To run our code, start the Registration Server in its own terminal using: 

  `python reg_server.py`

You should see the message: "Registration Server running on '<IP>' at '65243'"

Take note of the IP printed in this message, as it is used as command line input for the peer program.

2. For each peer you would like to start, open a new terminal window and enter:

`python peer_client.py <input directory> <Registration Server IP> <port for peer server>`
* **input directory:** the directory containing on-hand RFC files for the peer
* **Registraiton Server IP:** the IP address of the Registration Server, printed when you ran step 1.
* **port for peer server:** a desired port for the peer's server function. Note that if you are running multiple peers on the same host, the port numbers entered must be unique for each peer. 

3. For a peer, select an option from the printed menu:

(Q) query for RFCs - Sends a query to currently registered peers to get their RFC Index

(G) get missing RFCs - Starts the process of downloading RFCs from peers

(P) Check active peers - Sends a query for the current list of active peers

(L) Leave the network - Leaves the network, removing this peer from the list of active peers


4. On a new peer, select option (P) then (Q) to get the most up-to-date information about other peers.

5. Select (G) to begin the download process. You will see another command line prompt where you can choose to download all missing RFC files, or specify a specific number of RFCs to download.

6. When finished, select (L) in the menu to leave the server.
