---
name: run-fe
description: Start both the frontend development server and the backend API server.
---
# Start Frontend and Backend

When the user triggers this skill, you must start BOTH the backend API server and the frontend development server in the background.

1. **Start Backend**: Run the backend API server by executing `.\venv\Scripts\python.exe main.py serve` in the project root directory.
2. **Start Frontend**: Run the frontend development server by executing `npm run dev` with the current working directory set to the `frontend` folder.

Since these commands run long-lived servers, you MUST run them in the background asynchronously so the user can continue working without being blocked.

3. **Print App Link**: Once the servers are started, print the frontend development server application URL (typically `http://localhost:5173`) directly in the chat to the user so they can click and access it easily.

