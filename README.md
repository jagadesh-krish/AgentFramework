# ChatVoyager

Welcome to the **ChatVoyager** project! This innovative chatbot is designed to assist users in planning their travel or vacation.

## 🌟 Features

- **Discover Places of Interest**: Search for historic monuments, natural wonders, and cultural landmarks.
- **Interactive Chat**: Engage in real-time conversations with the chatbot.
- **Personalized Recommendations**: Get tailored suggestions based on your preferences.
- **Streaming Responses**: Enjoy dynamic and responsive interactions.
- **Thinking Steps Visualization**: See how the AI processes your queries step-by-step.
- **Real-Time Weather Updates**: Fetch real-time weather information for effective decision-making

## 🛠️ Technologies Used

- **FastAPI**: High-performance backend framework for API and WebSocket handling.
- **ChromaDB**: Advanced vector database for efficient querying.
- **Sentence Transformers**: State-of-the-art embeddings for semantic search.
- **WebSocket**: Real-time communication between the client and server.
- **Structlog**: Enhanced logging for better debugging and monitoring.
- **RabbitMQ**: Message queuing for asynchronous task handling.
- **Microsoft Agent Framework**: A robust framework for developing intelligent agents and workflows.

## 🚀 How It Works

1. **User Interaction**: Users input their queries via the chatbot interface.
2. **AI Processing**: The chatbot uses AI models to understand and process the queries.
3. **Database Querying**: Relevant places are retrieved from the ChromaDB database.
4. **Response Generation**: The chatbot provides detailed and structured responses.

## 📂 Project Structure

```
agentframework/
├── agentframework/
│   ├── client/
│   │   ├── index.html
│   │   ├── chat.js
│   ├── service_layer/
│   │   ├── chat_handlers.py
│   │   ├── http_handlers.py
│   ├── tools.py
│   ├── agent.py
│   ├── response_schema.py
├── RAG/
│   ├── poi_in_india.py
├── main.py
├── response_worker.py
├── README.md
```

## 🖥️ Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/jagadesh-krish/AgentFramework.git
   ```

2. **Navigate to the Project Directory**:
   ```bash
   cd AgentFramework
   ```

3. **Install Dependencies Using Poetry**:
   ```bash
   poetry install
   ```

4. **Set Up Docker for ChromaDB**:
   Ensure Docker is installed and running. Use the following command to start ChromaDB:
   ```bash
   docker run -d --rm --name chromadb -p 8000:8000 -e IS_PERSISTENT=TRUE chromadb/chroma:latest
   ```

5. **Start RabbitMQ**:
   Ensure RabbitMQ is running. If using Docker, start RabbitMQ with:
   ```bash
   docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:management
   ```

6. **Start Local LLM Using Ollama**:
   Ensure Ollama is installed and running for local LLM inference. Start Ollama with:
   ```bash
   ollama start
   ```

7. **Run the FASTAPI Application**:
   ```bash
   poetry run python main.py
   ```

8. **Run the Consumer/Agent Application**:
   ```bash
   poetry run python response_worker.py
   ```
