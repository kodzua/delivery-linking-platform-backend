# delivery linking platform backend
this is the backend service for a delivery linking platform.
it is built using fastapi and runs on python, served with uvicorn.

---

# features
- fastapi REST API
- asynchronous request handling
- modular project structure
- auto-reload for development
- clean separation of routes and services

---

# requirements
make sure you have :
- python 3.12+
- pip installed

---

# installation
- clone the repository :
git clone https://github.com/your-username/delivery-linking-backend.git
cd delivery-linking-backend

- create a virtual environment and activate it :
macos/linux :
python3 -m venv venv
source venv/bin/activate

windows :
python -m venv venv
venv\Scripts\activate

- install the required dependencies :
pip install -r requirements.txt

---

# configuration :
create a .env file in the root directory and add your environment variables :
DATABASE_URL=postgresql+asyncpg://<username>:<password>@<host>:<port>/<database_name>
SECRET_KEY=your_secret_key_here
DEBUG=True

---

# running the app :
start the local development server using uvicorn :
uvicorn app.main:app --reload
the server will be running at http://127.0.0.1:8000

---

# api documentation :
once the server is running, you can access the interactive api docs at :
- swagger ui : http://127.0.0.1:8000/docs
- redoc : http://127.0.0.1:8000/redoc

---

# known issues :
email service compatibility : you must run this project on python 3.12. if you attempt to use python 3.13+, the application will start without errors, but the email service will silently fail to send outbound messages.
