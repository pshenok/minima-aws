import json
import logging
from async_queue import AsyncQueue
import control_flow_commands as cfc
from chat_retriever import ChatRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chat")

async def loop(
        questions_queue: AsyncQueue,
        response_queue: AsyncQueue,
        config: dict,
        data_obj: dict
):
    """
    Main loop for processing chat interactions.
    
    Args:
        questions_queue (AsyncQueue): Queue for incoming user questions.
        response_queue (AsyncQueue): Queue for outgoing responses to the user.
        config (dict): Configuration dictionary.
        data_obj (dict): Data object containing user and conversation information.
    """
    user_id = data_obj["user_id"]
    files_ids = data_obj["files"]
    conversation_id = data_obj["conversation_id"]
    chat_retriever = ChatRetriever(config, user_id, files_ids, conversation_id)
    
    while True:
        data = await questions_queue.dequeue()
        data = data.replace("\n", "")
        if data == cfc.CFC_CLIENT_DISCONNECTED:
            response_queue.enqueue(
                json.dumps({
                    "reporter": "output_message",
                    "type": "disconnect_message",
                })
            )
            break
        if data == cfc.CFC_CHAT_STARTED:
            response_queue.enqueue(
                json.dumps({
                    "reporter": "output_message",
                    "type": "start_message",
                })
            )
            history = chat_retriever.get_user_history()
            for message in history:
                response_queue.enqueue(json.dumps(message))
        elif data == cfc.CFC_CHAT_STOPPED:
            response_queue.enqueue(
                json.dumps({
                    "reporter": "output_message",
                    "type": "stop_message",
                })
            )
        elif data:
            answer = chat_retriever.query(data)
            response_queue.enqueue(
                json.dumps({
                    "reporter": "output_message",
                    "type": "answer",
                    "message": answer,
                })
            )