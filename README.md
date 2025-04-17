<p align="center">
  <a href="https://www.mnma.ai/" target="blank"><img src="assets/logo-full.svg" width="300" alt="MNMA Logo" /></a>
</p>

# 🚀 Minima AWS – Cloud-Based RAG Solution

**Minima AWS** is an open-source, cloud-based **Retrieval-Augmented Generation (RAG)** framework that integrates with **AWS services**, including **S3, SQS, RDS**, and **AWS Bedrock** for embedding models and LLMs. This setup enables efficient document retrieval and chat-based interaction with your indexed data.

---

## 🌐 Overview

Minima AWS operates as a set of containerized services that work together to:

1. 📤 Upload & process documents from an **AWS S3** bucket.
2. 🔍 Index documents for vector search using **Qdrant**.
3. 🤖 Leverage **AWS Bedrock** for embeddings and LLM-based querying.
4. 💬 Enable chat-based retrieval with an **LLM using indexed documents**.

---

## 🏗️ Prerequisites: Setting Up AWS Services

### ✅ **Required AWS Resources**
- 🪣 **Amazon S3** – Store and retrieve documents. (before running application create dir 'upload' inside bucket)
- 📩 **Amazon SQS** – Handle document processing requests.
- 🛢️ **Amazon RDS (PostgreSQL/MySQL)** – Store metadata about indexed documents.
- 🤖 **AWS Bedrock** – Used for:
  - **LLMs (Chat models)**
  - **Embedding models (Vector representation of documents)**

---

## 🔧 Environment Variables

Before running the application, create a `.env` file in the **project root directory** and configure the following variables:

```ini
# AWS Credentials & Services
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1
AWS_BUCKET_NAME=your_s3_bucket_name
AWS_FILES_PATH=s3_folder_path

# SQS Configuration
AWS_SQS_QUEUE=your_sqs_queue_name

# Local File Storage
LOCAL_FILES_PATH=/path/to/local/storage

# RDS Database Configuration
RDS_DB_INSTANCE=your_rds_instance
RDS_DB_NAME=your_rds_database
RDS_DB_USER=your_rds_user
RDS_DB_PASSWORD=your_rds_password
RDS_DB_PORT=5432  # PostgreSQL default

# Vector Search Configuration (Qdrant)
QDRANT_BOOTSTRAP=qdrant
QDRANT_COLLECTION=minima_collection

# AWS Bedrock - LLM & Embedding Model
EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1
EMBEDDING_SIZE=1024
CHAT_MODEL_ID=anthropic.claude-v2
```

### 📝 Explanation:
- **`EMBEDDING_MODEL_ID`** → Embedding model for converting documents into vector representations.
- **`CHAT_MODEL_ID`** → LLM model for answering user queries.

---

📌 How to quickly get the Amazon Bedrock Model ARN from AWS Console

1. Go to AWS Bedrock console:
 - https://console.aws.amazon.com/bedrock

2. Navigate to “Model Access” (in the sidebar on the left).
3. Locate your desired model in the displayed list:
 - Each model has a name, provider, and associated ARN clearly displayed.
4. Copy the model ARN, which looks like:

```
arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-v2
```

You can now use this ARN directly in your configurations.

---

## 🐳 Running Minima AWS with Docker Compose

Once the `.env` file is set up, deploy the application using **Docker Compose**:

```bash
docker compose up --build
```

This will start all required services in separate containers.

---

## 🔧 Services Overview

The system consists of multiple microservices, each running as a **Docker container**.

| **Service**       | **Description** |
|------------------|---------------|
| `qdrant`        | Vector storage for document embeddings. |
| `mnma-upload`   | Uploads and processes documents from AWS S3. |
| `mnma-index`    | Extracts embeddings (using AWS Bedrock) and indexes documents into Qdrant. |
| `mnma-chat`     | Uses an AWS Bedrock LLM to respond to queries based on indexed documents. |

---

## 📤 Uploading Files to Minima AWS

### 1️⃣ **Upload Files via cURL**
Use the following `curl` command to upload a file to Minima AWS:

```bash
curl -X 'POST' \
  'http://localhost:8001/upload/upload_files/?user_id=4637951a-7b45-4af4-805c-1f1c471668f3' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@example.pdf;type=application/pdf'
```

### 2️⃣ **API Endpoint Details**
- **URL:** `http://localhost:8001/upload/upload_files/`
- **Method:** `POST`
- **Query Parameter:** `user_id` (Required)
- **Headers:**
  - `accept: application/json`
  - `Content-Type: multipart/form-data`
- **Body:** A file (e.g., `example.pdf`)

### 3️⃣ **Expected Server Response (JSON)**
```json
{
  "files": [
    {
      "user_id": "4637951a-7b45-4af4-805c-1f1c471668f3",
      "file_id": "52f206e1-26f7-4b62-84d2-7f9bac19400d",
      "file_path": "uploads/example.pdf",
      "filename": "example.pdf"
    }
  ]
}
```

### 4️⃣ **Uploading via Swagger UI**
1. Open **Swagger UI** in your browser:

   👉 **[http://localhost:8001/upload/docs#/default/upload_files_upload_upload_files__post](http://localhost:8001/upload/docs#/default/upload_files_upload_upload_files__post)**

2. Select **POST `/upload/upload_files/`**.
3. Enter your **`user_id`** (e.g., `4637951a-7b45-4af4-805c-1f1c471668f3`).
4. Upload your file (e.g., `Black.pdf`).
5. Click **"Execute"** to send the request.

---

## 🗨️ Connecting to Minima Chat

Minima's **UI is under development** at [**Minima UI GitHub Repo**](https://github.com/pshenok/minima-ui).  
Until the UI is ready, you can use **`websocat`** to interact with the chat service.

---

## 📡 Using WebSocket with Websocat

To connect to Minima Chat manually, install **`websocat`**:

### 🔹 **Install Websocat**
**MacOS:**
```bash
brew install websocat
```
**Linux:**
```bash
sudo apt install websocat
```
**Windows:**
Download from: [**Websocat Releases**](https://github.com/vi/websocat/releases)

---

### 🔹 **Connect to the Chat**
```bash
websocat ws://localhost:8003/chat/{user-id}/{chat-name}/{file-id},{other-file-id}
```
- Replace `{user-id}` with **your user ID**.
- Replace `{file-id}` with **the file IDs** you want to search within.
- You can list **multiple files** using commas.

---

### ✅ **Example**
```bash
websocat ws://localhost:8003/chat/4637951a-7b45-4af4-805c-1f1c471668f3/minima-chat/67890,54321
```
This command initiates a **chat session** with files **67890** and **54321** for **user `4637951a-7b45-4af4-805c-1f1c471668f3`**.

---

## 📜 License

Minima AWS is licensed under the **Mozilla Public License v2.0 (MPLv2)**.

📌 **GitHub Repository:** [Minima AWS](https://github.com/pshenok/minima-aws)

---

## 📞 Need Help?

- ❓ **Issues?** Open a [GitHub Issue](https://github.com/pshenok/minima-aws/issues).
- 💬 **Questions?** Contact us via **GitHub Discussions**.

🚀 **Deploy Minima AWS and unlock the power of AWS Bedrock-powered RAG!** 🚀
```

