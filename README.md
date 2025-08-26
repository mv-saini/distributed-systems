# Distributed File Locking with ZooKeeper

This project demonstrates a distributed locking mechanism for file access using [ZooKeeper](https://zookeeper.apache.org/) and Python ([Kazoo](https://kazoo.readthedocs.io/)). Multiple clients coordinate access to a shared file, ensuring mutual exclusion.

## Project Structure

```
docker-compose.yml
app/
  client.py
  Dockerfile
  requirements.txt
```

- **docker-compose.yml**: Defines ZooKeeper and three client containers.
- **app/client.py**: Python client implementing distributed locking and file access.
- **app/Dockerfile**: Containerizes the Python client.
- **app/requirements.txt**: Python dependencies.

## How It Works

- ZooKeeper manages distributed locks.
- Each client tries to acquire a lock before accessing the shared file (`data/data.txt`).
- Only one client can write to the file at a time.
- Shared data is stored in a Docker volume (`shared-data`).

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)

### Build and Run

1. **Clone the repository:**
   ```sh
   git clone https://github.com/mv-saini/distributed-systems.git
   cd distributed-systems
   ```

2. **Start the services:**
   ```sh
   docker-compose up --build
   ```

3. **View shared file contents:**
   ```sh
   docker run --rm -it -v distributed-systems_shared-data:/data alpine cat /data/data.txt
   ```

### Stopping

To stop and remove containers, networks, and leave volumes (shared data) intact:

```sh
docker-compose down
```

To also remove volumes and delete all shared data:

```sh
docker-compose down -v
```

**Note:** Using the `-v` flag will delete all data stored in named volumes (e.g., `distributed-systems_shared-data`). Omit `-v` if you want to persist data between runs.

## Customization

- Change the number of clients in `docker-compose.yml`.
- Modify `app/client.py` for different file operations or lock logic.

## References
- [Kazoo Documentation](https://kazoo.readthedocs.io/)
- [ZooKeeper Documentation](https://zookeeper.apache.org/)
