import os
import json
import boto3
import logging
import psycopg2
from psycopg2 import sql

logger = logging.getLogger(__name__)

class RDSHelper:
    def __init__(self, config):
        """
        Initialize the RDSHelper with configuration parameters.
        
        Args:
            config (dict): Configuration dictionary containing SQL queries.
        """
        self.db_instance = os.environ.get("RDS_DB_INSTANCE")
        self.database = os.environ.get("RDS_DB_NAME")
        self.user = os.environ.get("RDS_DB_USER")
        self.password = os.environ.get("RDS_DB_PASSWORD")
        self.port = os.environ.get("RDS_DB_PORT")
        self.connection = None
        self.cursor = None
        self.rds_config = config

    def get_rds_endpoint(self):
        """
        Retrieve the endpoint of the RDS instance from AWS.

        Returns:
            str: The endpoint address of the RDS instance.
        """
        rds_client = boto3.client('rds')
        response = rds_client.describe_db_instances(DBInstanceIdentifier=self.db_instance)
        endpoint = response['DBInstances'][0]['Endpoint']['Address']
        return endpoint

    def connect(self):
        """
        Establish a connection to the RDS database and initialize the cursor.
        """
        try:
            endpoint = self.get_rds_endpoint()
            self.connection = psycopg2.connect(
                host=endpoint,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            self.cursor = self.connection.cursor()
            logger.info("Connected to the database")
        except Exception as error:
            logger.error(f"Error: Could not connect to the database\n{error}")

    def disconnect(self):
        """
        Close the database cursor and connection.
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Disconnected from the database")

    def create_table(self):
        """
        Create a table in the database using the query from the configuration.
        """
        try:
            create_table_query = self.rds_config['create_table']
            self.cursor.execute(create_table_query)
            self.connection.commit()
            logger.info("Table 'files' created successfully")
        except Exception as error:
            logger.error(f"Error: Could not create table\n{error}")

    def insert_record(self, file_id, user_id, file_name, status):
        """
        Insert a record into the database.

        Args:
            file_id (str): ID of the file.
            user_id (str): ID of the user.
            file_name (str): Name of the file.
            status (str): Status of the file.
        Returns:
            str: JSON string containing the inserted record details or error message.
        """
        try:
            if self.cursor.closed:
                self.connect()
            insert_query = sql.SQL(self.rds_config['insert_record'])
            self.cursor.execute(insert_query, (file_id, user_id, file_name, status))
            record = self.cursor.fetchone()
            self.connection.commit()
            logger.info(f"Records inserted successfully, number of records: {len(record)}")
            return json.dumps({
                "id": record[0],
                "file_id": record[1],
                "user_id": record[2],
                "file_name": record[3],
                "status": record[4]
            })
        except Exception as error:
            logger.error(f"Error: Could not insert record\n{error}")
            self.connection.rollback()
            return json.dumps({"error": str(error)})

    def fetch_records_by_user_id(self, user_id):
        """
        Fetch records from the database by user ID.

        Args:
            user_id (str): ID of the user.

        Returns:
            str: JSON string containing the fetched records or error message.
        """
        try:
            if self.cursor.closed:
                self.connect()
            fetch_query = sql.SQL(self.rds_config['records_by_user_id'])
            self.cursor.execute(fetch_query, (user_id,))
            records = self.cursor.fetchall()
            logger.info(f"Fetched {len(records)} records, user_id: {user_id}")
            return json.dumps([{
                "id": record[0],
                "file_id": record[1],
                "user_id": record[2],
                "file_name": record[3],
                "status": record[4]
            } for record in records])
        except Exception as error:
            logger.error(f"Error: Could not fetch records\n{error}")
            return json.dumps({"error": str(error)})
    
    def update_status_for_files(self, file_ids, new_status):
        """
        Update the status for multiple files.

        Args:
            file_ids (list): List of file IDs to update.
            new_status (str): New status to set for the files.

        Returns:
            str: JSON string containing the updated records or error message.
        """
        try:
            if self.cursor.closed:
                self.connect()
            update_query = sql.SQL(self.rds_config['update_files_status'])
            self.cursor.execute(update_query, (new_status, file_ids))
            updated_records = self.cursor.fetchall()
            self.connection.commit()
            logger.info(f"Updated {len(updated_records)} records")
            return json.dumps([{
                "id": record[0],
                "file_id": record[1],
                "user_id": record[2],
                "file_name": record[3],
                "status": record[4]
            } for record in updated_records])
        except Exception as error:
            logger.error(f"Error: Could not update records\n{error}")
            return json.dumps({"error": str(error)})
    
    def fetch_file_statuses_by_user_id(self, user_id):
        """
        Fetch the statuses of files by user ID.

        Args:
            user_id (str): ID of the user.

        Returns:
            str: JSON string containing the fetched file statuses or error message.
        """
        try:
            fetch_query = sql.SQL(self.rds_config['files_status_by_user_id'])
            self.cursor.execute(fetch_query, (user_id,))
            records = self.cursor.fetchall()
            logger.info(f"Fetched {len(records)} file statuses, user_id: {user_id}")
            return json.dumps([{
                "file_name": record[0],
                "status": record[1]
            } for record in records])
        except Exception as error:
            logger.error(f"Error: Could not fetch file statuses\n{error}")
            return json.dumps({"error": str(error)})
        
    def delete_document(self, file_ids, user_id):
        """
        Delete a document from the database.

        Args:
            file_ids (list): List of file IDs to delete.

        Returns:
            str: JSON string containing the result of the deletion or error message.
        """
        try:
            if self.cursor.closed:
                self.connect()
            delete_query = sql.SQL(self.rds_config['delete_files'])
            self.cursor.execute(delete_query, (file_ids, user_id))
            self.connection.commit()
            logger.info(f"Deleted {len(file_ids)} documents")
            logger.info(f"Documents deleted successfully, file_ids: {file_ids}")
            logger.info(f"Documents deleted successfully, user_id: {user_id}")
            return json.dumps({
                "message": "Documents deleted successfully", 
                "file_ids": file_ids,
                "user_id": user_id
            })
        except Exception as error:
            logger.error(f"Error: Could not delete documents\n{error}")
            return json.dumps({"error": str(error)})