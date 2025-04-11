import yaml
from async_queue import AsyncQueue
from aws_rds_helper import RDSHelper

# Create a shared instance of AsyncQueue.
# This shared instance will be used across different parts of the application.
# Ensure that this shared object is managed carefully to prevent concurrency issues.
async_queue = AsyncQueue()
with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)   
    
rds_helper = RDSHelper(config['rds'])