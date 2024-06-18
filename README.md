# battleship

This project implements a Battleship game using Python. The server allows two players to connect, place their ships, and take turns firing at each other's ships until one player's ships are all sunk. The client discovers the server using multicast, connects to it, and handles the game interaction.

## Features

- **Multithreading**: Handles multiple clients concurrently.
- **Multicast Discovery**: Clients discover the server using a multicast group.
- **Signal Handling**: Graceful shutdown on termination signals.
- **Logging**: Logs game events and errors.
