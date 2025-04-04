# Interview Backend

This repository contains the backend code for the Interview application.

## Setup Instructions

Follow these steps to set up and run the backend server:

1. Clone the repository:
   ```bash
   git clone https://github.com/Prathmesh-ChumsAI/Interview_Backend.git
   ```

2. Navigate to the repository directory:
   ```bash
   cd Interview_Backend
   ```

3. Navigate to the code folder (if applicable):
   ```bash
   cd code
   ```

4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the FastAPI server with hot reload:
   ```bash
   python -m uvicorn main:app --reload
   ```

## Development

The server should now be running locally. You can access the API documentation at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## Features

- FastAPI-based backend
- Auto-reloading for development

## Troubleshooting

If you encounter any issues during setup:
- Ensure you have Python installed (recommended version: 3.8+)
- Verify that the requirements.txt file exists in the specified directory
- Check that main.py contains the FastAPI app instance named 'app'

## Contributing

Please refer to the contribution guidelines for information on how to contribute to this project.

