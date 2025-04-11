import os
import boto3
import logging
from qdrant_client import QdrantClient
from langchain_aws import BedrockEmbeddings
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage
from langchain_qdrant import QdrantVectorStore
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langchain.chains.retrieval import create_retrieval_chain
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.utils import ConfigurableFieldSpec
from qdrant_client.conversions.common_types import Filter as Filter
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain.chains.combine_documents.stuff import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever

loggers = logging.getLogger(__name__)

class ChatRetriever:
    """
    This class handles the setup and execution of a conversational retrieval-augmented generation (RAG) chain 
    using AWS Bedrock for embeddings, Qdrant for vector storage, and a conversational model.
    """

    def __init__(self, config, user_id, files_id, conversation_id):
        """
        Initializes the ChatRetriever with necessary configurations and AWS/Qdrant clients.
        
        Args:
            config (dict): Configuration dictionary containing prompts and other settings.
            user_id (str): Unique identifier for the user session.
            files_id (list): List of unique identifiers for the files uploaded by the user.
            conversation_id (str): Unique identifier for the conversation.
        """
        self.config = config
        self.user_id = user_id
        self.files_id = files_id
        self.conversation_id = conversation_id
        self.store = {}
        self.client_bedrock = boto3.client(
            service_name='bedrock-runtime', 
            region_name=os.environ.get("AWS_DEFAULT_REGION")
        )
        self.embeddings = BedrockEmbeddings(
            model_id=os.environ.get("EMBEDDING_MODEL_ID"),
            client=self.client_bedrock,        
        )
        self.qdrant = QdrantClient(
            host=os.environ.get("QDRANT_BOOTSTRAP"),
        )
        self.vector_store = QdrantVectorStore(
            client=self.qdrant,
            collection_name=user_id,
            embedding=self.embeddings,
        )
        self.llm = ChatBedrockConverse(
            model=os.environ.get("CHAT_MODEL_ID"),
            temperature=0,
            max_tokens=None,
        )
        self.chat_rag = self.create_chat_rag_chain()

    def get_session_history(self) -> BaseChatMessageHistory:
        """
        Retrieves or initializes chat message history for a given session ID.

        Args:
            session_id (str): Unique session identifier.
        
        Returns:
            BaseChatMessageHistory: An instance of chat message history.
        """
        chat_id = self.get_chat_id()
        if chat_id not in self.store:
            self.store[chat_id] = SQLChatMessageHistory(
                session_id=chat_id, 
                connection_string="sqlite:///sqlite.db"
            )
        return self.store[chat_id]
    
    def get_chat_id(self):
        chat_id = self.user_id+self.conversation_id
        if len(self.files_id)!=0:
            return chat_id.join(self.files_id)
        return chat_id
    
    def create_chat_rag_chain(self) -> RunnableWithMessageHistory:
        """
        Creates a RAG (retrieval-augmented generation) chain tailored for conversational AI.
        
        Returns:
            RunnableWithMessageHistory: A runnable chain with integrated message history.
        """
        contextualize_q_system_prompt = self.config['prompts']['context']
        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]) 
        history_aware_retriever = create_history_aware_retriever(
            self.llm, 
            self.vector_store.as_retriever(), 
            contextualize_q_prompt
        )
        system_prompt = self.config['prompts']['system']
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ])

        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
            history_factory_config=[
                ConfigurableFieldSpec(
                    id="chat_id",
                    annotation=str,
                    name="Chat ID",
                    description="Unique identifier for the chat.",
                    default="",
                    is_shared=True,
                ),
            ],
            
        )
        return conversational_rag_chain
    
    def get_user_history(self):
        """
        Retrieves the chat history for a given session and formats it into a structured list.
        
        Returns:
            list: A list of dictionaries containing chat messages, each with a reporter, type, and message.
        """
        history = self.get_session_history().messages
        history_array = []
        for replica in history:
            reporter, message_type = None, None
            if type(replica) is HumanMessage:
                reporter = "input_message"
                message_type = "question"
            elif type(replica) is AIMessage:
                reporter = "output_message"
                message_type = "answer"
            history_array.append({
                "reporter": reporter,
                "type": message_type,
                "message": replica.content,
            })
        return history_array


    def query(self, question: str):
        """
        Processes a user query through the RAG chain and returns the generated answer.
        
        Args:
            question (str): The user's question or input.
        
        Returns:
            str: The generated answer from the conversational RAG chain.
        """
        answer = self.chat_rag.invoke(
            input= { "input": f"{question}" },
            config={ "configurable": {"chat_id": self.get_chat_id()} },
        )

        return answer["answer"]