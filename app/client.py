import logging
import time
import uuid
import threading
from kazoo.client import KazooClient
from kazoo.exceptions import NodeExistsError
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(message)s')
logger = logging.getLogger(__name__)

class SharedResource:
    """A class representing a shared file resource."""
    def __init__(self, filename="data.txt"):
        self.filename = filename

        try:
            with open(self.filename, 'a'):
                pass
        except IOError as e:
            logger.error(f"Error creating file {self.filename}: {e}")
            raise

    def read(self):
        """Reads the file."""
        with open(self.filename, 'r') as f:
            return f.read()

    def write(self, data):
        """Appends new data to the file."""
        with open(self.filename, 'a') as f:
            f.write(data + '\n')
            
class DistributedLocker:
    """Implements a distributed lock using ZooKeeper."""
    def __init__(self, zk_client, lock_path):
        self.zk = zk_client
        self.lock_path = lock_path
        self.my_node = None

        # Ensure the parent path for the lock exists
        self.zk.ensure_path(self.lock_path)
    
    def acquire(self):
        """Acquires the distributed lock."""
        logger.info("Attempting to acquire lock...")
        
        # Create an ephemeral sequential node
        path = f"{self.lock_path}/lock-"
        try:
            self.my_node = self.zk.create(path, ephemeral=True, sequence=True)
            logger.info(f"Created lock node: {self.my_node}")
        except NodeExistsError:
            pass
        
        while True:
            # Get all children and find my position
            children = sorted(self.zk.get_children(self.lock_path))
            my_node_name = self.my_node.split('/')[-1]
            try:
                my_index = children.index(my_node_name)
            except ValueError:
                # If the session expires briefly. Re-create and retry.
                self.my_node = self.zk.create(path, ephemeral=True, sequence=True)
                continue

            # Acquire the lock
            if my_index == 0:
                logger.info("Lock acquired successfully!")
                return
            else:
                # Set a watch on the predecessor
                predecessor_node = children[my_index - 1]
                predecessor_path = f"{self.lock_path}/{predecessor_node}"
                logger.info(f"Waiting for lock, watching predecessor: {predecessor_path}")

                # Create an event to block this thread until the predecessor node is deleted (lock becomes available)
                event = threading.Event()

                # Set a watch on the predecessor node
                @self.zk.DataWatch(predecessor_path)
                # Called when the node changes
                def watch_predecessor(data, stat):
                    if stat is None: # If node was deleted
                        # Notify the event that the lock is available and remove the watch by returning false
                        event.set()
                        return False 
                
                # Wait for the watch to be triggered and re-check the condition 
                # Backup in case the connection falls and client is waiting forever
                event.wait(timeout=10)
    
    def release(self):
        """Releases the distributed lock."""
        if self.my_node and self.zk.exists(self.my_node):
            self.zk.delete(self.my_node)
            logger.info(f"Lock released by deleting node: {self.my_node}")
        self.my_node = None
        
def client_process(client_id):
    """Simulates a client competing for and using the distributed lock."""
    session_id = str(uuid.uuid4())
    
    # Initialize ZooKeeper client
    zk_client = KazooClient(hosts='zookeeper:2181')
    try:
        # Start the ZooKeeper client connection
        zk_client.start()
        
        # Create a distributed lock instance for this client
        locker = DistributedLocker(zk_client, "/shared_file_lock")

        # Create a shared resource instance for file operations
        shared_resource = SharedResource(filename="data/data.txt")

        # Acquire the lock
        locker.acquire()

        # --- CRITICAL SECTION --- 
        try:
            current_data = shared_resource.read().strip()
            logger.info(f"Client {client_id} (Session {session_id[:8]}...) read: '{current_data}'")

            new_data = f"Data from client {client_id} at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))} (Session {session_id})"
            shared_resource.write(new_data)
            logger.info(f"Client {client_id} (Session {session_id[:8]}...) wrote: '{new_data}'")
            time.sleep(1) # Simulate work inside the critical section
        finally:
            # Release the lock
            locker.release()
            
    except Exception as e:
        logger.error(f"An error occurred in client {client_id}: {e}")
    finally:
        zk_client.stop()
        zk_client.close()
        logger.info(f"Client {client_id} finished and disconnected from ZooKeeper.")

if __name__ == "__main__":
    client_id = int(os.getenv("CLIENT_ID", 1))
    client_process(client_id=client_id)
# docker run --rm -it -v distributed-app_shared-data:/data alpine cat /data/data.txt